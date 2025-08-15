import io
import os
from datetime import datetime
from flask import send_file
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
import logging

from utils import number_to_words
from models import Company
import config

def generate_invoice_pdf(invoice):
    """Generate a professional invoice PDF with modern styling"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch
        )

        styles = getSampleStyleSheet()
        content = []

        # Custom styles
        title_style = ParagraphStyle(
            name='InvoiceTitle',
            fontSize=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=20
        )
        
        header_style = ParagraphStyle(
            name='Header',
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#1f2937')
        )
        
        normal_style = ParagraphStyle(
            name='Normal',
            fontSize=10,
            fontName='Helvetica',
            textColor=colors.HexColor('#374151')
        )

        # Invoice title
        if invoice.invoice_type == 'Proforma':
            title_text = "PROFORMA INVOICE"
        else:
            title_text = "TAX INVOICE"
        
        content.append(Paragraph(title_text, title_style))
        content.append(Spacer(1, 20))

        # Company and invoice details header
        company = Company.query.first()
        if not company:
            company = type('Company', (), {
                'name': config.COMPANY_NAME,
                'address': config.COMPANY_ADDRESS,
                'city': config.COMPANY_CITY,
                'state': config.COMPANY_STATE,
                'pincode': config.COMPANY_PINCODE,
                'phone': config.COMPANY_PHONE,
                'email': config.COMPANY_EMAIL,
                'gstin': config.GSTIN,
                'pan': config.PAN
            })()

        header_data = [
            [
                Paragraph(f"<b>Invoice No:</b> {invoice.invoice_number}<br/>"
                         f"<b>Date:</b> {invoice.invoice_date.strftime('%d-%m-%Y')}<br/>"
                         f"<b>Due Date:</b> {invoice.due_date.strftime('%d-%m-%Y') if invoice.due_date else 'N/A'}", 
                         normal_style),
                Paragraph(f"<b>{company.name}</b><br/>"
                         f"{company.address}<br/>"
                         f"{company.city}, {company.state} - {company.pincode}<br/>"
                         f"Phone: {company.phone}<br/>"
                         f"Email: {company.email}", 
                         normal_style)
            ]
        ]
        
        header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
        header_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(header_table)
        content.append(Spacer(1, 20))

        # Bill to and company GST details
        client = invoice.client
        bill_to_data = [
            [
                Paragraph("<b>Bill To</b>", header_style),
                Paragraph("<b>Company Details</b>", header_style)
            ],
            [
                Paragraph(f"<b>{client.name}</b><br/>"
                         f"{client.contact_person}<br/>" if client.contact_person else "" +
                         f"{client.address}<br/>"
                         f"{client.city}, {client.state} - {client.pincode}<br/>"
                         f"Phone: {client.phone}<br/>"
                         f"Email: {client.email}<br/>"
                         f"<b>GSTIN:</b> {client.gstin or 'N/A'}", 
                         normal_style),
                Paragraph(f"<b>GSTIN:</b> {company.gstin}<br/>"
                         f"<b>PAN:</b> {company.pan}<br/>"
                         f"<b>State:</b> {company.state}<br/>"
                         f"<b>State Code:</b> {company.gstin[:2] if company.gstin else 'N/A'}", 
                         normal_style)
            ]
        ]
        
        bill_to_table = Table(bill_to_data, colWidths=[3.5 * inch, 3.5 * inch])
        bill_to_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(bill_to_table)
        content.append(Spacer(1, 20))

        # Line items table
        items_data = [['S.No', 'HSN/SAC', 'Description', 'Qty', 'Unit', 'Rate', 'Tax%', 'Amount']]
        
        for item in invoice.line_items:
            items_data.append([
                str(item.sr_no),
                item.hsn_code or '',
                Paragraph(item.description.replace('\n', '<br/>'), normal_style),
                f"{item.quantity:g}",
                item.unit,
                f"₹{item.unit_price:,.2f}",
                f"{item.tax_percentage:g}%",
                f"₹{item.total_amount:,.2f}"
            ])

        # Add empty rows to maintain table structure
        while len(items_data) < 12:  # Minimum 10 rows for professional look
            items_data.append(['', '', '', '', '', '', '', ''])

        items_table = Table(items_data, colWidths=[
            0.5*inch, 0.8*inch, 2.8*inch, 0.6*inch, 0.6*inch, 0.8*inch, 0.5*inch, 1*inch
        ])
        
        items_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        content.append(items_table)
        content.append(Spacer(1, 15))

        # Tax summary and totals
        tax_data = [
            ['', '', 'Subtotal:', f"₹{invoice.subtotal:,.2f}"],
            ['', '', 'CGST:', f"₹{invoice.cgst:,.2f}"],
            ['', '', 'SGST:', f"₹{invoice.sgst:,.2f}"],
            ['', '', 'IGST:', f"₹{invoice.igst:,.2f}"],
            ['', '', 'Round Off:', '₹0.00'],
            ['', '', Paragraph('<b>Total Amount:</b>', header_style), 
             Paragraph(f'<b>₹{invoice.total_amount:,.2f}</b>', header_style)]
        ]
        
        tax_table = Table(tax_data, colWidths=[2*inch, 2*inch, 1.5*inch, 1.5*inch])
        tax_table.setStyle(TableStyle([
            ('GRID', (2, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#f3f4f6')),
            ('LEFTPADDING', (2, 0), (-1, -1), 8),
            ('RIGHTPADDING', (2, 0), (-1, -1), 8),
            ('TOPPADDING', (2, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (2, 0), (-1, -1), 4),
        ]))
        content.append(tax_table)
        content.append(Spacer(1, 15))

        # Amount in words
        amount_words = number_to_words(int(invoice.total_amount))
        words_text = f"Amount in Words: {amount_words.title()} Rupees Only"
        
        words_table = Table([[Paragraph(f'<b>{words_text}</b>', normal_style)]], 
                           colWidths=[7*inch])
        words_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f9fafb')),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(words_table)
        content.append(Spacer(1, 20))

        # Terms and bank details
        terms_data = [
            [
                Paragraph("<b>Terms & Conditions:</b><br/>" + 
                         (invoice.terms_conditions or 
                          "1. Payment due within 30 days of invoice date.<br/>"
                          "2. Interest @ 2% per month will be charged on overdue amounts.<br/>"
                          "3. Subject to local jurisdiction only."), 
                         normal_style),
                Paragraph(f"<b>Bank Details:</b><br/>"
                         f"Bank: {config.BANK_NAME}<br/>"
                         f"A/c No: {config.ACCOUNT_NO}<br/>"
                         f"A/c Name: {config.ACCOUNT_NAME}<br/>"
                         f"IFSC: {config.IFSC_CODE}<br/>"
                         f"Branch: {config.BRANCH}", 
                         normal_style)
            ]
        ]
        
        terms_table = Table(terms_data, colWidths=[3.5*inch, 3.5*inch])
        terms_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        content.append(terms_table)
        content.append(Spacer(1, 30))

        # Signature section
        signature_data = [
            ['', f"For {company.name}"],
            ['', ''],
            ['', ''],
            ['Customer Signature', 'Authorized Signatory']
        ]
        
        signature_table = Table(signature_data, colWidths=[3.5*inch, 3.5*inch])
        signature_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor('#6b7280')),
        ]))
        content.append(signature_table)

        # Add footer
        footer_text = f"This is a computer generated invoice | Generated on {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        if invoice.blockchain_hash:
            footer_text += f" | Blockchain Verified: {invoice.blockchain_hash[:16]}..."
        
        footer_para = Paragraph(footer_text, 
                               ParagraphStyle('Footer', fontSize=8, alignment=TA_CENTER, 
                                            textColor=colors.HexColor('#6b7280')))
        content.append(Spacer(1, 20))
        content.append(footer_para)

        # Build PDF
        doc.build(content)
        buffer.seek(0)
        
        return buffer

    except Exception as e:
        logging.error(f"PDF generation failed: {e}")
        raise

def generate_challan_pdf(challan):
    """Generate delivery challan PDF"""
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=0.5 * inch,
            bottomMargin=0.5 * inch,
            leftMargin=0.5 * inch,
            rightMargin=0.5 * inch
        )

        styles = getSampleStyleSheet()
        content = []

        # Title
        title_style = ParagraphStyle(
            name='ChallanTitle',
            fontSize=18,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#dc2626'),
            spaceAfter=20
        )
        
        content.append(Paragraph("DELIVERY CHALLAN", title_style))
        content.append(Spacer(1, 20))

        # Rest of the challan generation logic similar to invoice
        # ... (implement based on challan requirements)

        doc.build(content)
        buffer.seek(0)
        
        return buffer

    except Exception as e:
        logging.error(f"Challan PDF generation failed: {e}")
        raise

def export_excel(invoices, filename="invoices_export.xlsx"):
    """Export invoices to Excel format"""
    try:
        import xlsxwriter
        
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        worksheet = workbook.add_worksheet('Invoices')
        
        # Headers
        headers = ['Invoice No', 'Date', 'Client', 'Amount', 'Status', 'Due Date']
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        
        # Data
        for row, invoice in enumerate(invoices, 1):
            worksheet.write(row, 0, invoice.invoice_number)
            worksheet.write(row, 1, invoice.invoice_date.strftime('%Y-%m-%d'))
            worksheet.write(row, 2, invoice.client.name)
            worksheet.write(row, 3, invoice.total_amount)
            worksheet.write(row, 4, invoice.payment_status)
            worksheet.write(row, 5, invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '')
        
        workbook.close()
        buffer.seek(0)
        
        return buffer

    except Exception as e:
        logging.error(f"Excel export failed: {e}")
        raise

