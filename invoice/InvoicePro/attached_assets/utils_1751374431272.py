from collections import defaultdict
from datetime import datetime
import random

from sqlalchemy import func, extract
from dateutil.relativedelta import relativedelta

from app import db
from models import Invoice, Client, InvoiceLineItem

def number_to_words(n):
    """
    Convert an integer number n into words (English).
    Supports numbers up to 999,999,999.
    """
    if n == 0:
        return "zero"

    def one(num):
        switcher = {
            1: "one",
            2: "two",
            3: "three",
            4: "four",
            5: "five",
            6: "six",
            7: "seven",
            8: "eight",
            9: "nine"
        }
        return switcher.get(num, "")

    def two_less_20(num):
        switcher = {
            10: "ten",
            11: "eleven",
            12: "twelve",
            13: "thirteen",
            14: "fourteen",
            15: "fifteen",
            16: "sixteen",
            17: "seventeen",
            18: "eighteen",
            19: "nineteen"
        }
        return switcher.get(num, "")

    def ten(num):
        switcher = {
            2: "twenty",
            3: "thirty",
            4: "forty",
            5: "fifty",
            6: "sixty",
            7: "seventy",
            8: "eighty",
            9: "ninety"
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

    billion = n // 1000000000
    million = (n - billion * 1000000000) // 1000000
    thousand = (n - billion * 1000000000 - million * 1000000) // 1000
    rest = n % 1000

    result = ""
    if billion > 0:
        result += three(billion) + " billion"
    if million > 0:
        result += " " if result != "" else ""
        result += three(million) + " million"
    if thousand > 0:
        result += " " if result != "" else ""
        result += three(thousand) + " thousand"
    if rest > 0:
        result += " " if result != "" else ""
        result += three(rest)
    return result.strip()

def get_monthly_revenue_data():
    today = datetime.today()
    start_date = today.replace(day=1) - relativedelta(months=11)

    results = db.session.query(
        func.strftime('%Y-%m', Invoice.invoice_date).label('month'),
        func.sum(Invoice.total_amount).label('revenue')
    ).filter(
        Invoice.invoice_date >= start_date,
        Invoice.payment_status == 'Paid'
    ).group_by('month').order_by('month').all()

    revenue_dict = {r.month: r.revenue for r in results}
    
    monthly_data = []
    for i in range(12):
        month_date = today.replace(day=1) - relativedelta(months=i)
        month_str = month_date.strftime('%Y-%m')
        display_str = month_date.strftime('%b %Y')
        revenue = revenue_dict.get(month_str, 0) or 0
        monthly_data.append({'month': display_str, 'revenue': float(revenue)})

    monthly_data.reverse()
    return monthly_data

def get_tax_summary():
    """
    Returns a dictionary with aggregated tax amounts: cgst, sgst, total.
    Only considers paid invoices.
    """

    cgst_sum = db.session.query(func.sum(Invoice.cgst)).filter(Invoice.payment_status == 'Paid').scalar() or 0
    sgst_sum = db.session.query(func.sum(Invoice.sgst)).filter(Invoice.payment_status == 'Paid').scalar() or 0
    total_tax = cgst_sum + sgst_sum

    return {
        'cgst': float(cgst_sum),
        'sgst': float(sgst_sum),
        'total': float(total_tax)
    }

def get_client_analytics():
    # Step 1: Monthly Profit & Margin using invoice_line_item
    monthly_data = db.session.query(
        func.strftime('%Y-%m', Invoice.invoice_date).label('month'),  # '2025-06'
        func.sum(InvoiceLineItem.unit_price * InvoiceLineItem.quantity).label('revenue'),
        func.sum(InvoiceLineItem.cost_price * InvoiceLineItem.quantity).label('cost')
    ).join(Invoice).filter(
        Invoice.payment_status == 'Paid'
    ).group_by('month').order_by('month').all()

    monthly_profit_data = []
    for row in monthly_data:
        month_str = datetime.strptime(row.month, '%Y-%m').strftime('%b %Y')  # 'Jun 2025'
        revenue = row.revenue or 0
        cost = row.cost or 0
        profit = revenue - cost
        margin_percentage = round((profit / revenue) * 100, 2) if revenue > 0 else 0.0

        monthly_profit_data.append({
            'month': month_str,
            'revenue': revenue,
            'cost': cost,
            'profit': profit,
            'margin_percentage': margin_percentage
        })

    # Step 2: Top 5 Clients by Revenue
    top_clients_raw = db.session.query(
        Client.name,
        func.sum(Invoice.total_amount).label('revenue'),
        func.count(Invoice.id).label('invoice_count')
    ).join(Invoice).filter(
        Invoice.payment_status == 'Paid'
    ).group_by(Client.id).order_by(
        func.sum(Invoice.total_amount).desc()
    ).limit(5).all()

    top_clients = [{
        'name': row.name,
        'revenue': float(row.revenue),
        'invoice_count': row.invoice_count
    } for row in top_clients_raw]

    # Step 3: Client Type Counts
    total_clients = db.session.query(func.count(Client.id)).scalar() or 0
    regular_clients = db.session.query(func.count(Client.id)).filter(Client.client_type == 'Regular').scalar() or 0
    premium_clients = db.session.query(func.count(Client.id)).filter(Client.client_type == 'Premium').scalar() or 0

    # Final output
    return {
        'monthly_profit_data': monthly_profit_data,
        'top_clients': top_clients,
        'total_clients': total_clients,
        'regular_clients': regular_clients,
        'premium_clients': premium_clients
    }


def generate_invoice_number():
    """
    Generate a unique invoice number in the format: YYYYMMDD-XXXX
    where XXXX is a random 4-digit number.
    """

    date_str = datetime.now().strftime('%Y%m%d')
    random_number = random.randint(1000, 9999)
    return f"{date_str}-{random_number}"


def generate_challan_number():
    """
    Generate a unique challan number in the format: CH-YYYYMMDD-XXXX
    where XXXX is a random 4-digit number.
    """
    
    date_str = datetime.now().strftime('%Y%m%d')
    random_number = random.randint(1000, 9999)
    return f"CH-{date_str}-{random_number}"

def get_client_invoice_details():
    """
    Organizes invoice data into a nested dictionary:
    {year: {month: {client_name: [ {description, amount}, ... ] } } }
    """
    result = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    paid_invoices = db.session.query(Invoice).filter(Invoice.payment_status == 'Paid').all()

    for invoice in paid_invoices:
        year = invoice.invoice_date.year
        month = invoice.invoice_date.strftime('%B')  # e.g. 'June'
        client_name = invoice.client.name

        for item in invoice.line_items:
            result[year][month][client_name].append({
                'description': item.description,
                'amount': item.total_amount
            })

    return result

from werkzeug.security import generate_password_hash as werkzeug_generate_password_hash, check_password_hash as werkzeug_check_password_hash

def generate_password_hash(password):
    return werkzeug_generate_password_hash(password)

def check_password_hash(pwhash, password):
    return werkzeug_check_password_hash(pwhash, password)
