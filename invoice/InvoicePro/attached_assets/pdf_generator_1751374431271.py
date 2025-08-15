import io
import os
import config
from datetime import datetime
from types import SimpleNamespace
from flask import send_file
import xlsxwriter
from models import db, Invoice

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas

from num2words import num2words
from utils import get_client_invoice_details, number_to_words
from models import Company



def number_to_words(n):
    return num2words(n, lang='en_IN').replace(',', '').title()

def generate_invoice_pdf(invoice):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.3 * inch,
        bottomMargin=0.3 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    content = []

    # Custom styles
    center_title = ParagraphStyle(name='CenterTitle', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold')
    small_right = ParagraphStyle(name='SmallRight', fontSize=8, alignment=TA_RIGHT, fontName='Helvetica')
    normal = ParagraphStyle(name='Normal', fontSize=9, fontName='Helvetica')

    triplicate_para = Paragraph("<font size=8>(TRIPLICATE FOR RECIPIENT)</font>", small_right)
    triplicate_table = Table([[triplicate_para]], colWidths=[7.1 * inch])
    triplicate_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    content.append(triplicate_table)

    # Title
    content.append(Paragraph("PROFORMA INVOICE", center_title))
    content.append(Spacer(1, 6))

    # Header with invoice no and company
    header_data = [[
        Paragraph(f"<b>Invoice No:</b> {invoice.invoice_number}<br/><b>Date:</b> {invoice.invoice_date.strftime('%d-%m-%Y')}", styles['Normal']),
        Paragraph(f"<b>{config.COMPANY_NAME}</b><br/><font size=9>{config.ADDRESS}</font>", small_right)
    ]]
    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, colors.black, None, (2, 2, 2, 2)),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    content.append(header_table)
    content.append(Spacer(1, 10))

    # Client & Company info
    """ company_dict = {
    "name": "OMPS ENGINEERING INDUSTRIES",
    "address": "No. 39, 9th Street, Kamaraj Nagar, Avadi, Chennai - 600071",
    "gstin": "33AAFF01969B1Z1",
    "pan": "AAFF01969B1",
    "tin": "33436486057",
    "phone": "044 - 4853 397, 9884544409, 9884533309",
    "email": "ompsindustries@gmail.com"
    }
    company = SimpleNamespace(**company_dict) """
    client = invoice.client
    """ company = invoice.company or Company.query.first() """

    info_data = [[
        Paragraph("<b>To</b><br/>" +
                  f"{client.name}<br/>{client.address}<br/>{client.city}, {client.state} - {client.pincode}<br/>Tamil Nadu, India<br/><b>GSTIN:</b> {client.gstin or ''}", normal),
        Paragraph("<b>Our Details</b><br/>" +
                  f"<b>GSTIN:</b> {config.gstin}<br/><b>PAN:</b> {config.pan}<br/><b>TIN:</b> {config.tin or '33436486057'}", normal)
    ]]
    info_table = Table(info_data, colWidths=[3.5 * inch, 3.5 * inch])
    info_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.6, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke)
    ]))
    content.append(info_table)
    content.append(Spacer(1, 10))

    # Line items
    items_data = [['Sl No', 'HSN Code', 'Product Name / Description', 'Qty', 'Unit Price', 'Total']]
    for item in invoice.line_items:
        items_data.append([
            str(item.sr_no),
            item.hsn_code or '',
            Paragraph(item.description.replace('\n', '<br/>'), normal),
            str(item.quantity),
            f"Rs. {item.unit_price:,.2f}",
            f"Rs. {item.total_amount:,.2f}"
        ])
    while len(items_data) < 18:
        items_data.append([''] * 6)

    items_table = Table(items_data, colWidths=[0.5*inch, 0.9*inch, 3.2*inch, 0.6*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (3, -1), 'CENTER'),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT')
    ]))
    content.append(items_table)
    content.append(Spacer(1, 8))

    # Totals
    tax_data = [
        ['Party GST NO:', client.gstin or '', 'Sub Total', f"Rs. {invoice.subtotal:,.2f}"],
        ['Ref. Dt:', '________', 'SGST 9%', f"Rs. {invoice.sgst:,.2f}"],
        ['Ref. No:', '_________', 'CGST 9%', f"Rs. {invoice.cgst:,.2f}"],
        ['PO No:', '________', 'Round off / Freight', f"Rs. 0.00"],
        ['Date:', '________', 'Grand Total', f"Rs. {invoice.total_amount:,.2f}"]
    ]
    tax_table = Table(tax_data, colWidths=[1.5*inch, 2*inch, 2*inch, 1.5*inch])
    tax_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    content.append(tax_table)
    content.append(Spacer(1, 8))

    # Amount in words and Vehicle No
    words = number_to_words(int(invoice.total_amount)) + " only"
    words_table = Table([
        ['Vehicle No:', '___________________', f'Rupees {words}']
    ], colWidths=[1.1*inch, 2.4*inch, 3.5*inch])
    words_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica')
    ]))
    content.append(words_table)
    content.append(Spacer(1, 20))

    # Bank + Signature
    bank_sign_data = [
        ["OUR BANK DETAILS", "", ""],
        ["Bank Name : UNION BANK OF INDIA", "", f"For {config.COMPANY_NAME}"],
        ["A/C No. : 54780514000101", "", ""],
        ["A/C Name : OMPS Engineering Industries", "", ""],
        ["IFSC Code : UBIN081042", "", ""],
        ["Branch : AVADI", "", ""],
        ["", "", "Authorised Signatory"]
    ]
    bank_sign_table = Table(bank_sign_data, colWidths=[3.5*inch, 0.3*inch, 3.2*inch])
    bank_sign_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.4, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (2, 1), (2, 1), 'Helvetica-Bold'),
        ('FONTNAME', (2, -1), (2, -1), 'Helvetica-Bold'),
    ]))
    content.append(bank_sign_table)

    # Footer
    footer = Paragraph(
        f"Ph. {config.PHONE} | Email: {config.EMAIL}",
        ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, fontName='Helvetica')
    )
    content.append(Spacer(1, 10))
    content.append(footer)

    doc.build(content)
    buffer.seek(0)
    return buffer

