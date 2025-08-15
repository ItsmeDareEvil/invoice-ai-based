import random
import hashlib
import qrcode
import io
import base64
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, extract
from dateutil.relativedelta import relativedelta
from werkzeug.security import generate_password_hash as werkzeug_generate_password_hash
from werkzeug.security import check_password_hash as werkzeug_check_password_hash

from app import db
from models import Invoice, Client, InvoiceLineItem, Company

def generate_password_hash(password):
    """Generate password hash"""
    return werkzeug_generate_password_hash(password)

def check_password_hash(pwhash, password):
    """Check password hash"""
    return werkzeug_check_password_hash(pwhash, password)

def number_to_words(n):
    """Convert an integer number n into words (English, Indian style)"""
    if n == 0:
        return "zero"

    def one(num):
        switcher = {
            1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
            6: "six", 7: "seven", 8: "eight", 9: "nine"
        }
        return switcher.get(num, "")

    def two_less_20(num):
        switcher = {
            10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
            15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen"
        }
        return switcher.get(num, "")

    def ten(num):
        switcher = {
            2: "twenty", 3: "thirty", 4: "forty", 5: "fifty",
            6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"
        }
        return switcher.get(num, "")

    def two(num):
        if num == 0:
            return ""
        elif num < 10:
            return one(num)
        elif num < 20:
            return two_less_20(num)
        else:
            tens = num // 10
            rest = num % 10
            return ten(tens) + (" " + one(rest) if rest != 0 else "")

    def three(num):
        hundred = num // 100
        rest = num % 100
        if hundred == 0:
            return two(rest)
        else:
            return one(hundred) + " hundred" + (" " + two(rest) if rest != 0 else "")

    # Indian numbering system: crores, lakhs, thousands
    crore = n // 10000000
    lakh = (n % 10000000) // 100000
    thousand = (n % 100000) // 1000
    rest = n % 1000

    result = ""
    if crore > 0:
        result += three(crore) + " crore"
    if lakh > 0:
        result += " " if result != "" else ""
        result += three(lakh) + " lakh"
    if thousand > 0:
        result += " " if result != "" else ""
        result += three(thousand) + " thousand"
    if rest > 0:
        result += " " if result != "" else ""
        result += three(rest)
    
    return result.strip()

def generate_invoice_number():
    """Generate unique invoice number with AI-enhanced format"""
    current_date = datetime.now()
    date_str = current_date.strftime('%Y%m%d')
    
    # Get count of invoices created today
    today_count = Invoice.query.filter(
        Invoice.invoice_date == current_date.date()
    ).count() + 1
    
    # Generate sequential number with random component for uniqueness
    random_component = random.randint(100, 999)
    invoice_number = f"AI-INV-{date_str}-{today_count:03d}-{random_component}"
    
    # Ensure uniqueness
    while Invoice.query.filter_by(invoice_number=invoice_number).first():
        random_component = random.randint(100, 999)
        invoice_number = f"AI-INV-{date_str}-{today_count:03d}-{random_component}"
    
    return invoice_number

def generate_challan_number():
    """Generate unique delivery challan number"""
    current_date = datetime.now()
    date_str = current_date.strftime('%Y%m%d')
    random_number = random.randint(1000, 9999)
    
    challan_number = f"CH-{date_str}-{random_number}"
    
    # Import here to avoid circular import
    from models import DeliveryChallan
    
    # Ensure uniqueness
    while DeliveryChallan.query.filter_by(challan_number=challan_number).first():
        random_number = random.randint(1000, 9999)
        challan_number = f"CH-{date_str}-{random_number}"
    
    return challan_number

def generate_payment_qr_code(invoice):
    """Generate QR code for payment with UPI integration"""
    try:
        company = Company.query.first()
        
        # UPI payment string format
        upi_string = f"upi://pay?pa={company.email}&pn={company.name}&am={invoice.total_amount}&cu=INR&tn=Invoice {invoice.invoice_number}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_string)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 for storage
        img_buffer = io.BytesIO()
        qr_img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code_base64}"
        
    except Exception as e:
        print(f"QR code generation failed: {e}")
        return ""

def predict_payment_date(invoice, ai_risk_assessment):
    """Predict payment date based on AI risk assessment and client history"""
    try:
        client = Client.query.get(invoice.client_id)
        
        # Base prediction on due date
        base_date = invoice.due_date or invoice.invoice_date + timedelta(days=30)
        
        # Adjust based on client's historical payment behavior
        if client.payment_behavior_pattern == "Early":
            predicted_date = base_date - timedelta(days=5)
        elif client.payment_behavior_pattern == "Late":
            predicted_date = base_date + timedelta(days=15)
        else:  # Consistent
            predicted_date = base_date
        
        # Adjust based on AI risk score
        risk_score = ai_risk_assessment.get('risk_assessment', {}).get('score', 0.5)
        if risk_score > 0.7:  # High risk
            predicted_date = predicted_date + timedelta(days=10)
        elif risk_score < 0.3:  # Low risk
            predicted_date = predicted_date - timedelta(days=3)
        
        return predicted_date
        
    except Exception as e:
        print(f"Payment date prediction failed: {e}")
        return invoice.due_date

