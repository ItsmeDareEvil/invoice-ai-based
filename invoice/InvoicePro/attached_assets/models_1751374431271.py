from datetime import datetime
from sqlalchemy import func
from app import db

class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    gstin = db.Column(db.String(15))
    pan = db.Column(db.String(10))
    logo_path = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100))
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    gstin = db.Column(db.String(15))
    pan = db.Column(db.String(10))
    client_type = db.Column(db.String(50), default='Regular')  # Regular, VIP, New
    tags = db.Column(db.Text)  # JSON string for color-coded tags
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # CRM fields
    lead_stage = db.Column(db.String(50), default='New')  # New, In Discussion, Quoted, Closed
    last_contact_date = db.Column(db.DateTime)
    follow_up_date = db.Column(db.DateTime)
    total_business = db.Column(db.Float, default=0.0)
    
    invoices = db.relationship('Invoice', backref='client', lazy=True)
    challans = db.relationship('DeliveryChallan', backref='client', lazy=True)

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    due_date = db.Column(db.Date)
    
    # Financial fields
    subtotal = db.Column(db.Float, default=0.0)
    cgst = db.Column(db.Float, default=0.0)
    sgst = db.Column(db.Float, default=0.0)
    igst = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Payment tracking
    payment_status = db.Column(db.String(20), default='Unpaid')  # Paid, Unpaid, Partially Paid
    payment_date = db.Column(db.Date)
    payment_mode = db.Column(db.String(50))  # Cash, UPI, Bank Transfer, Card, Other
    amount_paid = db.Column(db.Float, default=0.0)
    
    # Additional fields
    notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    invoice_type = db.Column(db.String(20), default='Invoice')  # Invoice, Proforma, Tax Invoice
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    line_items = db.relationship('InvoiceLineItem', backref='invoice', lazy=True, cascade='all, delete-orphan')

class InvoiceLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    sr_no = db.Column(db.Integer, nullable=False)
    hsn_code = db.Column(db.String(20))
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default='Nos')
    unit_price = db.Column(db.Float, nullable=False)
    tax_percentage = db.Column(db.Float, default=18.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    
    # Cost tracking for profit analysis
    cost_price = db.Column(db.Float, default=0.0)

class DeliveryChallan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challan_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    challan_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    delivery_date = db.Column(db.Date)
    
    # Status tracking
    status = db.Column(db.String(20), default='Open')  # Open, Delivered, Billed
    notes = db.Column(db.Text)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))  # When converted to invoice
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    line_items = db.relationship('ChallanLineItem', backref='challan', lazy=True, cascade='all, delete-orphan')

class ChallanLineItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challan_id = db.Column(db.Integer, db.ForeignKey('delivery_challan.id'), nullable=False)
    sr_no = db.Column(db.Integer, nullable=False)
    hsn_code = db.Column(db.String(20))
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default='Nos')
    
    # Optional pricing for challans that include rates
    unit_price = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)

class PaymentReminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    reminder_type = db.Column(db.String(50))  # Follow-up, Payment Due, Overdue
    status = db.Column(db.String(20), default='Pending')  # Pending, Sent, Completed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    reminder_type = db.Column(db.String(50))  # Follow-up, Payment, Quotation, Meeting, Auditor Work
    status = db.Column(db.String(20), default='Pending')  # Pending, Completed
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    client = db.relationship('Client', backref='reminders')

class BusinessSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