def generate_challan_pdf(challan):

    """Generate a delivery challan PDF matching HTML layout."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ChallanTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.black,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName="Helvetica-Bold",
    )
    section_title_style = ParagraphStyle(
        "SectionTitle",
        fontSize=10,
        backColor=colors.black,
        textColor=colors.white,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        leading=12,
    )
    small_text_style = ParagraphStyle(
        "SmallText",
        fontSize=8,
        alignment=TA_LEFT,
        fontName="Helvetica"
    )
    content = []

    # Title
    content.append(Paragraph("DELIVERY CHALLAN", title_style))
    content.append(Spacer(1, 12))

    # Header (Challan No, Date, Company name/address)
    company = SimpleNamespace(
    name=config.COMPANY_NAME,
    address=config.ADDRESS,
    gstin=config.gstin,
    pan=config.pan,
    tin=config.tin
    )

    client = challan.client

    header_data = [
        [
            Paragraph(f"<b>Challan No:</b> {challan.challan_number}", styles["Normal"]),
            Paragraph(f"<b>Date:</b> {challan.challan_date.strftime('%d-%m-%Y')}", styles["Normal"]),
        ],
        [
            Paragraph(f"<b>{config.COMPANY_NAME}</b>", styles["Heading4"]),
            Paragraph(config.ADDRESS, small_text_style),
        ],
    ]

    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(
        TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    content.append(header_table)
    content.append(Spacer(1, 12))

    # To / Our Details
    details_data = [
        [
            Paragraph("To", section_title_style),
            Paragraph("Our Details", section_title_style)
        ],
        [
            Paragraph(
                f"<b>{client.name}</b><br/>{client.address}<br/>{client.city}, {client.state} - {client.pincode}<br/>"
                f"Tamil Nadu, India<br/><b>GSTIN:</b> {client.gstin or ''}",
                styles["Normal"]
            ),
            Paragraph(
            f"<b>GSTIN:</b> {company.gstin}<br/>"
            f"<b>PAN:</b> {company.pan}<br/>"
            f"<b>TIN:</b> {company.tin}",
            styles["Normal"]
            ),
        ]
    ]
    info_table = Table(details_data, colWidths=[3.5 * inch, 3.5 * inch])
    info_table.setStyle(
        TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ])
    )
    content.append(info_table)
    content.append(Spacer(1, 12))

    # Line Items Table
    item_data = [["Sl No", "HSN Code", "Product Name / Description", "Qty", "Unit Price", "Total"]]
    total = 0
    for item in challan.line_items:
        item_data.append([
            str(item.sr_no),
            item.hsn_code,
            item.description.replace("\n", "<br/>"),
            str(item.quantity),
            f"Rs. {item.unit_price:,.2f}",
            f"Rs. {item.total_amount:,.2f}",
        ])
        total += item.total_amount

    item_table = Table(item_data, colWidths=[0.6*inch, 1*inch, 3*inch, 0.8*inch, 1*inch, 1*inch])
    item_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
    ]))
    content.append(item_table)
    content.append(Spacer(1, 12))

    # Summary Section
    summary_data = [
        ["Vehicle No:", "___________________"],
        ["Amount in Words:", f"Rupees {int(total)} only"]
    ]
    summary_table = Table(summary_data, colWidths=[2.5 * inch, 4.5 * inch])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 20))

    # Signature and Bank Section
    bank_data = [
        [
           Paragraph(
                f"<b>OUR BANK DETAILS</b><br/>Bank Name: {config.BANK_NAME}<br/>"
                f"A/C No.: {config.ACCOUNT_NO}<br/>A/C Name: {config.ACCOUNT_NAME}<br/>"
                f"IFSC Code: {config.IFSC_CODE}<br/>Branch: {config.BRANCH}", styles["Normal"]
            ),

            "",
            Paragraph("Authorised Signatory", styles["Normal"])
        ]
    ]
    bank_table = Table(bank_data, colWidths=[3.5 * inch, 1.5 * inch, 2 * inch])
    bank_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
    ]))
    content.append(bank_table)
    content.append(Spacer(1, 12))

    # Footer contact info
    contact_info = Paragraph(
        f"Ph. {config.PHONE} | Email: {config.EMAIL}",
        ParagraphStyle("Footer", fontSize=8, alignment=TA_CENTER, fontName="Helvetica")
    )
    content.append(contact_info)

    doc.build(content)
    buffer.seek(0)
    return buffer

def generate_report_pdf(invoice):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )

    styles = getSampleStyleSheet()
    content = []

    title_style = ParagraphStyle('title', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold')
    content.append(Paragraph("PROFORMA INVOICE", title_style))
    content.append(Spacer(1, 12))

    # Header Table (Dashed Border)
    header_data = [
        [
            Paragraph(f"<b>Invoice No:</b> {invoice.invoice_number}<br/><b>Date:</b> {invoice.invoice_date.strftime('%d-%m-%Y')}<br/><font size=8>(TRIPLICATE FOR RECIPIENT)</font>", styles['Normal']),
            Paragraph(f"<b>{config.COMPANY_NAME}</b><br/><font size=10>{config.ADDRESS}</font>", ParagraphStyle(name='Right', alignment=TA_RIGHT, fontSize=10))
        ]
    ]

    header_table = Table(header_data, colWidths=[3.4*inch, 3.4*inch])
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBEFORE', (1, 0), (1, 0), 1, colors.black),
    ]))
    content.append(header_table)
    content.append(Spacer(1, 12))

    # Client & Company Details Table
    client = invoice.client
    company = SimpleNamespace(
        name=config.COMPANY_NAME,
        address=config.ADDRESS,
        gstin=config.GSTIN,
        pan=config.PAN,
        tin=config.TIN
    )


    details_data = [
        [
            Paragraph(f"<b>To</b><br/><b>{client.name}</b><br/>{client.address}<br/>{client.city}, {client.state} - {client.pincode}<br/>Tamil Nadu, India<br/><b>GSTIN:</b> {client.gstin or ''}", styles['Normal']),
           Paragraph(
                f"<b>OUR BANK DETAILS</b><br/>"
                f"Bank Name: {config.BANK_NAME}<br/>"
                f"A/C No.: {config.ACCOUNT_NO}<br/>"
                f"A/C Name: {config.ACCOUNT_NAME}<br/>"
                f"IFSC Code: {config.IFSC_CODE}<br/>"
                f"Branch: {config.BRANCH}", styles['Normal']
            )

        ]
    ]
    details_table = Table(details_data, colWidths=[3.4*inch, 3.4*inch])
    details_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    content.append(details_table)
    content.append(Spacer(1, 12))

    # Items Table
    items_data = [['Sl No', 'HSN Code', 'Product Name / Description', 'Qty', 'Unit Price', 'Total']]
    for item in invoice.line_items:
        items_data.append([
            str(item.sr_no),
            item.hsn_code,
            Paragraph(item.description.replace('\n', '<br/>'), styles['Normal']),
            str(item.quantity),
            f"Rs. {item.unit_price:,.2f}",
            f"Rs. {item.total_amount:,.2f}"
        ])
    items_table = Table(items_data, colWidths=[0.5*inch, 1*inch, 2.8*inch, 0.6*inch, 1*inch, 1.1*inch])
    items_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (3, 1), (3, -1), 'CENTER'),
        ('ALIGN', (4, 1), (-1, -1), 'RIGHT'),
    ]))
    content.append(items_table)
    content.append(Spacer(1, 10))

    # Summary Section
    summary_data = [
        ['Sub Total', f"Rs. {invoice.subtotal:,.2f}"],
        ['SGST 9%', f"Rs. {invoice.sgst:,.2f}"],
        ['CGST 9%', f"Rs. {invoice.cgst:,.2f}"],
        ['Round off / Freight', f"Rs. 0.00"],
        ['Grand Total', f"Rs. {invoice.total_amount:,.2f}"]
    ]
    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
    ]))
    content.append(summary_table)
    content.append(Spacer(1, 10))

    # Vehicle + Amount in Words
    in_words = invoice.total_amount_in_words  # Assume you convert number to words before passing
    content.append(Paragraph(f"<b>Vehicle No:</b> ___________________   <b>Rupees {in_words} only</b>", styles['Normal']))
    content.append(Spacer(1, 20))

    # Bank Details + Signatory
    sign_data = [
        [Paragraph(
            f"<b>OUR BANK DETAILS</b><br/>"
            f"Bank Name: {config.BANK_NAME}<br/>"
            f"A/C No.: {config.ACCOUNT_NO}<br/>"
            f"A/C Name: {config.ACCOUNT_NAME}<br/>"
            f"IFSC Code: {config.IFSC_CODE}<br/>"
            f"Branch: {config.BRANCH}", 
            styles['Normal']
        ),
        Paragraph("Authorised Signatory", ParagraphStyle(name='RightSign', alignment=TA_RIGHT, fontSize=10))]
    ]
    sign_table = Table(sign_data, colWidths=[4.5*inch, 2.3*inch])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    content.append(sign_table)

    # Footer Contact
    content.append(Spacer(1, 12))
    footer = Paragraph(f"Ph. {config.PHONE} | Email: {config.EMAIL}", ParagraphStyle(name='Footer', fontSize=8, alignment=TA_CENTER))
    content.append(footer)

    doc.build(content)
    buffer.seek(0)
    return buffer


def generate_detailed_monthly_report():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()
    content = []

    # Title
    title_style = ParagraphStyle('title', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold')
    content.append(Paragraph("Monthly & Yearly Client-wise Revenue Report", title_style))
    content.append(Spacer(1, 16))

    data = get_client_invoice_details()

    for year in sorted(data.keys()):
        year_style = ParagraphStyle('year', fontSize=14, fontName='Helvetica-Bold')
        content.append(Paragraph(f"Year: {year}", year_style))
        content.append(Spacer(1, 12))

        for month in sorted(data[year].keys()):
            month_style = ParagraphStyle('month', fontSize=12, fontName='Helvetica-Bold')
            content.append(Paragraph(f"Month: {month}", month_style))
            content.append(Spacer(1, 10))

            for client_name, invoices in data[year][month].items():
                client_style = ParagraphStyle('client', fontSize=11, fontName='Helvetica-Bold')
                content.append(Paragraph(f"Client: {client_name}", client_style))
                content.append(Spacer(1, 6))

                # Table header
                table_data = [['Description', 'Amount Paid (₹)']]
                for invoice in invoices:
                    table_data.append([
                        Paragraph(invoice['description'].replace('\n', '<br/>'), styles['Normal']),
                        f"{invoice['amount']:,.2f}"
                    ])

                table = Table(table_data, colWidths=[4.5 * inch, 1.5 * inch])
                table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ]))
                content.append(table)
                content.append(Spacer(1, 10))

            content.append(Spacer(1, 12))  # Extra space after each month

        content.append(Spacer(1, 14))  # Extra space after each year

    # Footer (optional)
    footer = Paragraph("<i>Generated by InvoiceGenius</i>", ParagraphStyle('footer', fontSize=8, alignment=TA_CENTER))
    content.append(Spacer(1, 20))
    content.append(footer)

    doc.build(content)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='detailed_client_report.pdf', mimetype='application/pdf')

def export_excel():
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Invoices")

    # Header row
    headers = ["Invoice No", "Client Name", "Invoice Date", "Subtotal", "CGST", "SGST", "Total", "Payment Status"]
    worksheet.write_row("A1", headers)

    # Fetch invoices from DB
    invoices = Invoice.query.order_by(Invoice.invoice_date.desc()).all()

    # Populate data rows
    row = 1
    for inv in invoices:
        worksheet.write(row, 0, inv.invoice_number)
        worksheet.write(row, 1, inv.client.name if inv.client else "N/A")
        worksheet.write(row, 2, inv.invoice_date.strftime('%Y-%m-%d') if inv.invoice_date else "")
        worksheet.write(row, 3, inv.subtotal or 0)
        worksheet.write(row, 4, inv.cgst or 0)
        worksheet.write(row, 5, inv.sgst or 0)
        worksheet.write(row, 6, inv.total_amount or 0)
        worksheet.write(row, 7, inv.payment_status or "Unknown")
        row += 1

    workbook.close()
    output.seek(0)

    filename = f"invoices_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, as_attachment=True, download_name=filename, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
