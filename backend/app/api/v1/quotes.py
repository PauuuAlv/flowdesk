import io
import uuid
from datetime import date
from fastapi import APIRouter,Depends,HTTPException,status
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph,Spacer,Table,TableStyle,SimpleDocTemplate
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.quote import Quote,QuoteItem
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.quote import QuoteItemResponse,QuoteResponse,SaveQuoteRequest,UpdateQuoteStatusRequest,calculate_totals
from app.security.permissions import require_permission

router=APIRouter()


def _get(quote_id:uuid.UUID,tenant_id,db:Session):
    item=db.query(Quote).filter(Quote.id==quote_id,Quote.tenant_id==tenant_id).first()
    if not item:raise HTTPException(404,"Quote not found")
    return item


def _relations(payload:SaveQuoteRequest,tenant_id,db:Session):
    try:client_id=uuid.UUID(payload.client_id);owner_id=uuid.UUID(payload.owner_user_id);opportunity_id=uuid.UUID(payload.opportunity_id) if payload.opportunity_id else None
    except ValueError as exc:raise HTTPException(422,"Invalid identifier") from exc
    client=db.query(Client).filter(Client.id==client_id,Client.tenant_id==tenant_id).first();owner=db.query(User).filter(User.id==owner_id,User.tenant_id==tenant_id,User.status=="active").first();opportunity=None
    if opportunity_id:opportunity=db.query(Opportunity).filter(Opportunity.id==opportunity_id,Opportunity.tenant_id==tenant_id).first()
    if not client:raise HTTPException(404,"Client not found")
    if not owner:raise HTTPException(404,"Owner not found")
    if opportunity_id and not opportunity:raise HTTPException(404,"Opportunity not found")
    if opportunity and opportunity.client_id!=client.id:raise HTTPException(409,"Opportunity does not belong to client")
    return client,owner,opportunity


def _effective_status(item:Quote):return "expired" if item.status=="sent" and item.valid_until<date.today() else item.status
def _serialize(item:Quote,tenant_name:str):
    return QuoteResponse(id=str(item.id),folio=f"COT-{item.issue_date.year}-{item.sequence:04d}",tenant_name=tenant_name,client_id=str(item.client_id),client_name=item.client.company_name,client_contact=item.client.contact_name,client_email=item.client.email,opportunity_id=str(item.opportunity_id) if item.opportunity_id else None,opportunity_name=item.opportunity.name if item.opportunity else None,owner_user_id=str(item.owner_user_id),owner_name=item.owner.full_name or item.owner.email,issue_date=item.issue_date,valid_until=item.valid_until,currency=item.currency,discount=item.discount,tax_rate=item.tax_rate,subtotal=item.subtotal,tax=item.tax,total=item.total,status=_effective_status(item),notes=item.notes,items=[QuoteItemResponse(id=str(x.id),position=x.position,description=x.description,quantity=x.quantity,unit_price=x.unit_price,amount=x.amount) for x in item.items],created_at=item.created_at,updated_at=item.updated_at)

def _tenant_name(tenant_id,db:Session):
    tenant=db.query(Tenant).filter(Tenant.id==tenant_id).first();return tenant.name if tenant else "Empresa"


@router.get("",response_model=list[QuoteResponse])
def list_quotes(db:Session=Depends(get_db),user:User=Depends(require_permission("quotes.view"))):return [_serialize(x,_tenant_name(user.tenant_id,db)) for x in db.query(Quote).filter(Quote.tenant_id==user.tenant_id).order_by(Quote.created_at.desc()).all()]


@router.post("",response_model=QuoteResponse,status_code=status.HTTP_201_CREATED)
def create_quote(payload:SaveQuoteRequest,db:Session=Depends(get_db),user:User=Depends(require_permission("quotes.create"))):
    client,owner,opportunity=_relations(payload,user.tenant_id,db);subtotal,tax,total=calculate_totals(payload);sequence=(db.query(func.max(Quote.sequence)).filter(Quote.tenant_id==user.tenant_id).scalar() or 0)+1
    item=Quote(tenant_id=user.tenant_id,sequence=sequence,client_id=client.id,owner_user_id=owner.id,opportunity_id=opportunity.id if opportunity else None,issue_date=payload.issue_date,valid_until=payload.valid_until,discount=payload.discount,tax_rate=payload.tax_rate,subtotal=subtotal,tax=tax,total=total,notes=payload.notes,status="draft")
    item.items=[QuoteItem(position=i,description=x.description,quantity=x.quantity,unit_price=x.unit_price,amount=x.quantity*x.unit_price) for i,x in enumerate(payload.items,1)];db.add(item);db.commit();db.refresh(item);return _serialize(item,_tenant_name(user.tenant_id,db))


