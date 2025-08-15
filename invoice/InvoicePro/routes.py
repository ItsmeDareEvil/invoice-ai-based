import os
import json
import logging
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session, abort
from werkzeug.utils import secure_filename
from sqlalchemy import func, and_, or_, extract, desc
from sqlalchemy.orm import joinedload

from app import app, db
from models import *
from utils import *
from pdf_generator import generate_invoice_pdf, generate_challan_pdf
from ai_services import ai_assistant, predictive_analytics, inventory_ai
from blockchain_service import blockchain_service, smart_contract_manager
from ocr_service import ocr_processor, receipt_processor
from voice_service import voice_processor, voice_invoice_builder
from analytics_engine import AnalyticsEngine

# Initialize analytics engine
analytics_engine = AnalyticsEngine()

def login_required(f):
    """Decorator to require login for routes"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash('Welcome back! AI-powered invoice system is ready.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    """AI-powered dashboard with predictive analytics"""
    try:
        # Get basic statistics
        total_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
            Invoice.payment_status == 'Paid'
        ).scalar() or 0
        
        outstanding_amount = db.session.query(func.sum(Invoice.total_amount - Invoice.amount_paid)).filter(
            Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
        ).scalar() or 0
        
        total_invoices = Invoice.query.count()
        total_clients = Client.query.count()
        
        # AI-powered insights
        ai_insights = {}
        if app.config.get("AI_FEATURES_ENABLED") and predictive_analytics:
            try:
                cash_flow_prediction = predictive_analytics.predict_cash_flow(6)
                payment_patterns = predictive_analytics.analyze_client_payment_patterns()
                ai_insights = {
                    'cash_flow': cash_flow_prediction,
                    'payment_patterns': payment_patterns
                }
            except Exception as e:
                logging.error(f"AI insights generation failed: {e}")
        
        # Recent activities
        recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(10).all()
        upcoming_payments = Invoice.query.filter(
            Invoice.due_date >= datetime.now().date(),
            Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
        ).order_by(Invoice.due_date.asc()).limit(10).all()
        
        # Analytics data
        monthly_revenue = analytics_engine.get_monthly_revenue_trend()
        client_analytics = analytics_engine.get_client_performance_metrics()
        
        # Blockchain statistics
        blockchain_stats = {}
        if app.config.get("BLOCKCHAIN_ENABLED") and blockchain_service:
            try:
                blockchain_stats = blockchain_service.get_blockchain_stats()
            except Exception as e:
                logging.error(f"Blockchain stats failed: {e}")
        
        return render_template('dashboard.html',
                             total_revenue=total_revenue,
                             outstanding_amount=outstanding_amount,
                             total_invoices=total_invoices,
                             total_clients=total_clients,
                             recent_invoices=recent_invoices,
                             upcoming_payments=upcoming_payments,
                             monthly_revenue=monthly_revenue,
                             client_analytics=client_analytics,
                             ai_insights=ai_insights,
                             blockchain_stats=blockchain_stats,
                             today=datetime.now())
                             
    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        flash('Error loading dashboard data.', 'error')
        return render_template('dashboard.html', error=str(e))

@app.route('/invoices')
@login_required
def invoice_management():
    """Advanced invoice management with AI filtering"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    client_filter = request.args.get('client_id', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    # Build query
    query = Invoice.query.options(joinedload(Invoice.client))
    
    if search:
        query = query.join(Client).filter(
            or_(
                Invoice.invoice_number.contains(search),
                Client.name.contains(search),
                Client.phone.contains(search),
                Client.email.contains(search)
            )
        )
    
    if status_filter:
        query = query.filter(Invoice.payment_status == status_filter)
    
    if client_filter:
        query = query.filter(Invoice.client_id == client_filter)
    
    if date_from:
        query = query.filter(Invoice.invoice_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Invoice.invoice_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    # Pagination
    invoices = query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get clients for filter dropdown
    clients = Client.query.order_by(Client.name).all()
    
    # AI insights for invoices
    ai_invoice_insights = {}
    if app.config.get("AI_FEATURES_ENABLED") and ai_assistant:
        try:
            # Get payment delay predictions
            ai_invoice_insights = analytics_engine.get_ai_invoice_insights(
                [inv.id for inv in invoices.items]
            )
        except Exception as e:
            logging.error(f"AI invoice insights failed: {e}")
    
    return render_template('invoice_management.html',
                         invoices=invoices,
                         clients=clients,
                         search=search,
                         status_filter=status_filter,
                         client_filter=client_filter,
                         date_from=date_from,
                         date_to=date_to,
                         ai_insights=ai_invoice_insights)

@app.route('/create_invoice', methods=['GET', 'POST'])
@login_required
def create_invoice():
    """AI-enhanced invoice creation with voice commands"""
    if request.method == 'POST':
        try:
            # Extract form data
            client_id = request.form.get('client_id')
            invoice_date_str = request.form.get('invoice_date')
            due_date_str = request.form.get('due_date')
            notes = request.form.get('notes', '')
            terms_conditions = request.form.get('terms_conditions', '')
            
            # Parse dates
            invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date() if invoice_date_str else datetime.now().date()
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None
            
            # Generate invoice number
            invoice_number = generate_invoice_number()
            
            # Create invoice
            invoice = Invoice(
                invoice_number=invoice_number,
                client_id=client_id,
                invoice_date=invoice_date,
                due_date=due_date,
                notes=notes,
                terms_conditions=terms_conditions,
                ai_generated=request.form.get('ai_generated') == 'true',
                voice_command_created=request.form.get('voice_created') == 'true'
            )
            
            db.session.add(invoice)
            db.session.flush()
            
            # Process line items
            line_items_data = json.loads(request.form.get('line_items', '[]'))
            subtotal = 0
            total_tax = 0
            
            for i, item_data in enumerate(line_items_data, 1):
                quantity = float(item_data['quantity'])
                unit_price = float(item_data['unit_price'])
                tax_percentage = float(item_data.get('tax_percentage', 18.0))
                
                line_total = quantity * unit_price
                tax_amount = (line_total * tax_percentage) / 100
                
                line_item = InvoiceLineItem(
                    invoice_id=invoice.id,
                    sr_no=i,
                    hsn_code=item_data.get('hsn_code', ''),
                    description=item_data['description'],
                    quantity=quantity,
                    unit=item_data.get('unit', 'Nos'),
                    unit_price=unit_price,
                    tax_percentage=tax_percentage,
                    tax_amount=tax_amount,
                    total_amount=line_total + tax_amount,
                    cost_price=float(item_data.get('cost_price', 0)),
                    ai_suggested=item_data.get('ai_suggested', False)
                )
                
                db.session.add(line_item)
                subtotal += line_total
                total_tax += tax_amount
            
            # Calculate taxes based on client location
            client = Client.query.get(client_id)
            company = Company.query.first()
            
            if client and company and client.state == company.state:
                # Same state - CGST + SGST
                invoice.cgst = total_tax / 2
                invoice.sgst = total_tax / 2
                invoice.igst = 0
            else:
                # Different state - IGST
                invoice.igst = total_tax
                invoice.cgst = 0
                invoice.sgst = 0
            
            invoice.subtotal = subtotal
            invoice.total_amount = subtotal + total_tax
            
            # Generate QR code for payments
            invoice.qr_payment_code = generate_payment_qr_code(invoice)
            
            # AI risk assessment
            if app.config.get("AI_FEATURES_ENABLED") and ai_assistant:
                try:
                    risk_assessment = ai_assistant.analyze_client_history(client_id)
                    invoice.ai_risk_assessment = risk_assessment
                    invoice.predicted_payment_date = predict_payment_date(invoice, risk_assessment)
                except Exception as e:
                    logging.error(f"AI risk assessment failed: {e}")
            
            # Add to blockchain if enabled
            if app.config.get("BLOCKCHAIN_ENABLED") and blockchain_service:
                try:
                    blockchain_hash = blockchain_service.add_invoice_to_blockchain(invoice)
                    if blockchain_hash:
                        logging.info(f"Invoice {invoice_number} added to blockchain")
                except Exception as e:
                    logging.error(f"Blockchain addition failed: {e}")
            
            db.session.commit()
            
            flash('AI-powered invoice created successfully!', 'success')
            return redirect(url_for('invoice_detail', id=invoice.id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Invoice creation failed: {e}")
            flash(f'Error creating invoice: {str(e)}', 'error')
    
    # GET request - show form
    clients = Client.query.order_by(Client.name).all()
    
    # AI suggestions for new invoice
    ai_suggestions = {}
    client_id = request.args.get('client_id')
    if client_id and app.config.get("AI_FEATURES_ENABLED") and ai_assistant:
        try:
            ai_suggestions = ai_assistant.suggest_invoice_items(int(client_id))
        except Exception as e:
            logging.error(f"AI suggestions failed: {e}")
    
    return render_template('create_invoice.html',
                         clients=clients,
                         ai_suggestions=ai_suggestions,
                         today=datetime.now())

@app.route('/invoice/<int:id>')
@login_required
def invoice_detail(id):
    """Detailed invoice view with blockchain verification"""
    invoice = Invoice.query.get_or_404(id)
    
    # Blockchain verification
    blockchain_verification = {}
    if app.config.get("BLOCKCHAIN_ENABLED") and blockchain_service and invoice.blockchain_hash:
        try:
            blockchain_verification = blockchain_service.verify_invoice_integrity(id)
        except Exception as e:
            logging.error(f"Blockchain verification failed: {e}")
    
    # AI insights for this invoice
    ai_insights = {}
    if app.config.get("AI_FEATURES_ENABLED") and ai_assistant:
        try:
            client_analysis = ai_assistant.analyze_client_history(invoice.client_id)
            ai_insights = {
                'payment_prediction': client_analysis.get('risk_assessment', {}),
                'similar_invoices': analytics_engine.find_similar_invoices(id)
            }
        except Exception as e:
            logging.error(f"AI insights failed: {e}")
    
    return render_template('invoice_detail.html',
                         invoice=invoice,
                         blockchain_verification=blockchain_verification,
                         ai_insights=ai_insights)

@app.route('/invoice/<int:id>/pdf')
@login_required
def invoice_pdf(id):
    """Generate PDF for invoice"""
    invoice = Invoice.query.get_or_404(id)
    try:
        pdf_buffer = generate_invoice_pdf(invoice)
        return send_file(pdf_buffer,
                        as_attachment=True,
                        download_name=f'Invoice_{invoice.invoice_number}.pdf',
                        mimetype='application/pdf')
    except Exception as e:
        logging.error(f"PDF generation failed: {e}")
        flash('Error generating PDF', 'error')
        return redirect(url_for('invoice_detail', id=id))

@app.route('/clients')
@login_required
def client_management():
    """Advanced client management with AI insights"""
    search = request.args.get('search', '')
    client_type = request.args.get('type', '')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = Client.query
    
    if search:
        query = query.filter(
            or_(
                Client.name.contains(search),
                Client.phone.contains(search),
                Client.email.contains(search),
                Client.contact_person.contains(search)
            )
        )
    
    if client_type:
        query = query.filter(Client.client_type == client_type)
    
    # Pagination
    clients = query.order_by(Client.name).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # AI insights for clients
    client_insights = {}
    if app.config.get("AI_FEATURES_ENABLED") and ai_assistant:
        try:
            for client in clients.items:
                if client.ai_risk_score > 0:
                    client_insights[client.id] = {
                        'risk_level': 'High' if client.ai_risk_score > 0.7 else 'Medium' if client.ai_risk_score > 0.3 else 'Low',
                        'predicted_ltv': client.predicted_ltv,
                        'payment_behavior': client.payment_behavior_pattern
                    }
        except Exception as e:
            logging.error(f"Client insights failed: {e}")
    
    return render_template('client_management.html',
                         clients=clients,
                         search=search,
                         client_type=client_type,
                         client_insights=client_insights)

@app.route('/create_client', methods=['GET', 'POST'])
@login_required
def create_client():
    """Create new client with AI enhancements"""
    if request.method == 'POST':
        try:
            client = Client(
                name=request.form.get('name'),
                contact_person=request.form.get('contact_person'),
                address=request.form.get('address'),
                city=request.form.get('city'),
                state=request.form.get('state'),
                pincode=request.form.get('pincode'),
                phone=request.form.get('phone'),
                email=request.form.get('email'),
                gstin=request.form.get('gstin'),
                pan=request.form.get('pan'),
                client_type=request.form.get('client_type', 'Regular'),
                lead_stage=request.form.get('lead_stage', 'New'),
                notes=request.form.get('notes', ''),
                tags=request.form.get('tags', ''),
                blockchain_verified=request.form.get('blockchain_verified') == 'on'
            )
            
            # Set follow-up date if provided
            follow_up_date = request.form.get('follow_up_date')
            if follow_up_date:
                client.follow_up_date = datetime.strptime(follow_up_date, '%Y-%m-%d').date()
            
            db.session.add(client)
            db.session.commit()
            
            flash('Client created successfully!', 'success')
            return redirect(url_for('client_management'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Client creation failed: {e}")
            flash(f'Error creating client: {str(e)}', 'error')
    
    return render_template('create_client.html')

@app.route('/analytics')
@login_required
def analytics():
    """Advanced analytics dashboard with AI insights"""
    try:
        # Time range for analytics
        time_range = request.args.get('range', '12m')  # 12 months default
        
        # Generate comprehensive analytics
        analytics_data = {
            'revenue_trends': analytics_engine.get_revenue_trends(time_range),
            'client_performance': analytics_engine.get_client_performance_metrics(),
            'payment_analytics': analytics_engine.get_payment_analytics(),
            'profitability_analysis': analytics_engine.get_profitability_analysis(),
            'ai_predictions': {},
            'blockchain_insights': {}
        }
        
        # AI-powered predictions
        if app.config.get("AI_FEATURES_ENABLED") and predictive_analytics:
            try:
                analytics_data['ai_predictions'] = {
                    'cash_flow': predictive_analytics.predict_cash_flow(6),
                    'payment_patterns': predictive_analytics.analyze_client_payment_patterns()
                }
            except Exception as e:
                logging.error(f"AI predictions failed: {e}")
        
        # Blockchain analytics
        if app.config.get("BLOCKCHAIN_ENABLED") and blockchain_service:
            try:
                analytics_data['blockchain_insights'] = blockchain_service.get_blockchain_stats()
            except Exception as e:
                logging.error(f"Blockchain analytics failed: {e}")
        
        return render_template('analytics.html', analytics_data=analytics_data)
        
    except Exception as e:
        logging.error(f"Analytics error: {e}")
        flash('Error loading analytics data.', 'error')
        return render_template('analytics.html', error=str(e))

@app.route('/ai_assistant')
@login_required
def ai_assistant_page():
    """AI Assistant interface"""
    return render_template('ai_assistant.html')

@app.route('/settings')
@login_required
def settings():
    """Application settings with AI and blockchain configuration"""
    company = Company.query.first()
    user = User.query.get(session['user_id'])
    business_settings = BusinessSettings.query.all()
    
    settings_data = {
        'company': company,
        'user': user,
        'business_settings': {setting.key: setting.value for setting in business_settings},
        'ai_enabled': app.config.get("AI_FEATURES_ENABLED", False),
        'blockchain_enabled': app.config.get("BLOCKCHAIN_ENABLED", False)
    }
    
    return render_template('settings.html', settings_data=settings_data)

# API Routes for AJAX and Advanced Features

@app.route('/api/voice_command', methods=['POST'])
@login_required
def api_voice_command():
    """Process voice commands"""
    if not app.config.get("AI_FEATURES_ENABLED") or not voice_processor:
        return jsonify({'error': 'Voice commands not available'})
    
    try:
        data = request.get_json()
        voice_text = data.get('text', '')
        context = data.get('context', {})
        
        result = voice_processor.process_voice_command(
            session['user_id'], voice_text, context
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Voice command API failed: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/ai_suggestions/<int:client_id>')
@login_required
def api_ai_suggestions(client_id):
    """Get AI suggestions for invoice items"""
    if not app.config.get("AI_FEATURES_ENABLED") or not ai_assistant:
        return jsonify({'error': 'AI features not available'})
    
    try:
        context = request.args.get('context', '')
        suggestions = ai_assistant.suggest_invoice_items(client_id, context)
        return jsonify({'suggestions': suggestions})
        
    except Exception as e:
        logging.error(f"AI suggestions API failed: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/document_scan', methods=['POST'])
@login_required
def api_document_scan():
    """OCR document scanning API"""
    if not app.config.get("AI_FEATURES_ENABLED") or not ocr_processor:
        return jsonify({'error': 'OCR features not available'})
    
    try:
        if 'document' not in request.files:
            return jsonify({'error': 'No document provided'})
        
        file = request.files['document']
        if file.filename == '':
            return jsonify({'error': 'No file selected'})
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process with OCR
        scan_type = request.form.get('type', 'invoice')
        
        if scan_type == 'receipt':
            result = receipt_processor.extract_receipt_data(filepath)
        else:
            result = ocr_processor.extract_invoice_data(filepath)
        
        # Clean up uploaded file
        os.remove(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Document scan API failed: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/blockchain_verify/<int:invoice_id>')
@login_required
def api_blockchain_verify(invoice_id):
    """Blockchain verification API"""
    if not app.config.get("BLOCKCHAIN_ENABLED") or not blockchain_service:
        return jsonify({'error': 'Blockchain features not available'})
    
    try:
        verification = blockchain_service.verify_invoice_integrity(invoice_id)
        return jsonify(verification)
        
    except Exception as e:
        logging.error(f"Blockchain verification API failed: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/inventory_forecast/<int:item_id>')
@login_required
def api_inventory_forecast(item_id):
    """Inventory demand forecasting API"""
    if not app.config.get("AI_FEATURES_ENABLED") or not inventory_ai:
        return jsonify({'error': 'AI inventory features not available'})
    
    try:
        days_ahead = request.args.get('days', 30, type=int)
        forecast = inventory_ai.forecast_demand(item_id, days_ahead)
        return jsonify(forecast)
        
    except Exception as e:
        logging.error(f"Inventory forecast API failed: {e}")
        return jsonify({'error': str(e)})

@app.route('/api/analytics_data')
@login_required
def api_analytics_data():
    """Real-time analytics data API"""
    try:
        data_type = request.args.get('type', 'revenue')
        time_range = request.args.get('range', '12m')
        
        if data_type == 'revenue':
            data = analytics_engine.get_revenue_trends(time_range)
        elif data_type == 'clients':
            data = analytics_engine.get_client_performance_metrics()
        elif data_type == 'payments':
            data = analytics_engine.get_payment_analytics()
        else:
            data = {'error': 'Invalid data type'}
        
        return jsonify(data)
        
    except Exception as e:
        logging.error(f"Analytics API failed: {e}")
        return jsonify({'error': str(e)})

# Error Handlers

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Context Processors

@app.context_processor
def inject_globals():
    """Inject global template variables"""
    return {
        'ai_enabled': app.config.get("AI_FEATURES_ENABLED", False),
        'blockchain_enabled': app.config.get("BLOCKCHAIN_ENABLED", False),
        'current_user_id': session.get('user_id'),
        'is_admin': session.get('is_admin', False)
    }