def get_monthly_revenue_data(months=12):
    """Get monthly revenue data for analytics"""
    today = datetime.today()
    start_date = today.replace(day=1) - relativedelta(months=months-1)

    results = db.session.query(
        func.strftime('%Y-%m', Invoice.invoice_date).label('month'),
        func.sum(Invoice.total_amount).label('revenue'),
        func.count(Invoice.id).label('invoice_count')
    ).filter(
        Invoice.invoice_date >= start_date,
        Invoice.payment_status == 'Paid'
    ).group_by('month').order_by('month').all()

    revenue_dict = {r.month: {'revenue': r.revenue, 'count': r.invoice_count} for r in results}
    
    monthly_data = []
    for i in range(months):
        month_date = today.replace(day=1) - relativedelta(months=i)
        month_str = month_date.strftime('%Y-%m')
        display_str = month_date.strftime('%b %Y')
        data = revenue_dict.get(month_str, {'revenue': 0, 'count': 0})
        
        monthly_data.append({
            'month': display_str,
            'revenue': float(data['revenue'] or 0),
            'invoice_count': data['count']
        })

    monthly_data.reverse()
    return monthly_data

def get_client_performance_metrics():
    """Get client performance analytics"""
    # Top clients by revenue
    top_clients = db.session.query(
        Client.name,
        Client.id,
        func.sum(Invoice.total_amount).label('total_revenue'),
        func.count(Invoice.id).label('invoice_count'),
        func.avg(Invoice.total_amount).label('avg_invoice_value')
    ).join(Invoice).filter(
        Invoice.payment_status == 'Paid'
    ).group_by(Client.id).order_by(
        func.sum(Invoice.total_amount).desc()
    ).limit(10).all()
    
    # Client type distribution
    client_types = db.session.query(
        Client.client_type,
        func.count(Client.id).label('count')
    ).group_by(Client.client_type).all()
    
    # Payment behavior analysis
    payment_behavior = db.session.query(
        Client.payment_behavior_pattern,
        func.count(Client.id).label('count')
    ).filter(Client.payment_behavior_pattern.isnot(None)).group_by(
        Client.payment_behavior_pattern
    ).all()
    
    return {
        'top_clients': [
            {
                'name': client.name,
                'id': client.id,
                'total_revenue': float(client.total_revenue),
                'invoice_count': client.invoice_count,
                'avg_invoice_value': float(client.avg_invoice_value)
            }
            for client in top_clients
        ],
        'client_types': [
            {'type': ct.client_type, 'count': ct.count}
            for ct in client_types
        ],
        'payment_behavior': [
            {'pattern': pb.payment_behavior_pattern, 'count': pb.count}
            for pb in payment_behavior
        ]
    }

def get_payment_analytics():
    """Get payment analytics and trends"""
    # Payment status distribution
    payment_status = db.session.query(
        Invoice.payment_status,
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total_amount).label('total_amount')
    ).group_by(Invoice.payment_status).all()
    
    # Payment mode analysis (for paid invoices)
    payment_modes = db.session.query(
        Invoice.payment_mode,
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total_amount).label('total_amount')
    ).filter(
        Invoice.payment_status == 'Paid',
        Invoice.payment_mode.isnot(None)
    ).group_by(Invoice.payment_mode).all()
    
    # Average payment delay
    avg_delay = db.session.query(
        func.avg(func.julianday(Invoice.payment_date) - func.julianday(Invoice.due_date)).label('avg_delay')
    ).filter(
        Invoice.payment_status == 'Paid',
        Invoice.payment_date.isnot(None),
        Invoice.due_date.isnot(None)
    ).scalar()
    
    return {
        'payment_status': [
            {
                'status': ps.payment_status,
                'count': ps.count,
                'amount': float(ps.total_amount or 0)
            }
            for ps in payment_status
        ],
        'payment_modes': [
            {
                'mode': pm.payment_mode,
                'count': pm.count,
                'amount': float(pm.total_amount)
            }
            for pm in payment_modes
        ],
        'avg_payment_delay_days': float(avg_delay or 0)
    }

def get_tax_summary():
    """Get tax summary for financial reporting"""
    tax_summary = db.session.query(
        func.sum(Invoice.cgst).label('total_cgst'),
        func.sum(Invoice.sgst).label('total_sgst'),
        func.sum(Invoice.igst).label('total_igst'),
        func.sum(Invoice.total_amount).label('total_revenue')
    ).filter(Invoice.payment_status == 'Paid').first()
    
    return {
        'cgst': float(tax_summary.total_cgst or 0),
        'sgst': float(tax_summary.total_sgst or 0),
        'igst': float(tax_summary.total_igst or 0),
        'total_tax': float((tax_summary.total_cgst or 0) + (tax_summary.total_sgst or 0) + (tax_summary.total_igst or 0)),
        'total_revenue': float(tax_summary.total_revenue or 0)
    }

