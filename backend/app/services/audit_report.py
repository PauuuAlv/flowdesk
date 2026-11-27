"""Reporte PDF de auditoría (empresa o plataforma).

Hoja carta horizontal con una tabla: fecha y hora, acción, descripción,
usuario, módulo, IP, navegador, endpoint y los cambios (antes → después).
"""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.audit import entity_label

# Máximo de registros por reporte (para no generar PDFs enormes). Si hay más,
# el reporte lo indica y sugiere acotar los filtros.
MAX_REPORT_ROWS = 2000

NAVY = colors.HexColor("#123040")
BLUE = colors.HexColor("#275d78")
INK = colors.HexColor("#132735")
MUTED = colors.HexColor("#5f6b76")
LINE = colors.HexColor("#dfe4e8")
SOFT = colors.HexColor("#f6f8fa")

OPERATION_LABELS = {"CREATE": "Creación", "UPDATE": "Modificación", "DELETE": "Eliminación", "EVENT": "Evento"}
OPERATION_COLORS = {
    "CREATE": colors.HexColor("#1f6640"),
    "UPDATE": colors.HexColor("#7a4a0c"),
    "DELETE": colors.HexColor("#962f25"),
    "EVENT": colors.HexColor("#24506a"),
}
EVENT_LABELS = {
    "auth.login": "Inicio de sesión",
    "auth.login_failed": "Inicio de sesión fallido",
    "auth.register": "Registro por invitación",
    "auth.password_changed": "Cambio de contraseña",
    "auth.password_reset_requested": "Solicitud de restablecer contraseña",
    "auth.password_reset": "Contraseña restablecida",
    "audit.report_exported": "Reporte de auditoría",
    "tenant.created": "Empresa creada",
    "tenant.deleted": "Empresa eliminada",
    "subscription.updated": "Suscripción actualizada",
}
ACTOR_FALLBACK = {"system": "Sistema", "anonymous": "Visitante"}

_MAX_CHANGE_LINES = 8
_MAX_VALUE = 60


def resolve_timezone(name: str | None):
    if name:
        try:
            return ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            pass
    return timezone.utc


def browser_label(user_agent: str | None) -> str:
    if not user_agent:
        return "—"
    names = {
        "Edg": "Edge", "OPR": "Opera", "SamsungBrowser": "Samsung Internet", "Firefox": "Firefox",
        "FxiOS": "Firefox", "CriOS": "Chrome", "Chrome": "Chrome", "Version": "Safari",
    }
    match = re.search(r"(Edg|OPR|SamsungBrowser|Firefox|FxiOS|CriOS|Chrome|Version)/(\d+)", user_agent)
    name = f"{names[match.group(1)]} {match.group(2)}" if match else user_agent.split(" ")[0][:30]
    for pattern, os_name in (("Windows", "Windows"), ("Android", "Android"), ("iPhone|iPad", "iOS"),
                             ("Mac OS X", "macOS"), ("Linux", "Linux")):
        if re.search(pattern, user_agent):
            return f"{name} · {os_name}"
    return name


def _short(value) -> str:
    if value is None or value == "" or value == {} or value == []:
        return "—"
    if value is True:
        return "Sí"
    if value is False:
        return "No"
    if isinstance(value, dict):
        # Cambios guardados como {"before": x, "after": y} en eventos manuales.
        if set(value) == {"before", "after"}:
            return f"{_short(value['before'])} -> {_short(value['after'])}"
        text = ", ".join(f"{key}: {_short(item)}" for key, item in value.items())
    elif isinstance(value, (list, tuple)):
        text = ", ".join(str(item) for item in value) if value else "—"
    else:
        text = str(value)
    return text if len(text) <= _MAX_VALUE else text[:_MAX_VALUE] + "…"


def changes_text(item) -> str:
    """Resumen de cambios en texto plano (una línea por campo)."""
    before = item.before_data or {}
    after = item.after_data or ({} if item.operation != "EVENT" else (item.details or {}))
    if item.operation == "UPDATE":
        lines = [f"{key}: {_short(before.get(key))} -> {_short(after.get(key))}" for key in after]
    elif item.operation == "DELETE":
        lines = [f"{key}: {_short(value)}" for key, value in before.items()]
    else:
        lines = [f"{key}: {_short(value)}" for key, value in after.items()]
    if len(lines) > _MAX_CHANGE_LINES:
        extra = len(lines) - _MAX_CHANGE_LINES
        lines = lines[:_MAX_CHANGE_LINES] + [f"… y {extra} campo(s) más"]
    return "\n".join(lines) or "—"


