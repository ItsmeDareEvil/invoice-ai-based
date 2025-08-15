from datetime import datetime
from sqlalchemy import func, JSON
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
    website = db.Column(db.String(200))
    gstin = db.Column(db.String(15))
    pan = db.Column(db.String(10))
    logo_path = db.Column(db.String(200))
    
    # AI-Enhanced Company Features
    ai_brand_voice = db.Column(db.Text)  # AI-generated brand voice description
    auto_invoice_templates = db.Column(JSON)  # AI-customized invoice templates
    blockchain_id = db.Column(db.String(100))  # Blockchain company verification ID
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    client_type = db.Column(db.String(50), default='Regular')
    tags = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # CRM fields
    lead_stage = db.Column(db.String(50), default='New')
    last_contact_date = db.Column(db.DateTime)
    follow_up_date = db.Column(db.DateTime)
    total_business = db.Column(db.Float, default=0.0)
    
    # AI-Enhanced Client Features
    ai_risk_score = db.Column(db.Float, default=0.0)  # AI-calculated payment risk
    predicted_ltv = db.Column(db.Float, default=0.0)  # AI-predicted lifetime value
    communication_preferences = db.Column(JSON)  # AI-learned communication patterns
    sentiment_score = db.Column(db.Float, default=0.0)  # AI sentiment analysis
    payment_behavior_pattern = db.Column(db.String(50))  # Early/Late/Consistent
    preferred_products = db.Column(JSON)  # AI-detected product preferences
    blockchain_verified = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    payment_status = db.Column(db.String(20), default='Unpaid')
    payment_date = db.Column(db.Date)
    payment_mode = db.Column(db.String(50))
    amount_paid = db.Column(db.Float, default=0.0)
    
    # Additional fields
    notes = db.Column(db.Text)
    terms_conditions = db.Column(db.Text)
    invoice_type = db.Column(db.String(20), default='Invoice')
    
    # Revolutionary AI Features
    ai_generated = db.Column(db.Boolean, default=False)  # Created via AI assistant
    voice_command_created = db.Column(db.Boolean, default=False)  # Created via voice
    ai_suggestions_applied = db.Column(JSON)  # Track applied AI suggestions
    blockchain_hash = db.Column(db.String(100))  # Blockchain verification hash
    blockchain_timestamp = db.Column(db.DateTime)  # Blockchain timestamp
    qr_payment_code = db.Column(db.String(200))  # QR code for payments
    digital_signature = db.Column(db.Text)  # Digital signature data
    language_code = db.Column(db.String(10), default='en')  # Invoice language
    ar_preview_data = db.Column(JSON)  # AR preview configuration
    collaboration_data = db.Column(JSON)  # Real-time collaboration metadata
    ai_risk_assessment = db.Column(JSON)  # AI-generated risk assessment
    predicted_payment_date = db.Column(db.Date)  # AI-predicted payment date
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    line_items = db.relationship('InvoiceLineItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    ai_interactions = db.relationship('AIInteraction', backref='invoice', lazy=True)

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
    cost_price = db.Column(db.Float, default=0.0)
    
    # AI-Enhanced Line Item Features
    ai_suggested = db.Column(db.Boolean, default=False)  # AI suggested this item
    ai_confidence_score = db.Column(db.Float, default=0.0)  # AI confidence in suggestion
    similar_items_data = db.Column(JSON)  # AI-found similar items for reference
    price_optimization_applied = db.Column(db.Boolean, default=False)  # AI price optimization

class DeliveryChallan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    challan_number = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    challan_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    delivery_date = db.Column(db.Date)
    
    # Status tracking
    status = db.Column(db.String(20), default='Open')
    notes = db.Column(db.Text)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    
    # AI-Enhanced Delivery Features
    gps_tracking_enabled = db.Column(db.Boolean, default=False)
    delivery_coordinates = db.Column(db.String(100))  # GPS coordinates
    delivery_confirmation_method = db.Column(db.String(50))  # Signature/Photo/GPS
    ai_delivery_optimization = db.Column(JSON)  # AI route optimization data
    blockchain_delivery_proof = db.Column(db.String(100))  # Blockchain delivery proof
    
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
    unit_price = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Enhanced User Features
    is_admin = db.Column(db.Boolean, default=False)
    ai_features_enabled = db.Column(db.Boolean, default=True)
    voice_commands_enabled = db.Column(db.Boolean, default=True)
    preferred_language = db.Column(db.String(10), default='en')
    theme_preference = db.Column(db.String(20), default='auto')  # light/dark/auto
    biometric_enabled = db.Column(db.Boolean, default=False)
    collaboration_access = db.Column(db.Boolean, default=True)
    notification_preferences = db.Column(JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    ai_interactions = db.relationship('AIInteraction', backref='user', lazy=True)

class AIInteraction(db.Model):
    """Track AI interactions for learning and improvement"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    interaction_type = db.Column(db.String(50))  # voice_command, suggestion, analysis, etc.
    input_data = db.Column(JSON)  # User input or query
    ai_response = db.Column(JSON)  # AI response
    confidence_score = db.Column(db.Float)
    user_feedback = db.Column(db.String(20))  # positive, negative, neutral
    processing_time = db.Column(db.Float)  # Time taken for AI processing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlockchainRecord(db.Model):
    """Store blockchain verification records"""
    id = db.Column(db.Integer, primary_key=True)
    record_type = db.Column(db.String(50))  # invoice, payment, delivery, etc.
    record_id = db.Column(db.Integer)  # ID of the related record
    blockchain_hash = db.Column(db.String(100), unique=True)
    block_number = db.Column(db.Integer)
    transaction_hash = db.Column(db.String(100))
    verification_status = db.Column(db.String(20), default='pending')
    gas_used = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime)

class SmartContract(db.Model):
    """Manage smart contracts for automated payments"""
    id = db.Column(db.Integer, primary_key=True)
    contract_address = db.Column(db.String(100))
    contract_type = db.Column(db.String(50))  # payment_release, escrow, etc.
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'))
    conditions = db.Column(JSON)  # Smart contract conditions
    status = db.Column(db.String(20), default='active')  # active, executed, cancelled
    execution_data = db.Column(JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime)

class ExpenseTracking(db.Model):
    """AI-powered expense tracking with receipt scanning"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50))  # AI-categorized
    subcategory = db.Column(db.String(50))
    description = db.Column(db.Text)
    vendor_name = db.Column(db.String(200))
    
    # Receipt scanning data
    receipt_image_path = db.Column(db.String(200))
    ocr_extracted_data = db.Column(JSON)
    ai_confidence_score = db.Column(db.Float)
    manual_verification_needed = db.Column(db.Boolean, default=False)
    
    # Tax and business data
    tax_deductible = db.Column(db.Boolean, default=False)
    business_purpose = db.Column(db.Text)
    project_id = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InventoryItem(db.Model):
    """Smart inventory management with AI predictions"""
    id = db.Column(db.Integer, primary_key=True)
    item_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    current_stock = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Nos')
    cost_price = db.Column(db.Float)
    selling_price = db.Column(db.Float)
    reorder_level = db.Column(db.Float)
    max_stock_level = db.Column(db.Float)
    
    # AI-Enhanced Inventory Features
    ai_demand_forecast = db.Column(JSON)  # AI demand forecasting data
    ai_reorder_suggestions = db.Column(JSON)  # AI reorder recommendations
    abc_classification = db.Column(db.String(1))  # A, B, or C classification
    seasonal_pattern = db.Column(JSON)  # AI-detected seasonal patterns
    supplier_lead_time = db.Column(db.Integer)  # Days
    
    # Tracking
    last_reorder_date = db.Column(db.Date)
    last_sold_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PaymentReminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    reminder_date = db.Column(db.DateTime, nullable=False)
    reminder_type = db.Column(db.String(50))
    status = db.Column(db.String(20), default='Pending')
    notes = db.Column(db.Text)
    
    # AI-Enhanced Reminders
    ai_personalization_data = db.Column(JSON)  # AI-personalized reminder content
    optimal_send_time = db.Column(db.DateTime)  # AI-predicted best send time
    escalation_level = db.Column(db.Integer, default=1)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BusinessSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    setting_type = db.Column(db.String(50), default='general')  # general, ai, blockchain, etc.
    ai_managed = db.Column(db.Boolean, default=False)  # AI can modify this setting
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class DocumentTemplate(db.Model):
    """AI-generated and customizable document templates"""
    id = db.Column(db.Integer, primary_key=True)
    template_name = db.Column(db.String(100), nullable=False)
    template_type = db.Column(db.String(50))  # invoice, challan, quotation, etc.
    template_data = db.Column(JSON)  # Template structure and styling
    ai_generated = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    rating = db.Column(db.Float, default=0.0)
    is_public = db.Column(db.Boolean, default=False)  # Available in marketplace
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
