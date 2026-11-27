"""Exportación e importación masiva de información en CSV.

Cada entidad (clientes, catálogos, productos, servicios, pipelines y etapas,
oportunidades, actividades y cotizaciones) tiene un CSV propio con encabezados
en español. Las referencias entre entidades usan claves legibles (correo del
cliente, nombre del pipeline, código del producto, folio…) en lugar de los
identificadores internos, para que el archivo se pueda editar en Excel.

La importación es "todo o nada": se validan todas las filas y, si alguna tiene
errores, no se guarda ningún cambio y se devuelve la lista de errores por fila.
Las filas que ya existen (misma clave) se actualizan; las demás se crean.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
import uuid
import zipfile
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Callable, Iterable

from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.currencies import SUPPORTED_CURRENCIES, tenant_currency
from app.models.activity import Activity
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.opportunity_stage import OpportunityStage
from app.models.opportunity_stage_history import OpportunityStageHistory
from app.models.pipeline import Pipeline
from app.models.product import Product
from app.models.product_catalog import Brand, MeasurementUnit, ProductCategory
from app.models.quote import Quote, QuoteItem
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.client import CreateClientRequest
from app.services.pipelines import (
    MAX_PIPELINES_PER_TENANT, MAX_STAGES_PER_PIPELINE, STAGE_PALETTE, default_stage_color, unique_stage_key,
)

MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_ROWS = 5000
MONEY = Decimal("0.01")

try:  # Fechas sin zona horaria se interpretan con la hora de México.
    from zoneinfo import ZoneInfo

    LOCAL_TZ = ZoneInfo("America/Mexico_City")
except Exception:  # pragma: no cover - sin base de zonas horarias
    LOCAL_TZ = timezone(timedelta(hours=-6))


class RowError(Exception):
    """Error de validación de una fila; se reporta y la importación no se aplica."""


class FileError(Exception):
    """El archivo completo no se puede procesar (formato, tamaño, encabezados)."""


# --------------------------------------------------------------------------- valores

def _norm(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "")
    return "".join(c for c in text if unicodedata.category(c) != "Mn").strip().lower()


def _header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _norm(value)).strip("_")


ITEM_TYPES = {"product": "Producto", "service": "Servicio"}
STATUSES = {"active": "Activo", "inactive": "Inactivo"}
STAGE_TYPES = {"normal": "Normal", "won": "Ganada", "lost": "Perdida"}
ACTIVITY_TYPES = {"call": "Llamada", "email": "Correo", "meeting": "Reunión", "task": "Tarea"}
ACTIVITY_STATUSES = {"pending": "Pendiente", "completed": "Completada", "cancelled": "Cancelada"}
QUOTE_STATUSES = {"draft": "Borrador", "sent": "Enviada", "accepted": "Aceptada", "rejected": "Rechazada", "expired": "Vencida"}
LOSS_REASONS = {
    "price": "Precio", "no_response": "Sin respuesta", "competitor": "Competencia",
    "budget_cancelled": "Presupuesto cancelado", "not_qualified": "No calificada", "other": "Otro",
}
TRUE_VALUES = {"si", "s", "true", "1", "yes", "y", "x", "verdadero", "activo", "activa"}
FALSE_VALUES = {"no", "n", "false", "0", "falso", "inactivo", "inactiva"}


def yes_no(value: bool) -> str:
    return "Sí" if value else "No"


def _fmt_decimal(value) -> str:
    return "" if value is None else format(Decimal(value).normalize(), "f") if Decimal(value) % 1 else str(int(value))


def _fmt_dt(value: datetime | None) -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")


class Row:
    """Una fila del CSV con sus valores ya normalizados por encabezado."""

    def __init__(self, number: int, values: dict[str, str]):
        self.number = number
        self.values = values

    def text(self, col: str, label: str, *, required=False, min_len=0, max_len=None) -> str | None:
        value = " ".join((self.values.get(col) or "").split())
        if not value:
            if required:
                raise RowError(f"«{label}» es obligatorio.")
            return None
        if len(value) < min_len:
            raise RowError(f"«{label}» debe tener al menos {min_len} caracteres.")
        if max_len and len(value) > max_len:
            raise RowError(f"«{label}» admite máximo {max_len} caracteres.")
        return value

    def long_text(self, col: str, label: str, max_len: int) -> str | None:
        value = (self.values.get(col) or "").strip()
        if len(value) > max_len:
            raise RowError(f"«{label}» admite máximo {max_len} caracteres.")
        return value or None

    def has(self, col: str) -> bool:
        return bool((self.values.get(col) or "").strip())

    def boolean(self, col: str, label: str, default: bool) -> bool:
        raw = _norm(self.values.get(col) or "")
        if not raw:
            return default
        if raw in TRUE_VALUES:
            return True
        if raw in FALSE_VALUES:
            return False
        raise RowError(f"«{label}» debe ser Sí o No.")

    def choice(self, col: str, label: str, options: dict[str, str], default: str | None = None) -> str | None:
        raw = _norm(self.values.get(col) or "")
        if not raw:
            if default is None:
                raise RowError(f"«{label}» es obligatorio.")
            return default
        for key, text in options.items():
            if raw in (_norm(key), _norm(text)) or (len(raw) > 3 and _norm(text).startswith(raw)):
                return key
        raise RowError(f"«{label}» no es válido. Usa: {', '.join(options.values())}.")

    def decimal(self, col: str, label: str, *, default: Decimal | None = None, min_value=None, max_value=None,
                positive=False) -> Decimal | None:
        raw = (self.values.get(col) or "").strip().replace("$", "").replace("%", "").replace(" ", "")
        if not raw:
            return default
        if "," in raw and "." in raw:
            raw = raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(",", ".") if re.fullmatch(r"-?\d+,\d{1,2}", raw) else raw.replace(",", "")
        try:
            value = Decimal(raw)
        except InvalidOperation:
            raise RowError(f"«{label}» debe ser un número.")
        if positive and value <= 0:
            raise RowError(f"«{label}» debe ser mayor que cero.")
        if min_value is not None and value < min_value:
            raise RowError(f"«{label}» no puede ser menor que {min_value}.")
        if max_value is not None and value > max_value:
            raise RowError(f"«{label}» no puede ser mayor que {max_value}.")
        return value.quantize(MONEY, ROUND_HALF_UP)

    def integer(self, col: str, label: str, *, default: int | None = None, min_value=None, max_value=None) -> int | None:
        value = self.decimal(col, label, min_value=min_value, max_value=max_value)
        if value is None:
            return default
        if value % 1:
            raise RowError(f"«{label}» debe ser un número entero.")
        return int(value)

    def date(self, col: str, label: str, *, required=False) -> date | None:
        raw = (self.values.get(col) or "").strip()
        if not raw:
            if required:
                raise RowError(f"«{label}» es obligatoria.")
            return None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw[:10], fmt).date()
            except ValueError:
                continue
        raise RowError(f"«{label}» debe tener el formato AAAA-MM-DD.")

    def datetime(self, col: str, label: str, *, required=False) -> datetime | None:
        raw = (self.values.get(col) or "").strip()
        if not raw:
            if required:
                raise RowError(f"«{label}» es obligatoria.")
            return None
        value = None
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d"):
                try:
                    value = datetime.strptime(raw, fmt)
                    break
                except ValueError:
                    continue
        if value is None:
            raise RowError(f"«{label}» debe tener el formato AAAA-MM-DD HH:MM.")
        if value.tzinfo is None:
            value = value.replace(tzinfo=LOCAL_TZ)
        return value

    def currency(self, col: str, default: str) -> str:
        raw = (self.values.get(col) or "").strip().upper()
        if not raw:
            return default
        if raw not in SUPPORTED_CURRENCIES:
            raise RowError(f"«Moneda» no es válida. Usa: {', '.join(SUPPORTED_CURRENCIES)}.")
        return raw

    def uuid(self, col: str) -> str | None:
        raw = (self.values.get(col) or "").strip().lower()
        return raw or None


# --------------------------------------------------------------------------- contexto

@dataclass
class ImportContext:
    db: Session
    user: User
    created: int = 0
    updated: int = 0
    errors: list[dict] = field(default_factory=list)
    # Identificadores del CSV -> registros reales (para enlazar entre archivos).
    opportunity_ids: dict[str, uuid.UUID] = field(default_factory=dict)
    _currency: str | None = None
    _tenant: Tenant | None = None

    @property
    def tenant_id(self):
        return self.user.tenant_id

    @property
    def currency(self) -> str:
        if not self._currency:
            self._currency = tenant_currency(self.db, self.tenant_id)
        return self._currency

    @property
    def tenant(self) -> Tenant:
        if not self._tenant:
            self._tenant = self.db.query(Tenant).filter(Tenant.id == self.tenant_id).first()
        return self._tenant

    def error(self, filename: str, row: int, message: str) -> None:
        self.errors.append({"file": filename, "row": row, "message": message})

    def run(self, filename: str, row: Row, action: Callable[[], str | None]) -> None:
        """Ejecuta la fila en un savepoint: si falla, solo se revierte esa fila."""
        try:
            with self.db.begin_nested():
                result = action()
                self.db.flush()
        except RowError as exc:
            self.error(filename, row.number, str(exc))
            return
        except IntegrityError:
            self.error(filename, row.number, "El registro entra en conflicto con otro existente (dato duplicado).")
            return
        if result == "created":
            self.created += 1
        elif result == "updated":
            self.updated += 1

    # ---- búsquedas compartidas
    def client_by_email(self, email: str | None) -> Client:
        if not email:
            raise RowError("«Correo del cliente» es obligatorio.")
        client = self.db.query(Client).filter(Client.tenant_id == self.tenant_id,
            func.lower(Client.email) == email.strip().lower()).first()
        if not client:
            raise RowError(f"No existe un cliente con el correo {email}.")
        return client

    def owner_by_email(self, email: str | None) -> User:
        if not email:
            return self.user
        owner = self.db.query(User).filter(User.tenant_id == self.tenant_id, User.status == "active",
            func.lower(User.email) == email.strip().lower()).first()
        if not owner:
            raise RowError(f"No existe un usuario activo con el correo {email}.")
        return owner

    def opportunity_by_id(self, raw: str | None) -> Opportunity | None:
        if not raw:
            return None
        target = self.opportunity_ids.get(raw)
        if not target:
            try:
                target = uuid.UUID(raw)
            except ValueError:
                raise RowError(f"No existe la oportunidad {raw}.")
        item = self.db.query(Opportunity).filter(Opportunity.id == target, Opportunity.tenant_id == self.tenant_id).first()
        if not item:
            raise RowError(f"No existe la oportunidad {raw}.")
        return item


# --------------------------------------------------------------------------- CSV

def write_csv(columns: list[tuple[str, str]], rows: Iterable[dict]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow([col for col, _ in columns])
    for row in rows:
        writer.writerow(["" if row.get(col) is None else row.get(col) for col, _ in columns])
    # BOM: Excel reconoce los acentos al abrir el archivo.
    return ("﻿" + buffer.getvalue()).encode("utf-8")


def read_csv(content: bytes, columns: list[tuple[str, str]], required: tuple[str, ...]) -> list[Row]:
    if len(content) > MAX_FILE_BYTES:
        raise FileError("El archivo supera el máximo de 5 MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    if not text.strip():
        raise FileError("El archivo está vacío.")
    first_line = text.splitlines()[0]
    delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    headers = [_header(h) for h in next(reader, [])]
    known = {_header(col): col for col, _ in columns}
    # También se aceptan los títulos descriptivos ("Correo del cliente").
    known.update({_header(label): col for col, label in columns})
    mapped = [known.get(h) for h in headers]
    missing = [label for col, label in columns if col in required and col not in mapped]
    if missing:
        raise FileError(f"Faltan columnas obligatorias: {', '.join(missing)}.")
    rows: list[Row] = []
    for number, values in enumerate(reader, start=2):
        if not any(v.strip() for v in values):
            continue
        rows.append(Row(number, {col: values[i] for i, col in enumerate(mapped) if col and i < len(values)}))
        if len(rows) > MAX_ROWS:
            raise FileError(f"El archivo supera el máximo de {MAX_ROWS} filas.")
    return rows


# --------------------------------------------------------------------------- entidades

@dataclass
class Entity:
    key: str
    filename: str
    label: str
    columns: list[tuple[str, str]]
    required: tuple[str, ...]
    view_permission: str
    import_permissions: tuple[str, ...]
    export: Callable[[Session, object], Iterable[dict]]
    importer: Callable[[ImportContext, str, list[Row]], None]


def _slug_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _norm(value)).strip("-")[:50]


# ---- unidades

UNIT_COLUMNS = [("clave", "Clave"), ("nombre", "Nombre"), ("abreviatura", "Abreviatura"), ("tipo", "Tipo"), ("activo", "Activo")]


def export_units(db: Session, tenant_id):
    for u in db.query(MeasurementUnit).filter(MeasurementUnit.tenant_id == tenant_id).order_by(MeasurementUnit.item_type, MeasurementUnit.name):
        yield {"clave": u.key, "nombre": u.name, "abreviatura": u.abbreviation, "tipo": ITEM_TYPES.get(u.item_type, u.item_type), "activo": yes_no(u.is_active)}


def import_units(ctx: ImportContext, filename: str, rows: list[Row]):
    db = ctx.db
    for row in rows:
        def action(row=row):
            name = row.text("nombre", "Nombre", required=True, min_len=1, max_len=80)
            abbreviation = row.text("abreviatura", "Abreviatura", required=True, max_len=15)
            item_type = row.choice("tipo", "Tipo", ITEM_TYPES)
            key = _slug_key(row.text("clave", "Clave", max_len=50) or name)
            if not key:
                raise RowError("«Clave» no es válida.")
            base = db.query(MeasurementUnit).filter(MeasurementUnit.tenant_id == ctx.tenant_id)
            unit = base.filter(MeasurementUnit.key == key).first() or base.filter(func.lower(MeasurementUnit.name) == name.lower()).first()
            same_name = base.filter(func.lower(MeasurementUnit.name) == name.lower())
            if unit:
                same_name = same_name.filter(MeasurementUnit.id != unit.id)
            if same_name.first():
                raise RowError(f"Ya existe otra unidad llamada «{name}».")
            active = row.boolean("activo", "Activo", unit.is_active if unit else True)
            if unit:
                if unit.item_type != item_type and db.query(Product.id).filter(Product.unit_id == unit.id).first():
                    raise RowError(f"La unidad «{unit.name}» ya se usa en elementos y no puede cambiar de tipo.")
                unit.name, unit.abbreviation, unit.item_type, unit.is_active = name, abbreviation, item_type, active
                return "updated"
            db.add(MeasurementUnit(tenant_id=ctx.tenant_id, key=key, name=name, abbreviation=abbreviation, item_type=item_type, is_active=active))
            return "created"
        ctx.run(filename, row, action)


# ---- marcas y categorías

SIMPLE_COLUMNS = [("nombre", "Nombre"), ("descripcion", "Descripción"), ("activo", "Activo")]


def _simple_export(model):
    def export(db: Session, tenant_id):
        for item in db.query(model).filter(model.tenant_id == tenant_id).order_by(model.name):
            yield {"nombre": item.name, "descripcion": item.description or "", "activo": yes_no(item.is_active)}
    return export


def _simple_import(model, max_name: int):
    def importer(ctx: ImportContext, filename: str, rows: list[Row]):
        for row in rows:
            def action(row=row):
                name = row.text("nombre", "Nombre", required=True, min_len=2, max_len=max_name)
                description = row.text("descripcion", "Descripción", max_len=300)
                item = ctx.db.query(model).filter(model.tenant_id == ctx.tenant_id, func.lower(model.name) == name.lower()).first()
                active = row.boolean("activo", "Activo", item.is_active if item else True)
                if item:
                    item.name, item.description, item.is_active = name, description, active
                    return "updated"
                ctx.db.add(model(tenant_id=ctx.tenant_id, name=name, description=description, is_active=active))
                return "created"
            ctx.run(filename, row, action)
    return importer


# ---- productos y servicios

PRODUCT_COLUMNS = [
    ("codigo", "Código"), ("nombre", "Nombre"), ("descripcion", "Descripción"), ("categoria", "Categoría"),
    ("marca", "Marca"), ("unidad", "Unidad de medida"), ("precio_base", "Precio base"), ("moneda", "Moneda"),
    ("iva", "IVA"), ("estado", "Estado"),
]


def _product_export(item_type: str):
    def export(db: Session, tenant_id):
        query = db.query(Product).filter(Product.tenant_id == tenant_id, Product.item_type == item_type).order_by(Product.name)
        for p in query:
            yield {
                "codigo": p.sku, "nombre": p.name, "descripcion": p.description or "",
                "categoria": p.category.name if p.category else "", "marca": p.brand.name if p.brand else "",
                "unidad": p.measurement_unit.name, "precio_base": _fmt_decimal(p.base_price), "moneda": p.currency,
                "iva": _fmt_decimal(p.tax_rate), "estado": STATUSES.get(p.status, p.status),
            }
    return export


def _catalog_by_name(ctx: ImportContext, model, name: str | None):
    """Busca la marca o categoría por nombre; si no existe, se crea activa."""
    if not name:
        return None
    item = ctx.db.query(model).filter(model.tenant_id == ctx.tenant_id, func.lower(model.name) == name.lower()).first()
    if not item:
        item = model(tenant_id=ctx.tenant_id, name=name[:100], is_active=True)
        ctx.db.add(item)
        ctx.db.flush()
    return item


def _product_import(item_type: str):
    from app.api.v1.products import _next_available_sku  # import local: evita ciclos

    type_label = "producto" if item_type == "product" else "servicio"

    def importer(ctx: ImportContext, filename: str, rows: list[Row]):
        db = ctx.db
        for row in rows:
            def action(row=row):
                name = row.text("nombre", "Nombre", required=True, min_len=2, max_len=140)
                sku = (row.text("codigo", "Código", max_len=50) or "").upper() or None
                if sku and not re.fullmatch(r"[A-Z0-9._-]{2,50}", sku):
                    raise RowError("«Código» solo admite letras, números, punto, guion y guion bajo.")
                base = db.query(Product).filter(Product.tenant_id == ctx.tenant_id)
                item = base.filter(Product.sku == sku).first() if sku else None
                if item and item.item_type != item_type:
                    raise RowError(f"El código {sku} pertenece a un {'servicio' if item_type == 'product' else 'producto'}.")
                same_name = base.filter(Product.item_type == item_type, func.lower(Product.name) == name.lower())
                if item:
                    same_name = same_name.filter(Product.id != item.id)
                duplicate = same_name.first()
                if duplicate and (sku or item):
                    raise RowError(f"Ya existe un {type_label} llamado «{name}» con el código {duplicate.sku}.")
                if duplicate:
                    item = duplicate  # sin código: se actualiza el que tiene el mismo nombre
                unit_ref = row.text("unidad", "Unidad de medida", required=True)
                units = db.query(MeasurementUnit).filter(MeasurementUnit.tenant_id == ctx.tenant_id)
                unit = units.filter(MeasurementUnit.key == _slug_key(unit_ref)).first() or units.filter(
                    func.lower(MeasurementUnit.name) == unit_ref.lower()).first() or units.filter(
                    func.lower(MeasurementUnit.abbreviation) == unit_ref.lower(), MeasurementUnit.item_type == item_type).first()
                if not unit:
                    raise RowError(f"No existe la unidad de medida «{unit_ref}».")
                if unit.item_type != item_type:
                    raise RowError(f"La unidad «{unit.name}» no es de tipo {type_label}.")
                category = _catalog_by_name(ctx, ProductCategory, row.text("categoria", "Categoría", max_len=80))
                brand = _catalog_by_name(ctx, Brand, row.text("marca", "Marca", max_len=100))
                values = dict(
                    name=name, description=row.long_text("descripcion", "Descripción", 1000),
                    category_id=category.id if category else None, brand_id=brand.id if brand else None,
                    unit=unit.key, unit_id=unit.id,
                    base_price=row.decimal("precio_base", "Precio base", default=item.base_price if item else Decimal("0"), min_value=0),
                    currency=row.currency("moneda", item.currency if item else ctx.currency),
                    tax_rate=row.decimal("iva", "IVA", default=item.tax_rate if item else Decimal("16"), min_value=0, max_value=100),
                    status=row.choice("estado", "Estado", STATUSES, item.status if item else "active"),
                )
                if item:
                    for key, value in values.items():
                        setattr(item, key, value)
                    return "updated"
                _ensure_capacity(ctx, "products")
                db.add(Product(tenant_id=ctx.tenant_id, item_type=item_type,
                    sku=sku or _next_available_sku(db, ctx.tenant_id, name, item_type), **values))
                return "created"
            ctx.run(filename, row, action)
    return importer


def _ensure_capacity(ctx: ImportContext, resource: str) -> None:
    from fastapi import HTTPException
    from app.services.saas_limits import ensure_tenant_capacity

    ctx.db.flush()
    try:
        ensure_tenant_capacity(ctx.db, ctx.tenant_id, resource)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {}
        if detail.get("code") == "PLAN_LIMIT_REACHED":
            raise RowError(f"Se alcanzó el límite de tu plan ({detail.get('limit')} registros).")
        raise RowError("La suscripción de la empresa no está activa.")


# ---- clientes

CLIENT_COLUMNS = [("empresa", "Empresa"), ("contacto", "Contacto"), ("email", "Correo"), ("telefono", "Teléfono"),
                  ("estado", "Estado"), ("notas", "Notas")]


def export_clients(db: Session, tenant_id):
    for c in db.query(Client).filter(Client.tenant_id == tenant_id).order_by(Client.company_name):
        yield {"empresa": c.company_name, "contacto": c.contact_name, "email": c.email, "telefono": c.phone or "",
               "estado": STATUSES.get(c.status, c.status), "notas": c.notes or ""}


def import_clients(ctx: ImportContext, filename: str, rows: list[Row]):
    db = ctx.db
    for row in rows:
        def action(row=row):
            try:
                payload = CreateClientRequest(
                    company_name=row.text("empresa", "Empresa") or "", contact_name=row.text("contacto", "Contacto") or "",
                    email=(row.values.get("email") or "").strip(), phone=row.text("telefono", "Teléfono"),
                    notes=row.long_text("notas", "Notas", 1000),
                )
            except ValidationError as exc:
                fields = {"company_name": "Empresa", "contact_name": "Contacto", "email": "Correo", "phone": "Teléfono", "notes": "Notas"}
                names = sorted({fields.get(str(e["loc"][0]), str(e["loc"][0])) for e in exc.errors()})
                raise RowError(f"Revisa: {', '.join(names)}.")
            client = db.query(Client).filter(Client.tenant_id == ctx.tenant_id, func.lower(Client.email) == payload.email).first()
            status = row.choice("estado", "Estado", STATUSES, client.status if client else "active")
            if client:
                client.company_name, client.contact_name = payload.company_name, payload.contact_name
                client.phone, client.notes, client.status = payload.phone, payload.notes, status
                return "updated"
            _ensure_capacity(ctx, "clients")
            db.add(Client(tenant_id=ctx.tenant_id, company_name=payload.company_name, contact_name=payload.contact_name,
                          email=payload.email, phone=payload.phone, notes=payload.notes, status=status))
            return "created"
        ctx.run(filename, row, action)


# ---- pipelines y etapas (una fila por etapa)

PIPELINE_COLUMNS = [
    ("pipeline", "Pipeline"), ("pipeline_descripcion", "Descripción del pipeline"), ("pipeline_color", "Color del pipeline"),
    ("pipeline_predeterminado", "Pipeline predeterminado"), ("pipeline_activo", "Pipeline activo"),
    ("etapa_clave", "Clave de etapa"), ("etapa", "Etapa"), ("posicion", "Posición"), ("tipo", "Tipo de etapa"),
    ("probabilidad", "Probabilidad"), ("color", "Color de etapa"), ("activa", "Etapa activa"),
]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def export_pipelines(db: Session, tenant_id):
    pipelines = db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id).order_by(Pipeline.position, Pipeline.name).all()
    for p in pipelines:
        stages = db.query(OpportunityStage).filter(OpportunityStage.pipeline_id == p.id).order_by(OpportunityStage.position).all()
        for s in stages:
            yield {
                "pipeline": p.name, "pipeline_descripcion": p.description or "", "pipeline_color": p.color,
                "pipeline_predeterminado": yes_no(p.is_default), "pipeline_activo": yes_no(p.is_active),
                "etapa_clave": s.key, "etapa": s.name, "posicion": s.position, "tipo": STAGE_TYPES.get(s.stage_type, s.stage_type),
                "probabilidad": s.default_probability, "color": s.color, "activa": yes_no(s.is_active),
            }


def _hex(row: Row, col: str, label: str, default: str) -> str:
    value = (row.values.get(col) or "").strip()
    if not value:
        return default
    if not HEX.match(value):
        raise RowError(f"«{label}» debe ser un color hexadecimal como #3b82f6.")
    return value.lower()


def import_pipelines(ctx: ImportContext, filename: str, rows: list[Row]):
    db = ctx.db
    groups: "OrderedDict[str, list[Row]]" = OrderedDict()
    for row in rows:
        name = " ".join((row.values.get("pipeline") or "").split())
        if not name:
            ctx.error(filename, row.number, "«Pipeline» es obligatorio.")
            continue
        groups.setdefault(name.lower(), []).append(row)

    for group in groups.values():
        first = group[0]
        holder: dict = {}

        def pipeline_action(row=first):
            name = row.text("pipeline", "Pipeline", required=True, min_len=2, max_len=80)
            pipeline = db.query(Pipeline).filter(Pipeline.tenant_id == ctx.tenant_id, func.lower(Pipeline.name) == name.lower()).first()
            created = pipeline is None
            if created:
                count = db.query(func.count(Pipeline.id)).filter(Pipeline.tenant_id == ctx.tenant_id).scalar() or 0
                if count >= MAX_PIPELINES_PER_TENANT:
                    raise RowError(f"Solo se permiten {MAX_PIPELINES_PER_TENANT} pipelines por empresa.")
                pipeline = Pipeline(tenant_id=ctx.tenant_id, name=name, position=count + 1, is_default=False, is_active=True,
                                    color=STAGE_PALETTE[count % len(STAGE_PALETTE)])
                db.add(pipeline)
                db.flush()
            pipeline.name = name
            if row.has("pipeline_descripcion"):
                pipeline.description = row.text("pipeline_descripcion", "Descripción del pipeline", max_len=200)
            pipeline.color = _hex(row, "pipeline_color", "Color del pipeline", pipeline.color)
            make_default = row.boolean("pipeline_predeterminado", "Pipeline predeterminado", pipeline.is_default)
            active = row.boolean("pipeline_activo", "Pipeline activo", pipeline.is_active)
            if pipeline.is_default and not active:
                raise RowError("El pipeline predeterminado debe estar activo.")
            if make_default and not active:
                raise RowError("El pipeline predeterminado debe estar activo.")
            if not active and pipeline.is_active:
                open_count = db.query(func.count(Opportunity.id)).filter(Opportunity.pipeline_id == pipeline.id,
                    Opportunity.archived_at.is_(None), Opportunity.closed_at.is_(None)).scalar() or 0
                if open_count:
                    raise RowError("El pipeline tiene oportunidades abiertas y no se puede desactivar.")
            pipeline.is_active = active
            if make_default and not pipeline.is_default:
                db.query(Pipeline).filter(Pipeline.tenant_id == ctx.tenant_id, Pipeline.id != pipeline.id).update({"is_default": False})
                db.flush()
                pipeline.is_default = True
            holder["pipeline"], holder["created"] = pipeline, created
            return "created" if created else "updated"

        before = len(ctx.errors)
        ctx.run(filename, first, pipeline_action)
        if len(ctx.errors) > before or "pipeline" not in holder:
            continue
        pipeline: Pipeline = holder["pipeline"]

        for row in group:
            if not (row.has("etapa") or row.has("etapa_clave")):
                continue

            def stage_action(row=row):
                stages = db.query(OpportunityStage).filter(OpportunityStage.tenant_id == ctx.tenant_id)
                raw_key = row.text("etapa_clave", "Clave de etapa", max_len=50)
                stage = None
                if raw_key:
                    stage = stages.filter(OpportunityStage.key == raw_key).first()
                    if stage and stage.pipeline_id != pipeline.id:
                        raise RowError(f"La clave de etapa «{raw_key}» ya pertenece a otro pipeline.")
                name = row.text("etapa", "Etapa", required=stage is None, min_len=2, max_len=80) or stage.name
                if not stage:
                    stage = stages.filter(OpportunityStage.pipeline_id == pipeline.id, func.lower(OpportunityStage.name) == name.lower()).first()
                clash = stages.filter(OpportunityStage.pipeline_id == pipeline.id, func.lower(OpportunityStage.name) == name.lower())
                if stage:
                    clash = clash.filter(OpportunityStage.id != stage.id)
                if clash.first():
                    raise RowError(f"El pipeline ya tiene otra etapa llamada «{name}».")
                stage_type = row.choice("tipo", "Tipo de etapa", STAGE_TYPES, stage.stage_type if stage else "normal")
                count = stages.filter(OpportunityStage.pipeline_id == pipeline.id).count()
                default_probability = 100 if stage_type == "won" else 0 if stage_type == "lost" else 10
                position = row.integer("posicion", "Posición", default=stage.position if stage else count + 1, min_value=1, max_value=999)
                probability = row.integer("probabilidad", "Probabilidad",
                    default=stage.default_probability if stage else default_probability, min_value=0, max_value=100)
                color = _hex(row, "color", "Color de etapa", stage.color if stage else default_stage_color(stage_type, count))
                active = row.boolean("activa", "Etapa activa", stage.is_active if stage else True)
                if stage:
                    if stage.is_active and not active:
                        in_use = db.query(func.count(Opportunity.id)).filter(Opportunity.tenant_id == ctx.tenant_id,
                            Opportunity.stage == stage.key, Opportunity.archived_at.is_(None)).scalar() or 0
                        if in_use:
                            raise RowError(f"La etapa «{stage.name}» tiene oportunidades activas y no se puede desactivar.")
                    stage.name, stage.stage_type, stage.position = name, stage_type, position
                    stage.default_probability, stage.color, stage.is_active = probability, color, active
                    return "updated"
                if count >= MAX_STAGES_PER_PIPELINE:
                    raise RowError(f"Un pipeline admite máximo {MAX_STAGES_PER_PIPELINE} etapas.")
                db.add(OpportunityStage(tenant_id=ctx.tenant_id, pipeline_id=pipeline.id,
                    key=unique_stage_key(db, ctx.tenant_id, raw_key or name), name=name, position=position,
                    stage_type=stage_type, default_probability=probability, color=color, is_active=active))
                return "created"
            ctx.run(filename, row, stage_action)

        if holder["created"]:
            db.flush()
            types = {t for (t,) in db.query(OpportunityStage.stage_type).filter(OpportunityStage.pipeline_id == pipeline.id,
                     OpportunityStage.is_active.is_(True))}
            if not {"won", "lost"} <= types or "normal" not in types:
                ctx.error(filename, first.number, f"El pipeline nuevo «{pipeline.name}» necesita al menos una etapa normal, una Ganada y una Perdida.")


# ---- oportunidades

OPPORTUNITY_COLUMNS = [
    ("id", "ID"), ("nombre", "Nombre"), ("cliente_email", "Correo del cliente"), ("cliente", "Cliente"),
    ("pipeline", "Pipeline"), ("etapa_clave", "Clave de etapa"), ("etapa", "Etapa"),
    ("responsable_email", "Correo del responsable"), ("responsable", "Responsable"), ("monto", "Monto"),
    ("moneda", "Moneda"), ("probabilidad", "Probabilidad"), ("fecha_cierre_estimada", "Fecha estimada de cierre"),
    ("notas", "Notas"), ("motivo_perdida", "Motivo de pérdida"), ("detalle_perdida", "Detalle de pérdida"),
    ("archivada", "Archivada"), ("cerrada_en", "Cerrada en"), ("creada_en", "Creada en"),
]


def export_opportunities(db: Session, tenant_id):
    stages = {(s.pipeline_id, s.key): s.name for s in db.query(OpportunityStage).filter(OpportunityStage.tenant_id == tenant_id)}
    for o in db.query(Opportunity).filter(Opportunity.tenant_id == tenant_id).order_by(Opportunity.created_at):
        yield {
            "id": str(o.id), "nombre": o.name, "cliente_email": o.client.email, "cliente": o.client.company_name,
            "pipeline": o.pipeline.name, "etapa_clave": o.stage, "etapa": stages.get((o.pipeline_id, o.stage), o.stage),
            "responsable_email": o.owner.email, "responsable": o.owner.full_name or o.owner.email,
            "monto": _fmt_decimal(o.amount), "moneda": o.currency, "probabilidad": o.probability,
            "fecha_cierre_estimada": o.expected_close_date.isoformat() if o.expected_close_date else "",
            "notas": o.notes or "", "motivo_perdida": LOSS_REASONS.get(o.loss_reason, o.loss_reason or ""),
            "detalle_perdida": o.loss_detail or "", "archivada": yes_no(o.archived_at is not None),
            "cerrada_en": _fmt_dt(o.closed_at), "creada_en": _fmt_dt(o.created_at),
        }


def import_opportunities(ctx: ImportContext, filename: str, rows: list[Row]):
    db = ctx.db
    for row in rows:
        def action(row=row):
            raw_id = row.uuid("id")
            item = None
            if raw_id:
                try:
                    item = db.query(Opportunity).filter(Opportunity.id == uuid.UUID(raw_id), Opportunity.tenant_id == ctx.tenant_id).first()
                except ValueError:
                    item = None
            name = row.text("nombre", "Nombre", required=True, min_len=3, max_len=140)
            client = ctx.client_by_email(row.text("cliente_email", "Correo del cliente"))
            pipeline_name = row.text("pipeline", "Pipeline")
            pipelines = db.query(Pipeline).filter(Pipeline.tenant_id == ctx.tenant_id)
            if pipeline_name:
                pipeline = pipelines.filter(func.lower(Pipeline.name) == pipeline_name.lower()).first()
                if not pipeline:
                    raise RowError(f"No existe el pipeline «{pipeline_name}».")
            else:
                pipeline = item.pipeline if item else pipelines.filter(Pipeline.is_default.is_(True)).first()
                if not pipeline:
                    raise RowError("La empresa no tiene pipeline predeterminado.")
            stages = db.query(OpportunityStage).filter(OpportunityStage.pipeline_id == pipeline.id)
            stage_key, stage_name = row.text("etapa_clave", "Clave de etapa"), row.text("etapa", "Etapa")
            stage = (stages.filter(OpportunityStage.key == stage_key).first() if stage_key else None) or (
                stages.filter(func.lower(OpportunityStage.name) == stage_name.lower()).first() if stage_name else None)
            if not stage and (stage_key or stage_name):
                raise RowError(f"La etapa «{stage_name or stage_key}» no existe en el pipeline «{pipeline.name}».")
            if not stage:
                stage = (stages.filter(OpportunityStage.key == item.stage).first() if item else None) or stages.filter(
                    OpportunityStage.is_active.is_(True), OpportunityStage.stage_type == "normal").order_by(OpportunityStage.position).first()
                if not stage:
                    raise RowError(f"El pipeline «{pipeline.name}» no tiene etapas activas.")
            owner = ctx.owner_by_email(row.text("responsable_email", "Correo del responsable")) if row.has("responsable_email") or not item else item.owner
            probability = row.integer("probabilidad", "Probabilidad", default=item.probability if item and item.stage == stage.key else stage.default_probability,
                                      min_value=0, max_value=100)
            if stage.stage_type == "won":
                probability = 100
            elif stage.stage_type == "lost":
                probability = 0
            loss_reason = row.choice("motivo_perdida", "Motivo de pérdida", LOSS_REASONS, "") or None
            values = dict(
                name=name, client_id=client.id, pipeline_id=pipeline.id, owner_user_id=owner.id, stage=stage.key,
                amount=row.decimal("monto", "Monto", default=item.amount if item else Decimal("0"), min_value=0),
                currency=row.currency("moneda", item.currency if item else ctx.currency), probability=probability,
                expected_close_date=row.date("fecha_cierre_estimada", "Fecha estimada de cierre"),
                notes=row.long_text("notas", "Notas", 2000),
                loss_reason=loss_reason if stage.stage_type == "lost" else None,
                loss_detail=row.text("detalle_perdida", "Detalle de pérdida", max_len=300) if stage.stage_type == "lost" else None,
            )
            archived = row.boolean("archivada", "Archivada", bool(item and item.archived_at))
            now = datetime.now(timezone.utc)
            previous_stage = item.stage if item else None
            result = "updated"
            if not item:
                item = Opportunity(tenant_id=ctx.tenant_id, **values)
                db.add(item)
                db.flush()
                result = "created"
            else:
                for key, value in values.items():
                    setattr(item, key, value)
            if stage.stage_type in ("won", "lost"):
                item.closed_at = item.closed_at or now
            else:
                item.closed_at = None
            item.archived_at = (item.archived_at or now) if archived else None
            if raw_id:
                ctx.opportunity_ids[raw_id] = item.id
            if result == "created" or previous_stage != item.stage:
                db.add(OpportunityStageHistory(tenant_id=ctx.tenant_id, opportunity_id=item.id, from_stage_key=previous_stage,
                    to_stage_key=item.stage, probability=item.probability, expected_close_date=item.expected_close_date,
                    note="Importada desde CSV", changed_by_user_id=ctx.user.id))
            return result
        ctx.run(filename, row, action)


# ---- actividades

ACTIVITY_COLUMNS = [
    ("id", "ID"), ("titulo", "Título"), ("tipo", "Tipo"), ("estado", "Estado"), ("fecha_programada", "Fecha programada"),
    ("cliente_email", "Correo del cliente"), ("cliente", "Cliente"), ("oportunidad_id", "ID de oportunidad"),
    ("oportunidad", "Oportunidad"), ("responsable_email", "Correo del responsable"), ("responsable", "Responsable"),
    ("descripcion", "Descripción"), ("completada_en", "Completada en"),
]


def export_activities(db: Session, tenant_id):
    for a in db.query(Activity).filter(Activity.tenant_id == tenant_id).order_by(Activity.scheduled_at):
        yield {
            "id": str(a.id), "titulo": a.title, "tipo": ACTIVITY_TYPES.get(a.activity_type, a.activity_type),
            "estado": ACTIVITY_STATUSES.get(a.status, a.status), "fecha_programada": _fmt_dt(a.scheduled_at),
            "cliente_email": a.client.email, "cliente": a.client.company_name,
            "oportunidad_id": str(a.opportunity_id) if a.opportunity_id else "", "oportunidad": a.opportunity.name if a.opportunity else "",
            "responsable_email": a.owner.email, "responsable": a.owner.full_name or a.owner.email,
            "descripcion": a.description or "", "completada_en": _fmt_dt(a.completed_at),
        }


def import_activities(ctx: ImportContext, filename: str, rows: list[Row]):
    db = ctx.db
    for row in rows:
        def action(row=row):
            raw_id = row.uuid("id")
            item = None
            if raw_id:
                try:
                    item = db.query(Activity).filter(Activity.id == uuid.UUID(raw_id), Activity.tenant_id == ctx.tenant_id).first()
                except ValueError:
                    item = None
            opportunity = ctx.opportunity_by_id(row.uuid("oportunidad_id"))
            if row.has("cliente_email") or not opportunity:
                client = ctx.client_by_email(row.text("cliente_email", "Correo del cliente"))
            else:
                client = opportunity.client
            if opportunity and opportunity.client_id != client.id:
                raise RowError("La oportunidad no pertenece al cliente indicado.")
            owner = ctx.owner_by_email(row.text("responsable_email", "Correo del responsable")) if row.has("responsable_email") or not item else item.owner
            status = row.choice("estado", "Estado", ACTIVITY_STATUSES, item.status if item else "pending")
            values = dict(
                title=row.text("titulo", "Título", required=True, min_len=3, max_len=140),
                activity_type=row.choice("tipo", "Tipo", ACTIVITY_TYPES, item.activity_type if item else None),
                scheduled_at=row.datetime("fecha_programada", "Fecha programada", required=item is None) or item.scheduled_at,
                description=row.long_text("descripcion", "Descripción", 1000),
                client_id=client.id, opportunity_id=opportunity.id if opportunity else None, owner_user_id=owner.id, status=status,
            )
            result = "updated"
            if not item:
                item = Activity(tenant_id=ctx.tenant_id, **values)
                db.add(item)
                result = "created"
            else:
                for key, value in values.items():
                    setattr(item, key, value)
            item.completed_at = (item.completed_at or datetime.now(timezone.utc)) if status == "completed" else None
            return result
        ctx.run(filename, row, action)


# ---- cotizaciones (una fila por partida)

QUOTE_COLUMNS = [
    ("folio", "Folio"), ("cliente_email", "Correo del cliente"), ("cliente", "Cliente"), ("oportunidad_id", "ID de oportunidad"),
    ("oportunidad", "Oportunidad"), ("responsable_email", "Correo del responsable"), ("fecha_emision", "Fecha de emisión"),
    ("vigencia", "Vigencia"), ("moneda", "Moneda"), ("estado", "Estado"), ("notas", "Notas"), ("partida", "Partida"),
    ("producto_codigo", "Código de producto"), ("descripcion", "Descripción"), ("cantidad", "Cantidad"),
    ("precio_unitario", "Precio unitario"), ("descuento_porcentaje", "Descuento %"), ("importe", "Importe"), ("total", "Total"),
]


def _folio(q: Quote) -> str:
    return f"{q.prefix or 'COT'}-{q.issue_date.year}-{q.sequence:04d}"


def export_quotes(db: Session, tenant_id):
    for q in db.query(Quote).filter(Quote.tenant_id == tenant_id).order_by(Quote.sequence):
        status = "expired" if q.status == "sent" and q.valid_until < date.today() else q.status
        for x in q.items:
            yield {
                "folio": _folio(q), "cliente_email": q.client.email, "cliente": q.client.company_name,
                "oportunidad_id": str(q.opportunity_id) if q.opportunity_id else "", "oportunidad": q.opportunity.name if q.opportunity else "",
                "responsable_email": q.owner.email, "fecha_emision": q.issue_date.isoformat(), "vigencia": q.valid_until.isoformat(),
                "moneda": q.currency, "estado": QUOTE_STATUSES.get(status, status), "notas": q.notes or "", "partida": x.position,
                "producto_codigo": x.product.sku if x.product else "", "descripcion": x.description,
                "cantidad": _fmt_decimal(x.quantity), "precio_unitario": _fmt_decimal(x.unit_price),
                "descuento_porcentaje": _fmt_decimal(x.discount_percent), "importe": _fmt_decimal(x.amount), "total": _fmt_decimal(q.total),
            }


def import_quotes(ctx: ImportContext, filename: str, rows: list[Row]):
    db = ctx.db
    groups: "OrderedDict[str, list[Row]]" = OrderedDict()
    for row in rows:
        folio = (row.values.get("folio") or "").strip().upper()
        if not folio:
            ctx.error(filename, row.number, "«Folio» es obligatorio (agrupa las partidas de una cotización).")
            continue
        groups.setdefault(folio, []).append(row)
    existing = {_folio(q).upper(): q for q in db.query(Quote).filter(Quote.tenant_id == ctx.tenant_id)}

    for folio, group in groups.items():
        first = group[0]

        def action(first=first, folio=folio, group=group):
            item = existing.get(folio)
            client = ctx.client_by_email(first.text("cliente_email", "Correo del cliente"))
            opportunity = ctx.opportunity_by_id(first.uuid("oportunidad_id"))
            if opportunity and opportunity.client_id != client.id:
                raise RowError("La oportunidad no pertenece al cliente indicado.")
            owner = ctx.owner_by_email(first.text("responsable_email", "Correo del responsable")) if first.has("responsable_email") or not item else item.owner
            issue_date = first.date("fecha_emision", "Fecha de emisión") or (item.issue_date if item else date.today())
            valid_until = first.date("vigencia", "Vigencia") or (item.valid_until if item else issue_date + timedelta(days=ctx.tenant.quote_validity_days or 15))
            if valid_until < issue_date:
                raise RowError("La vigencia no puede ser anterior a la fecha de emisión.")
            currency = first.currency("moneda", item.currency if item else ctx.currency)
            status = first.choice("estado", "Estado", QUOTE_STATUSES, item.status if item else "draft")
            status = "sent" if status == "expired" else status
            lines: list[QuoteItem] = []
            for position, row in enumerate(group, start=1):
                try:
                    product = None
                    code = (row.text("producto_codigo", "Código de producto") or "").upper()
                    if code:
                        product = db.query(Product).filter(Product.tenant_id == ctx.tenant_id, Product.sku == code).first()
                        if not product:
                            raise RowError(f"No existe el producto o servicio con código {code}.")
                        if product.currency != currency:
                            raise RowError(f"«{product.name}» está en {product.currency} y la cotización en {currency}.")
                    description = row.text("descripcion", "Descripción", min_len=2, max_len=240) or (product.name if product else None)
                    if not description:
                        raise RowError("«Descripción» es obligatoria.")
                    quantity = row.decimal("cantidad", "Cantidad", default=Decimal("1"), positive=True)
                    price = row.decimal("precio_unitario", "Precio unitario", default=product.base_price if product else None, min_value=0)
                    if price is None:
                        raise RowError("«Precio unitario» es obligatorio.")
                    discount_percent = row.decimal("descuento_porcentaje", "Descuento %", default=Decimal("0"), min_value=0, max_value=100)
                except RowError as exc:
                    raise RowError(f"Fila {row.number}: {exc}")
                gross = quantity * price
                discount = gross * discount_percent / Decimal("100")
                lines.append(QuoteItem(product_id=product.id if product else None, position=position, description=description,
                    quantity=quantity, unit_price=price, gross_amount=gross.quantize(MONEY, ROUND_HALF_UP), discount_percent=discount_percent,
                    discount_amount=discount.quantize(MONEY, ROUND_HALF_UP), amount=(gross - discount).quantize(MONEY, ROUND_HALF_UP)))
            if len(lines) > 100:
                raise RowError("Una cotización admite máximo 100 partidas.")
            subtotal = sum((x.gross_amount for x in lines), Decimal("0")).quantize(MONEY, ROUND_HALF_UP)
            discount_total = sum((x.discount_amount for x in lines), Decimal("0")).quantize(MONEY, ROUND_HALF_UP)
            values = dict(client_id=client.id, opportunity_id=opportunity.id if opportunity else None, owner_user_id=owner.id,
                issue_date=issue_date, valid_until=valid_until, currency=currency, status=status,
                notes=first.long_text("notas", "Notas", 1000), discount=discount_total, tax_rate=0, subtotal=subtotal, tax=0,
                total=(subtotal - discount_total).quantize(MONEY, ROUND_HALF_UP))
            if item:
                for key, value in values.items():
                    setattr(item, key, value)
                item.items = lines
                return "updated"
            # Se conserva el número del folio si está libre; si no, se usa el siguiente.
            match = re.fullmatch(r"(?:([A-Z0-9-]{1,12})-\d{4}-)?(\d{1,9})", folio)
            used = db.query(Quote.id).filter(Quote.tenant_id == ctx.tenant_id)
            sequence = int(match.group(2)) if match else None
            if not sequence or used.filter(Quote.sequence == sequence).first():
                sequence = (db.query(func.max(Quote.sequence)).filter(Quote.tenant_id == ctx.tenant_id).scalar() or 0) + 1
            prefix = (match.group(1) if match and match.group(1) else None) or ctx.tenant.quote_prefix or "COT"
            quote = Quote(tenant_id=ctx.tenant_id, sequence=sequence, prefix=prefix, **values)
            quote.items = lines
            db.add(quote)
            return "created"

        before = len(ctx.errors)
        ctx.run(filename, first, action)
        # Los errores de partida ya indican su fila; se reubican para que el número sea exacto.
        for err in ctx.errors[before:]:
            m = re.match(r"Fila (\d+): (.*)", err["message"])
            if m:
                err["row"], err["message"] = int(m.group(1)), m.group(2)


# --------------------------------------------------------------------------- registro

ENTITIES: "OrderedDict[str, Entity]" = OrderedDict((e.key, e) for e in [
    Entity("units", "unidades_de_medida.csv", "Unidades de medida", UNIT_COLUMNS, ("nombre", "abreviatura", "tipo"),
           "products.view", ("products.update",), export_units, import_units),
    Entity("brands", "marcas.csv", "Marcas", SIMPLE_COLUMNS, ("nombre",), "products.view", ("products.update",),
           _simple_export(Brand), _simple_import(Brand, 100)),
    Entity("categories", "categorias.csv", "Categorías", SIMPLE_COLUMNS, ("nombre",), "products.view", ("products.update",),
           _simple_export(ProductCategory), _simple_import(ProductCategory, 80)),
    Entity("products", "productos.csv", "Productos", PRODUCT_COLUMNS, ("nombre", "unidad"), "products.view",
           ("products.create", "products.update"), _product_export("product"), _product_import("product")),
    Entity("services", "servicios.csv", "Servicios", PRODUCT_COLUMNS, ("nombre", "unidad"), "products.view",
           ("products.create", "products.update"), _product_export("service"), _product_import("service")),
    Entity("clients", "clientes.csv", "Clientes", CLIENT_COLUMNS, ("empresa", "contacto", "email"), "clients.view",
           ("clients.create", "clients.update"), export_clients, import_clients),
    Entity("pipelines", "pipelines_y_etapas.csv", "Pipelines y etapas", PIPELINE_COLUMNS, ("pipeline",), "opportunities.view",
           ("opportunities.update",), export_pipelines, import_pipelines),
    Entity("opportunities", "oportunidades.csv", "Oportunidades", OPPORTUNITY_COLUMNS, ("nombre", "cliente_email"),
           "opportunities.view", ("opportunities.create", "opportunities.update"), export_opportunities, import_opportunities),
    Entity("activities", "actividades.csv", "Actividades", ACTIVITY_COLUMNS, ("titulo", "tipo"), "activities.view",
           ("activities.create", "activities.update"), export_activities, import_activities),
    Entity("quotes", "cotizaciones.csv", "Cotizaciones", QUOTE_COLUMNS, ("folio", "cliente_email", "descripcion"), "quotes.view",
           ("quotes.create", "quotes.update"), export_quotes, import_quotes),
])


def can_view(entity: Entity, permissions: set[str]) -> bool:
    return entity.view_permission in permissions


def can_import(entity: Entity, permissions: set[str]) -> bool:
    return all(p in permissions for p in entity.import_permissions)


def export_entity(db: Session, tenant_id, entity: Entity) -> bytes:
    return write_csv(entity.columns, entity.export(db, tenant_id))


def template_entity(entity: Entity) -> bytes:
    return write_csv(entity.columns, [])


def export_all(db: Session, tenant_id, entities: list[Entity]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for entity in entities:
            archive.writestr(entity.filename, export_entity(db, tenant_id, entity))
    return buffer.getvalue()


def _summary(ctx: ImportContext, per_entity: list[dict]) -> dict:
    return {"applied": not ctx.errors, "created": ctx.created, "updated": ctx.updated,
            "entities": per_entity, "errors": ctx.errors[:500], "error_count": len(ctx.errors)}


def import_files(db: Session, user: User, files: list[tuple[Entity, bytes]]) -> dict:
    """Importa uno o varios CSV en una sola transacción (todo o nada)."""
    ctx = ImportContext(db=db, user=user)
    per_entity = []
    for entity, content in files:
        created, updated = ctx.created, ctx.updated
        try:
            rows = read_csv(content, entity.columns, entity.required)
        except FileError as exc:
            ctx.error(entity.filename, 1, str(exc))
            continue
        entity.importer(ctx, entity.filename, rows)
        per_entity.append({"entity": entity.key, "label": entity.label, "rows": len(rows),
                           "created": ctx.created - created, "updated": ctx.updated - updated})
    if ctx.errors:
        db.rollback()
    else:
        db.commit()
    return _summary(ctx, per_entity)


def read_zip(content: bytes) -> dict[str, bytes]:
    if len(content) > MAX_ZIP_BYTES:
        raise FileError("El archivo supera el máximo de 25 MB.")
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        raise FileError("El archivo no es un ZIP válido.")
    found: dict[str, bytes] = {}
    by_name = {e.filename: e.key for e in ENTITIES.values()}
    for info in archive.infolist():
        name = info.filename.rsplit("/", 1)[-1].lower()
        if name in by_name and info.file_size <= MAX_FILE_BYTES:
            found[by_name[name]] = archive.read(info)
    if not found:
        raise FileError("El ZIP no contiene ninguno de los CSV esperados.")
    return found