def build_audit_pdf(
    *,
    title: str,
    subtitle: str,
    items: list,
    total: int,
    filters: list[tuple[str, str]],
    generated_by: str,
    tz,
    logo_path: Path | None = None,
    show_tenant: bool = False,
    tenant_names: dict | None = None,
) -> io.BytesIO:
    tenant_names = tenant_names or {}
    buffer = io.BytesIO()
    page_size = landscape(letter)
    styles = getSampleStyleSheet()
    body = ParagraphStyle("AuditBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2,
                          leading=9, textColor=INK)
    small = ParagraphStyle("AuditSmall", parent=body, fontSize=6.5, leading=8, textColor=MUTED)
    header = ParagraphStyle("AuditHeader", parent=body, fontName="Helvetica-Bold", fontSize=6.8,
                            leading=8.5, textColor=colors.white)
    heading = ParagraphStyle("AuditTitle", parent=styles["Heading1"], fontName="Helvetica-Bold",
                             fontSize=18, leading=22, textColor=NAVY, spaceAfter=2)
    meta = ParagraphStyle("AuditMeta", parent=body, fontSize=8.5, leading=12, textColor=MUTED)

    generated_at = datetime.now(tz).strftime("%d/%m/%Y %H:%M")
    doc = SimpleDocTemplate(
        buffer, pagesize=page_size, leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=2.7 * cm, bottomMargin=1.5 * cm, title=title, author="Flowdesk",
    )

    def decorate(canvas, document):
        width, height = page_size
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 1.9 * cm, width, 1.9 * cm, fill=1, stroke=0)
        if logo_path and logo_path.exists():
            logo = ImageReader(str(logo_path))
            source_width, source_height = logo.getSize()
            box_width, box_height = 3.4 * cm, 1.2 * cm
            scale = min(box_width / source_width, box_height / source_height)
            canvas.setFillColor(colors.white)
            canvas.roundRect(1.2 * cm, height - 1.55 * cm, box_width, box_height, 0.12 * cm, fill=1, stroke=0)
            canvas.drawImage(
                logo, 1.2 * cm + (box_width - source_width * scale) / 2,
                height - 1.55 * cm + (box_height - source_height * scale) / 2,
                width=source_width * scale, height=source_height * scale, mask="auto",
            )
        else:
            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 16)
            canvas.drawString(1.2 * cm, height - 1.15 * cm, "FLOWDESK")
        canvas.setFillColor(colors.HexColor("#a9c9d8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(width - 1.2 * cm, height - 1.1 * cm, "Reporte de auditoría")
        canvas.setStrokeColor(LINE)
        canvas.line(1.2 * cm, 1.1 * cm, width - 1.2 * cm, 1.1 * cm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(1.2 * cm, 0.7 * cm, f"Generado el {generated_at} por {generated_by}")
        canvas.drawRightString(width - 1.2 * cm, 0.7 * cm, f"Página {document.page}")
        canvas.restoreState()

    story = [Paragraph(escape(title), heading), Paragraph(escape(subtitle), meta)]
    shown = len(items)
    summary = f"{total} registro(s) encontrados"
    if shown < total:
        summary += f"; se incluyen los {shown} más recientes. Acota los filtros para ver el resto."
    story.append(Paragraph(escape(summary), meta))
    if filters:
        text = " · ".join(f"<b>{escape(label)}:</b> {escape(value)}" for label, value in filters)
        story.append(Paragraph(f"Filtros: {text}", meta))
    story.append(Spacer(1, 0.35 * cm))

    columns = ["Fecha y hora", "Acción", "Descripción", "Usuario", "Módulo", "IP", "Navegador", "Endpoint", "Cambios"]
    widths = [2.2, 2.1, 4.6, 3.6, 2.4, 2.0, 2.4, 3.6, 5.0]
    if show_tenant:
        columns.insert(5, "Empresa")
        widths = [2.1, 2.0, 4.0, 3.2, 2.2, 2.4, 1.9, 2.3, 3.2, 4.5]

    def cell(text, style=body):
        return Paragraph(escape(text or "—").replace("\n", "<br/>"), style)

    rows = [[Paragraph(name, header) for name in columns]]
    for item in items:
        if item.operation == "EVENT":
            action = EVENT_LABELS.get(item.action, OPERATION_LABELS["EVENT"])
        else:
            action = OPERATION_LABELS.get(item.operation, item.operation)
        action_style = ParagraphStyle(f"op-{item.operation}", parent=body, fontName="Helvetica-Bold",
                                      textColor=OPERATION_COLORS.get(item.operation, INK))
        actor = item.actor_email or ACTOR_FALLBACK.get(item.actor_type, "—")
        endpoint = f"{item.http_method or ''} {item.endpoint or ''}".strip()
        row = [
            cell(item.created_at.astimezone(tz).strftime("%d/%m/%Y\n%H:%M:%S")),
            cell(action, action_style),
            cell(item.description),
            cell(actor),
            cell(entity_label(item.entity) or "—"),
            cell(item.ip_address),
            cell(browser_label(item.user_agent)),
            cell(endpoint, small),
            cell(changes_text(item), small),
        ]
        if show_tenant:
            name = tenant_names.get(item.tenant_id) or (item.details or {}).get("tenant_name")
            row.insert(5, cell(name or ("—" if not item.tenant_id else str(item.tenant_id)[:8])))
        rows.append(row)

    if len(rows) == 1:
        story.append(Paragraph("No hay registros que coincidan con los filtros.", meta))
    else:
        # Las proporciones se ajustan al ancho útil de la página.
        scale = doc.width / sum(widths)
        table = Table(rows, colWidths=[w * scale for w in widths], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            ("BOX", (0, 0), (-1, -1), 0.4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(table)

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    buffer.seek(0)
    return buffer