def calculate_profitability(invoice_id=None):
    """Calculate profitability metrics"""
    query = db.session.query(
        func.sum(InvoiceLineItem.unit_price * InvoiceLineItem.quantity).label('revenue'),
        func.sum(InvoiceLineItem.cost_price * InvoiceLineItem.quantity).label('cost')
    ).join(Invoice)
    
    if invoice_id:
        query = query.filter(Invoice.id == invoice_id)
    else:
        query = query.filter(Invoice.payment_status == 'Paid')
    
    result = query.first()
    
    revenue = float(result.revenue or 0)
    cost = float(result.cost or 0)
    profit = revenue - cost
    margin_percentage = (profit / revenue * 100) if revenue > 0 else 0
    
    return {
        'revenue': revenue,
        'cost': cost,
        'profit': profit,
        'margin_percentage': round(margin_percentage, 2)
    }

def generate_digital_signature(data):
    """Generate digital signature for documents"""
    try:
        # Simple hash-based signature (in production, use proper PKI)
        signature_data = f"{data['invoice_number']}{data['total_amount']}{data['client_id']}{datetime.now().isoformat()}"
        signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
        
        return {
            'signature': signature_hash,
            'timestamp': datetime.now().isoformat(),
            'algorithm': 'SHA256'
        }
    except Exception as e:
        print(f"Digital signature generation failed: {e}")
        return None

def validate_gst_number(gst_number):
    """Validate GST number format"""
    if not gst_number:
        return False
    
    # Basic GST format validation (15 characters)
    if len(gst_number) != 15:
        return False
    
    # Check if first 2 characters are digits (state code)
    if not gst_number[:2].isdigit():
        return False
    
    # Check if next 10 characters are alphanumeric (PAN)
    if not gst_number[2:12].isalnum():
        return False
    
    # Check if 13th character is alphabetic (entity type)
    if not gst_number[12].isalpha():
        return False
    
    # Check if last character is alphanumeric (check digit)
    if not gst_number[14].isalnum():
        return False
    
    return True

def format_currency(amount, currency_symbol="₹"):
    """Format currency in Indian style"""
    try:
        # Convert to float if string
        if isinstance(amount, str):
            amount = float(amount)
        
        # Indian numbering system formatting
        amount_str = f"{amount:,.2f}"
        
        # Replace commas with Indian style (lakhs and crores)
        parts = amount_str.split('.')
        integer_part = parts[0]
        decimal_part = parts[1] if len(parts) > 1 else "00"
        
        # Indian style comma placement
        if len(integer_part) > 3:
            # Remove existing commas
            integer_part = integer_part.replace(',', '')
            
            # Add Indian style commas
            if len(integer_part) > 3:
                integer_part = integer_part[:-3] + ',' + integer_part[-3:]
            if len(integer_part) > 6:
                integer_part = integer_part[:-6] + ',' + integer_part[-6:]
        
        formatted_amount = f"{integer_part}.{decimal_part}"
        return f"{currency_symbol}{formatted_amount}"
        
    except Exception as e:
        print(f"Currency formatting failed: {e}")
        return f"{currency_symbol}{amount}"

def get_financial_year_dates(date=None):
    """Get financial year start and end dates (Indian FY: April to March)"""
    if date is None:
        date = datetime.now().date()
    
    if date.month >= 4:  # April to December
        fy_start = date.replace(month=4, day=1)
        fy_end = date.replace(year=date.year + 1, month=3, day=31)
    else:  # January to March
        fy_start = date.replace(year=date.year - 1, month=4, day=1)
        fy_end = date.replace(month=3, day=31)
    
    return fy_start, fy_end

def calculate_due_date(invoice_date, payment_terms_days=30):
    """Calculate due date based on invoice date and payment terms"""
    return invoice_date + timedelta(days=payment_terms_days)

def get_outstanding_invoices_summary():
    """Get summary of outstanding invoices"""
    outstanding = db.session.query(
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total_amount - Invoice.amount_paid).label('total_outstanding')
    ).filter(
        Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
    ).first()
    
    # Overdue invoices (past due date)
    overdue = db.session.query(
        func.count(Invoice.id).label('count'),
        func.sum(Invoice.total_amount - Invoice.amount_paid).label('total_overdue')
    ).filter(
        Invoice.payment_status.in_(['Unpaid', 'Partially Paid']),
        Invoice.due_date < datetime.now().date()
    ).first()
    
    return {
        'outstanding_count': outstanding.count or 0,
        'outstanding_amount': float(outstanding.total_outstanding or 0),
        'overdue_count': overdue.count or 0,
        'overdue_amount': float(overdue.total_overdue or 0)
    }

