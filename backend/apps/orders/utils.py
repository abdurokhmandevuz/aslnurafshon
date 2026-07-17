import os
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_receipt_pdf(order) -> str:
    """
    Generate PDF receipt for the given Order object.
    Returns the absolute path to the generated PDF file.
    """
    # Ensure media directory exists
    pdf_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
    os.makedirs(pdf_dir, exist_ok=True)
    
    pdf_path = os.path.join(pdf_dir, f'chek_order_{order.id}.pdf')
    
    doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                            rightMargin=40, leftMargin=40,
                            topMargin=40, bottomMargin=40)
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#4A2E1E'), # Primary color
        spaceAfter=15,
        alignment=1 # Center
    )
    
    header_style = ParagraphStyle(
        'ReceiptHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2E2E2E')
    )
    
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12
    )

    story = []
    
    # 1. Shop name / Logo
    story.append(Paragraph("Asl Nurafshon", title_style))
    story.append(Spacer(1, 10))
    
    # 2. Receipt metadata table
    meta_data = [
        [
            Paragraph(f"<b>Buyurtma:</b> #{order.id}", header_style),
            Paragraph(f"<b>Sana:</b> {order.created_at.strftime('%d.%m.%Y %H:%M')}", header_style)
        ],
        [
            Paragraph(f"<b>Mijoz:</b> {order.user.full_name}", header_style),
            Paragraph(f"<b>Telefon:</b> {getattr(order.user, 'phone_number', '') or order.user.phone or ''}", header_style)
        ],
        [
            Paragraph(f"<b>To'lov usuli:</b> {order.get_payment_method_display()}", header_style),
            Paragraph(f"<b>To'lov holati:</b> {order.get_payment_status_display()}", header_style)
        ],
        [
            Paragraph(f"<b>Yetkazish manzili:</b> {order.address.address_text if order.address else 'Olib ketish'}", header_style),
            Paragraph("", header_style)
        ]
    ]
    
    meta_table = Table(meta_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 20))
    
    # 3. Items list table
    items_data = [[
        Paragraph("<b>№</b>", table_header_style),
        Paragraph("<b>Mahsulot nomi</b>", table_header_style),
        Paragraph("<b>Miqdor</b>", table_header_style),
        Paragraph("<b>Narxi (so'm)</b>", table_header_style),
        Paragraph("<b>Jami (so'm)</b>", table_header_style)
    ]]
    
    for idx, item in enumerate(order.items.all(), 1):
        items_data.append([
            Paragraph(str(idx), table_cell_style),
            Paragraph(f"{item.product_name_snapshot} ({item.variant_weight_snapshot})", table_cell_style),
            Paragraph(str(item.quantity), table_cell_style),
            Paragraph(f"{item.price_at_order:,}", table_cell_style),
            Paragraph(f"{item.line_total:,}", table_cell_style)
        ])
        
    items_table = Table(items_data, colWidths=[30, 250, 50, 90, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4A2E1E')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0E0E0')),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 15))
    
    # 4. Summary totals
    summary_data = [
        [Paragraph("<b>Mahsulotlar summasi:</b>", table_cell_style), Paragraph(f"{order.subtotal:,} so'm", table_cell_style)],
    ]
    if order.discount_amount > 0:
        summary_data.append([Paragraph("<b>Chegirma:</b>", table_cell_style), Paragraph(f"-{order.discount_amount:,} so'm", table_cell_style)])
    if order.delivery_fee > 0:
        summary_data.append([Paragraph("<b>Yetkazib berish:</b>", table_cell_style), Paragraph(f"{order.delivery_fee:,} so'm", table_cell_style)])
        
    summary_data.append([Paragraph("<b>Jami to'lov:</b>", ParagraphStyle('TotalLabel', parent=table_cell_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#4A2E1E'))),
                         Paragraph(f"<b>{order.total:,} so'm</b>", ParagraphStyle('TotalVal', parent=table_cell_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#4A2E1E')))])
    
    summary_table = Table(summary_data, colWidths=[150, 100])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    
    # Wrap in a wrapper table to push it to the right
    wrapper_table = Table([[ "", summary_table ]], colWidths=[270, 250])
    wrapper_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(wrapper_table)
    story.append(Spacer(1, 30))
    
    # 5. Footer
    footer_style = ParagraphStyle(
        'ReceiptFooter',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#777777'),
        alignment=1
    )
    story.append(Paragraph("Xaridingiz uchun rahmat! ☕", footer_style))
    
    doc.build(story)
    return pdf_path