@router.get("/{quote_id}",response_model=QuoteResponse)
def get_quote(quote_id:uuid.UUID,db:Session=Depends(get_db),user:User=Depends(require_permission("quotes.view"))):return _serialize(_get(quote_id,user.tenant_id,db),_tenant_name(user.tenant_id,db))

@router.get("/{quote_id}/pdf")
def quote_pdf(quote_id:uuid.UUID,db:Session=Depends(get_db),user:User=Depends(require_permission("quotes.view"))):
    data=_serialize(_get(quote_id,user.tenant_id,db),_tenant_name(user.tenant_id,db))
    buffer=io.BytesIO()
    navy=colors.HexColor("#123040")
    blue=colors.HexColor("#275d78")
    gold=colors.HexColor("#d78d36")
    ink=colors.HexColor("#132735")
    muted=colors.HexColor("#5f6b76")
    line=colors.HexColor("#dfe4e8")
    soft=colors.HexColor("#f3f6f8")
    white=colors.white
    styles=getSampleStyleSheet()
    body=ParagraphStyle("QuoteBody",parent=styles["BodyText"],fontName="Helvetica",fontSize=9.5,leading=14,textColor=ink)
    small=ParagraphStyle("QuoteSmall",parent=body,fontSize=8,leading=11,textColor=muted)
    label=ParagraphStyle("QuoteLabel",parent=small,fontName="Helvetica-Bold",fontSize=7.5,leading=10,textColor=blue,spaceAfter=3)
    table_header=ParagraphStyle("QuoteTableHeader",parent=label,textColor=white)
    title=ParagraphStyle("QuoteTitle",parent=styles["Heading1"],fontName="Helvetica-Bold",fontSize=22,leading=26,textColor=navy,spaceAfter=4)
    right=ParagraphStyle("QuoteRight",parent=body,alignment=TA_RIGHT)
    total_style=ParagraphStyle("QuoteTotal",parent=right,fontName="Helvetica-Bold",fontSize=13,leading=16,textColor=white)
    doc=SimpleDocTemplate(buffer,pagesize=letter,rightMargin=1.5*cm,leftMargin=1.5*cm,topMargin=3.0*cm,bottomMargin=1.7*cm)

    def decorate_page(canvas,document):
        width,height=letter
        canvas.saveState()
        canvas.setFillColor(navy)
        canvas.rect(0,height-2.15*cm,width,2.15*cm,fill=1,stroke=0)
        canvas.setFillColor(white)
        canvas.setFont("Helvetica-Bold",17)
        canvas.drawString(1.5*cm,height-1.25*cm,"FLOWDESK")
        canvas.setFillColor(colors.HexColor("#a9c9d8"))
        canvas.setFont("Helvetica",8)
        canvas.drawRightString(width-1.5*cm,height-1.2*cm,"CRM SaaS multiempresa")
        canvas.setStrokeColor(line)
        canvas.line(1.5*cm,1.25*cm,width-1.5*cm,1.25*cm)
        canvas.setFillColor(muted)
        canvas.setFont("Helvetica",7.5)
        canvas.drawRightString(width-1.5*cm,.75*cm,f"Página {document.page}")
        canvas.restoreState()

    status_labels={"draft":"BORRADOR","sent":"ENVIADA","accepted":"ACEPTADA","rejected":"RECHAZADA","expired":"VENCIDA"}
    heading=Table([
        [Paragraph(f"Cotización <font color='#275d78'>{data.folio}</font>",title),Paragraph(f"<b>{status_labels.get(data.status,data.status.upper())}</b>",right)],
        [Paragraph(data.tenant_name,body),""]
    ],colWidths=[12.5*cm,5.0*cm])
    heading.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(1,0),(1,0),soft),("BOX",(1,0),(1,0),.5,line),("LEFTPADDING",(1,0),(1,0),10),("RIGHTPADDING",(1,0),(1,0),10),("TOPPADDING",(1,0),(1,0),7),("BOTTOMPADDING",(1,0),(1,0),7)]))

    client_card=Table([
        [Paragraph("PREPARADA PARA",label),Paragraph("VIGENCIA Y RESPONSABLE",label)],
        [Paragraph(f"<b>{data.client_name}</b><br/>{data.client_contact or 'Sin contacto registrado'}<br/><font color='#5f6b76'>{data.client_email or 'Sin correo registrado'}</font>",body),Paragraph(f"Emisión: <b>{data.issue_date.strftime('%d/%m/%Y')}</b><br/>Válida hasta: <b>{data.valid_until.strftime('%d/%m/%Y')}</b><br/>Responsable: <b>{data.owner_name}</b>",body)]
    ],colWidths=[9.0*cm,8.5*cm])
    client_card.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),soft),("BOX",(0,0),(-1,-1),.6,line),("LINEBEFORE",(1,0),(1,-1),.6,line),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(-1,0),10),("BOTTOMPADDING",(0,0),(-1,0),2),("TOPPADDING",(0,1),(-1,1),2),("BOTTOMPADDING",(0,1),(-1,1),11)]))

    rows=[[Paragraph("DESCRIPCIÓN",table_header),Paragraph("CANT.",table_header),Paragraph("PRECIO UNITARIO",table_header),Paragraph("IMPORTE",table_header)]]
    rows += [[Paragraph(x.description,body),f"{x.quantity:,.2f}",f"${x.unit_price:,.2f}",f"${x.amount:,.2f}"] for x in data.items]
    items_table=Table(rows,colWidths=[8.2*cm,2.2*cm,3.5*cm,3.6*cm],repeatRows=1)
    item_style=[("BACKGROUND",(0,0),(-1,0),navy),("TEXTCOLOR",(0,0),(-1,0),white),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,1),(-1,-1),"RIGHT"),("GRID",(0,0),(-1,-1),.35,line),("LEFTPADDING",(0,0),(-1,-1),9),("RIGHTPADDING",(0,0),(-1,-1),9),("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8)]
    for row_index in range(2,len(rows),2):item_style.append(("BACKGROUND",(0,row_index),(-1,row_index),colors.HexColor("#f8fafb")))
    items_table.setStyle(TableStyle(item_style))

    totals=Table([
        [Paragraph("Subtotal",body),Paragraph(f"${data.subtotal:,.2f}",right)],
        [Paragraph("Descuento",body),Paragraph(f"-${data.discount:,.2f}",right)],
        [Paragraph(f"IVA ({data.tax_rate:,.2f}%)",body),Paragraph(f"${data.tax:,.2f}",right)],
        [Paragraph("TOTAL",total_style),Paragraph(f"${data.total:,.2f} {data.currency}",total_style)]
    ],colWidths=[3.8*cm,4.7*cm])
    totals.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,2),soft),("BACKGROUND",(0,3),(-1,3),blue),("BOX",(0,0),(-1,-1),.6,line),("LINEABOVE",(0,3),(-1,3),1,gold),("LEFTPADDING",(0,0),(-1,-1),11),("RIGHTPADDING",(0,0),(-1,-1),11),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    totals_wrapper=Table([["",totals]],colWidths=[9.0*cm,8.5*cm])
    totals_wrapper.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))

    story=[heading,Spacer(1,14),client_card,Spacer(1,18),items_table,Spacer(1,14),totals_wrapper]
    if data.notes:
        notes=Table([[Paragraph("NOTAS",label)],[Paragraph(data.notes,body)]],colWidths=[17.5*cm])
        notes.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#fff8ef")),("BOX",(0,0),(-1,-1),.6,colors.HexColor("#efd1a8")),("LEFTPADDING",(0,0),(-1,-1),11),("RIGHTPADDING",(0,0),(-1,-1),11),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
        story.extend([Spacer(1,16),notes])
    doc.build(story,onFirstPage=decorate_page,onLaterPages=decorate_page)
    buffer.seek(0)
    return StreamingResponse(buffer,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="{data.folio}.pdf"'})


@router.patch("/{quote_id}",response_model=QuoteResponse)
def update_quote(quote_id:uuid.UUID,payload:SaveQuoteRequest,db:Session=Depends(get_db),user:User=Depends(require_permission("quotes.update"))):
    item=_get(quote_id,user.tenant_id,db)
    if item.status!="draft":raise HTTPException(409,"Only draft quotes can be edited")
    client,owner,opportunity=_relations(payload,user.tenant_id,db);subtotal,tax,total=calculate_totals(payload)
    for key,value in {"client_id":client.id,"owner_user_id":owner.id,"opportunity_id":opportunity.id if opportunity else None,"issue_date":payload.issue_date,"valid_until":payload.valid_until,"discount":payload.discount,"tax_rate":payload.tax_rate,"subtotal":subtotal,"tax":tax,"total":total,"notes":payload.notes}.items():setattr(item,key,value)
    item.items=[QuoteItem(position=i,description=x.description,quantity=x.quantity,unit_price=x.unit_price,amount=x.quantity*x.unit_price) for i,x in enumerate(payload.items,1)];db.commit();db.refresh(item);return _serialize(item,_tenant_name(user.tenant_id,db))


@router.patch("/{quote_id}/status",response_model=QuoteResponse)
def update_status(quote_id:uuid.UUID,payload:UpdateQuoteStatusRequest,db:Session=Depends(get_db),user:User=Depends(require_permission("quotes.status"))):
    item=_get(quote_id,user.tenant_id,db);allowed={"draft":{"sent"},"sent":{"accepted","rejected"}}
    if payload.status not in allowed.get(item.status,set()):raise HTTPException(409,"Invalid quote status transition")
    item.status=payload.status;db.commit();db.refresh(item);return _serialize(item,_tenant_name(user.tenant_id,db))
