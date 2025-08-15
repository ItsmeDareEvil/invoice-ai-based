import shutil
from flask import render_template, request, redirect, url_for, flash, jsonify, send_file, session, request
from app import app, db
from models import *
from utils import *
from pdf_generator import generate_detailed_monthly_report, generate_invoice_pdf, generate_challan_pdf, export_excel
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, extract
from sqlalchemy.orm import joinedload
import xlsxwriter
import json
import csv
import io
import os

from twilio.rest import Client as TwilioClient
from twilio_config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from tempfile import NamedTemporaryFile
from pdf_generator import generate_invoice_pdf

# Import User model and password hashing utils
from models import User
from utils import generate_password_hash, check_password_hash

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def dashboard():
    # Dashboard analytics
    total_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
        Invoice.payment_status == 'Paid'
    ).scalar() or 0
    
    outstanding_amount = db.session.query(func.sum(Invoice.total_amount - Invoice.amount_paid)).filter(
        Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
    ).scalar() or 0
    
    total_invoices = Invoice.query.count()
    total_clients = Client.query.count()
    
    # Recent invoices
    recent_invoices = Invoice.query.order_by(Invoice.created_at.desc()).limit(5).all()
    
    # Outstanding invoices
    outstanding_invoices = Invoice.query.filter(
        Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
    ).order_by(Invoice.due_date.asc()).limit(10).all()
    
    # Monthly revenue for chart
    from utils import get_monthly_revenue_data
    monthly_revenue = get_monthly_revenue_data()

    # Pending reminders for dashboard
    reminders = Reminder.query.filter(
        Reminder.status == 'Pending',
        Reminder.reminder_date <= datetime.now()
    ).order_by(Reminder.reminder_date.asc()).limit(10).all()
    
    return render_template('dashboard.html', 
                         total_revenue=total_revenue,
                         outstanding_amount=outstanding_amount,
                         total_invoices=total_invoices,
                         total_clients=total_clients,
                         recent_invoices=recent_invoices,
                         outstanding_invoices=outstanding_invoices,
                         monthly_revenue=monthly_revenue,
                         reminders=reminders,
                         today=datetime.now().date())

@app.route('/invoices')
def invoices():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    client_id = request.args.get('client_id', '')
    
    query = Invoice.query
    
    if search:
        query = query.join(Client).filter(
            or_(
                Invoice.invoice_number.contains(search),
                Client.name.contains(search),
                Client.phone.contains(search)
            )
        )
    
    if status_filter:
        query = query.filter(Invoice.payment_status == status_filter)
    
    if client_id:
        query = query.filter(Invoice.client_id == client_id)
    
    if date_from:
        query = query.filter(Invoice.invoice_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Invoice.invoice_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    invoices = query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('view_invoice.html', invoices=invoices, 
                         search=search, status_filter=status_filter,
                         date_from=date_from, date_to=date_to,
                         today=datetime.now().date())

@app.route('/create_invoice', methods=['GET', 'POST'])
def create_invoice():
    from utils import generate_invoice_number

    if request.method == 'POST':
        try:
            # Get form data
            client_id = request.form.get('client_id')
            invoice_date_str = request.form.get('invoice_date')
            due_date_str = request.form.get('due_date')
            
            if invoice_date_str:
                invoice_date = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
            else:
                invoice_date = datetime.now().date()
                
            if due_date_str:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            else:
                due_date = None
            
            # Generate invoice number
            invoice_number = generate_invoice_number()
            
            # Create invoice
            invoice = Invoice()
            invoice.invoice_number = invoice_number
            invoice.client_id = client_id
            invoice.invoice_date = invoice_date
            invoice.due_date = due_date
            invoice.notes = request.form.get('notes', '')
            invoice.terms_conditions = request.form.get('terms_conditions', '')
            
            db.session.add(invoice)
            db.session.flush()  # Get invoice ID
            
            # Add line items
            subtotal = 0
            cgst_total = 0
            sgst_total = 0
            igst_total = 0
            
            line_items_data = json.loads(request.form.get('line_items', '[]'))
            
            for i, item in enumerate(line_items_data, 1):
                quantity = float(item['quantity'])
                unit_price = float(item['unit_price'])
                tax_percentage = float(item.get('tax_percentage', 18))
                
                line_total = quantity * unit_price
                tax_amount = (line_total * tax_percentage) / 100
                
                line_item = InvoiceLineItem(
                    invoice_id=invoice.id,
                    sr_no=i,
                    hsn_code=item.get('hsn_code', ''),
                    description=item['description'],
                    quantity=quantity,
                    unit=item.get('unit', 'Nos'),
                    unit_price=unit_price,
                    tax_percentage=tax_percentage,
                    tax_amount=tax_amount,
                    total_amount=line_total + tax_amount,
                    cost_price=float(item.get('cost_price', 0))
                )
                
                db.session.add(line_item)
                subtotal += line_total
                
                # Calculate CGST/SGST or IGST based on client state
                client = Client.query.get(client_id)
                company = Company.query.first()
                
                if client and company and client.state == company.state:
                    # Split actual tax amount
                    cgst_total += tax_amount / 2
                    sgst_total += tax_amount / 2
                else:
                    igst_total += tax_amount

            
            # Update invoice totals
            invoice.subtotal = subtotal
            invoice.cgst = cgst_total
            invoice.sgst = sgst_total
            invoice.igst = igst_total
            invoice.total_amount = subtotal + cgst_total + sgst_total + igst_total
            
            db.session.commit()
            flash('Invoice created successfully!', 'success')
            return redirect(url_for('invoice_detail', id=invoice.id, auto_close=1))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating invoice: {str(e)}', 'error')
    
    clients = Client.query.order_by(Client.name).all()
    return render_template('create_invoice.html', clients=clients, today=datetime.now())

@app.route('/invoice/<int:id>')
def invoice_detail(id):
    invoice = Invoice.query.get_or_404(id)
    return render_template('invoice_detail.html', invoice=invoice, today=datetime.now().date())

@app.route('/invoice/<int:id>/pdf')
def invoice_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    pdf_file = generate_invoice_pdf(invoice)
    return send_file(pdf_file, as_attachment=True, 
                    download_name=f'Invoice_{invoice.invoice_number}.pdf',
                    mimetype='application/pdf')

@app.route('/clients')
def clients():
    search = request.args.get('search', '')
    client_type = request.args.get('type', '')
    
    query = Client.query
    
    if search:
        query = query.filter(
            or_(
                Client.name.contains(search),
                Client.phone.contains(search),
                Client.email.contains(search)
            )
        )
    
    if client_type:
        query = query.filter(Client.client_type == client_type)
    
    clients = query.order_by(Client.name).all()
    return render_template('client_management.html', clients=clients, search=search)

@app.route('/create_client', methods=['GET', 'POST'])
def create_client():
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
                tags=request.form.get('tags', '')
            )
            
            # Set follow-up date if provided
            if request.form.get('follow_up_date'):
                client.follow_up_date = datetime.strptime(request.form.get('follow_up_date'), '%Y-%m-%d').date()
            
            db.session.add(client)
            db.session.commit()
            flash('Client created successfully!', 'success')
            return redirect(url_for('clients'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating client: {str(e)}', 'error')
    
    return render_template('create_client.html')

@app.route('/delivery_challans')
def delivery_challans():
    search = request.args.get('search', '')
    status_filter = request.args.get('status', '')
    
    query = DeliveryChallan.query
    
    if search:
        query = query.join(Client).filter(
            or_(
                DeliveryChallan.challan_number.contains(search),
                Client.name.contains(search)
            )
        )
    
    if status_filter:
        query = query.filter(DeliveryChallan.status == status_filter)
    
    challans = query.order_by(DeliveryChallan.created_at.desc()).all()
    return render_template('delivery_challan.html', challans=challans, search=search, status_filter=status_filter)

@app.route('/create_challan', methods=['GET', 'POST'])
def create_challan():
    from utils import generate_challan_number

    if request.method == 'POST':
        try:
            challan_number = generate_challan_number()
            
            challan = DeliveryChallan(
                challan_number=challan_number,
                client_id=request.form.get('client_id'),
                challan_date=datetime.strptime(request.form.get('challan_date'), '%Y-%m-%d').date(),
                delivery_date=datetime.strptime(request.form.get('delivery_date'), '%Y-%m-%d').date() if request.form.get('delivery_date') else None,
                notes=request.form.get('notes', '')
            )
            
            db.session.add(challan)
            db.session.flush()
            
            # Add line items
            raw_line_items = request.form.get('line_items')
            if not raw_line_items:
                raise ValueError("Line items missing.")

            line_items_data = json.loads(raw_line_items)

            
            for i, item in enumerate(line_items_data, 1):
                line_item = ChallanLineItem(
                    challan_id=challan.id,
                    sr_no=i,
                    hsn_code=item.get('hsn_code', ''),
                    description=item['description'],
                    quantity=float(item['quantity']),
                    unit=item.get('unit', 'Nos'),
                    unit_price=float(item.get('unit_price', 0)),
                    total_amount=float(item.get('quantity', 0)) * float(item.get('unit_price', 0))
                )
                
                db.session.add(line_item)
            
            db.session.commit()
            flash('Delivery Challan created successfully!', 'success')
            return redirect(url_for('delivery_challans'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating challan: {str(e)}', 'error')
    
    clients = Client.query.order_by(Client.name).all()
    return render_template('create_challan.html', clients=clients, today=datetime.now())

@app.route('/challan/<int:id>/details')
def challan_details(id):
    challan = DeliveryChallan.query.get_or_404(id)
    return render_template('partials/challan_detail.html', challan=challan)

@app.route('/challan/<int:id>/pdf')
def challan_pdf(id):
    challan = DeliveryChallan.query.get_or_404(id)
    pdf_file = generate_challan_pdf(challan)
    return send_file(pdf_file, as_attachment=True, 
                    download_name=f'Challan_{challan.challan_number}.pdf',
                    mimetype='application/pdf')

@app.route('/convert_multiple_challans_to_invoice')
def convert_multiple_challans_to_invoice():
    try:
        challan_ids_str = request.args.get('challan_ids', '')
        consolidation_option = request.args.get('consolidation_option', 'merge')
        due_date_str = request.args.get('due_date')
        notes = request.args.get('notes', '')

        if not challan_ids_str:
            flash('No challans selected for conversion', 'error')
            return redirect(url_for('delivery_challans'))

        challan_ids = [int(cid) for cid in challan_ids_str.split(',') if cid.isdigit()]
        challans = DeliveryChallan.query.filter(DeliveryChallan.id.in_(challan_ids)).all()

        if not challans:
            flash('Selected challans not found', 'error')
            return redirect(url_for('delivery_challans'))

        # Ensure all challans belong to the same client
        client_ids = set(ch.client_id for ch in challans)
        if len(client_ids) > 1:
            flash('Selected challans belong to different clients. Please select challans for one client only.', 'error')
            return redirect(url_for('delivery_challans'))

        client_id = client_ids.pop()

        # Generate invoice number
        invoice_number = generate_invoice_number()

        invoice_date = datetime.now().date()
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date() if due_date_str else None

        invoice = Invoice(
            invoice_number=invoice_number,
            client_id=client_id,
            invoice_date=invoice_date,
            due_date=due_date,
            notes=notes or f'Consolidated invoice from challans: {", ".join(ch.challan_number for ch in challans)}'
        )

        db.session.add(invoice)
        db.session.flush()

        subtotal = 0

        if consolidation_option == 'merge':
            # Merge all line items into one invoice
            sr_no = 1
            merged_items = {}

            for challan in challans:
                for item in challan.line_items:
                    key = (item.description, item.hsn_code, item.unit_price)
                    if key in merged_items:
                        merged_items[key].quantity += item.quantity
                        merged_items[key].total_amount += item.total_amount
                    else:
                        merged_items[key] = InvoiceLineItem(
                            invoice_id=invoice.id,
                            sr_no=sr_no,
                            hsn_code=item.hsn_code,
                            description=item.description,
                            quantity=item.quantity,
                            unit=item.unit,
                            unit_price=item.unit_price,
                            tax_percentage=18.0,
                            tax_amount=item.unit_price * item.quantity * 0.18,
                            total_amount=item.total_amount
                        )
                        sr_no += 1

            for item in merged_items.values():
                db.session.add(item)
                subtotal += item.unit_price * item.quantity

        else:
            # Group line items by challan number
            sr_no = 1
            for challan in challans:
                group_note = f'Items from Challan #{challan.challan_number}'
                group_item = InvoiceLineItem(
                    invoice_id=invoice.id,
                    sr_no=sr_no,
                    hsn_code='',
                    description=group_note,
                    quantity=0,
                    unit='',
                    unit_price=0,
                    tax_percentage=0,
                    tax_amount=0,
                    total_amount=0
                )
                db.session.add(group_item)
                sr_no += 1

                for item in challan.line_items:
                    invoice_item = InvoiceLineItem(
                        invoice_id=invoice.id,
                        sr_no=sr_no,
                        hsn_code=item.hsn_code,
                        description=item.description,
                        quantity=item.quantity,
                        unit=item.unit,
                        unit_price=item.unit_price,
                        tax_percentage=18.0,
                        tax_amount=item.unit_price * item.quantity * 0.18,
                        total_amount=item.total_amount
                    )
                    db.session.add(invoice_item)
                    subtotal += item.unit_price * item.quantity
                    sr_no += 1

        tax_amount = subtotal * 0.18
        invoice.subtotal = subtotal
        invoice.igst = tax_amount  # Assuming IGST for simplicity
        invoice.total_amount = subtotal + tax_amount

        # Update challan status and link to invoice
        for challan in challans:
            challan.status = 'Billed'
            challan.invoice_id = invoice.id

        db.session.commit()
        flash(f'Consolidated invoice {invoice.invoice_number} created from selected challans', 'success')
        return redirect(url_for('invoice_detail', id=invoice.id))

    except Exception as e:
        db.session.rollback()
        flash(f'Error converting challans: {str(e)}', 'error')
        return redirect(url_for('delivery_challans'))

@app.route('/crm')
def crm():
    # Lead statistics
    lead_stats = {
        'new': Client.query.filter(Client.lead_stage == 'New').count(),
        'discussion': Client.query.filter(Client.lead_stage == 'In Discussion').count(),
        'quoted': Client.query.filter(Client.lead_stage == 'Quoted').count(),
        'closed': Client.query.filter(Client.lead_stage == 'Closed').count()
    }

    # ✅ Follow-up reminders based on Reminder table
    follow_ups = Reminder.query.options(joinedload(Reminder.client)) \
    .filter(
        Reminder.reminder_type == 'Follow-up',
        Reminder.status != 'Completed'
    ) \
    .order_by(Reminder.reminder_date.asc()) \
    .limit(10).all()


    print(f"[DEBUG] Follow-up Query Result Count: {len(follow_ups)}")
    for r in follow_ups:
        print(f"[DEBUG] Follow-up → Client: {r.client.name}, Date: {r.reminder_date}, Note: {r.note if hasattr(r, 'note') else 'N/A'}")

    # Recent contacts
    recent_contacts = Client.query.filter(
        Client.last_contact_date.isnot(None)
    ).order_by(Client.last_contact_date.desc()).limit(10).all()

    # All clients
    clients = Client.query.order_by(Client.name).all()

    # All reminders
    reminders = Reminder.query.order_by(Reminder.reminder_date.asc()).all()

    # Overdue invoices
    forty_four_days_ago = datetime.now().date() - timedelta(days=44)
    overdue_invoices = Invoice.query.filter(
        and_(
            Invoice.invoice_date <= forty_four_days_ago,
            Invoice.payment_status != 'Paid'
        )
    ).all()

      

    return render_template('crm.html', 
                        lead_stats=lead_stats,
                        follow_ups=follow_ups,  # Now from Reminder
                        recent_contacts=recent_contacts,
                        clients=clients,
                        reminders=reminders,
                        overdue_invoices=overdue_invoices
                        )

@app.route('/api/contact_client_whatsapp', methods=['POST'])
def contact_client_whatsapp():
    return jsonify({'success': False, 'error': 'WhatsApp integration pending client setup'}), 501


@app.route('/api/send_invoice_whatsapp', methods=['POST'])
def send_invoice_whatsapp():
    data = request.get_json()
    invoice_id = data.get('invoice_id')
    if not invoice_id:
        return jsonify({'success': False, 'error': 'Missing invoice_id'}), 400
    
    invoice = Invoice.query.get(invoice_id)
    if not invoice:
        return jsonify({'success': False, 'error': 'Invoice not found'}), 404
    
    client = invoice.client
    if not client or not client.phone:
        return jsonify({'success': False, 'error': 'Client phone number not available'}), 400
    
    # Format client phone number for WhatsApp (E.164 format)
    phone_number = client.phone
    if not phone_number.startswith('+'):
        # Assuming country code +91 if not provided
        phone_number = '+91' + phone_number.lstrip('0')
    whatsapp_number = f'whatsapp:{phone_number}'
    
    # Generate invoice PDF file
    pdf_file = generate_invoice_pdf(invoice)
    
    # Use Twilio client to send WhatsApp message with media
    try:
        twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # TODO: Upload PDF to a public URL or storage and get media_url
        media_url = None  # Placeholder
        
        message_params = {
            'from_': TWILIO_WHATSAPP_NUMBER,
            'to': whatsapp_number,
            'body': f'Invoice #{invoice.invoice_number} from Your Company. Total Amount: ₹{invoice.total_amount:.2f}.'
        }
        
        if media_url:
            message_params['media_url'] = [media_url]
        
        message = twilio_client.messages.create(**message_params)
        
        return jsonify({'success': True, 'message_sid': message.sid})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/reminder/create', methods=['POST'])
def create_reminder():
    try:
        client_id = request.form.get('client_id')
        reminder_date_str = request.form.get('reminder_date')
        reminder_type = request.form.get('reminder_type')
        notes = request.form.get('notes', '')
        
        reminder_date = datetime.strptime(reminder_date_str, '%Y-%m-%dT%H:%M') if reminder_date_str else None
        
        reminder = Reminder(
            client_id=client_id,
            reminder_date=reminder_date,
            reminder_type=reminder_type,
            notes=notes,
            status='Pending'
        )
        
        db.session.add(reminder)
        db.session.commit()
        flash('Reminder created successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating reminder: {str(e)}', 'error')
    
    return redirect(url_for('crm'))

@app.route('/reminder/<int:id>/complete', methods=['POST'])
def complete_reminder(id):
    try:
        reminder = Reminder.query.get_or_404(id)
        reminder.status = 'Completed'
        db.session.commit()
        flash('Reminder marked as completed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating reminder: {str(e)}', 'error')
    return redirect(url_for('crm'))

@app.route('/reports')
def reports():
    from utils import get_monthly_revenue_data, get_tax_summary, get_client_analytics

    # Monthly revenue report
    monthly_revenue = get_monthly_revenue_data()
    
    # Tax summary
    tax_summary = get_tax_summary()
    
    # Client analytics
    client_analytics = get_client_analytics()
    print(get_monthly_revenue_data())
    print(get_tax_summary())
    print(get_client_analytics())

    
    return render_template('reports.html',
                         monthly_revenue=monthly_revenue,
                         tax_summary=tax_summary,
                         client_analytics=client_analytics)

@app.route('/export_csv')
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Invoice Number', 'Client Name', 'Date', 'Due Date', 'Amount', 'Status', 'Payment Date', 'Payment Mode'])
    
    # Write data
    invoices = Invoice.query.join(Client).all()
    for invoice in invoices:
        writer.writerow([
            invoice.invoice_number,
            invoice.client.name,
            invoice.invoice_date.strftime('%Y-%m-%d'),
            invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
            invoice.total_amount,
            invoice.payment_status,
            invoice.payment_date.strftime('%Y-%m-%d') if invoice.payment_date else '',
            invoice.payment_mode or ''
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'invoices_{datetime.now().strftime("%Y%m%d")}.csv'
    )

@app.route('/generate_tax_report')
def generate_tax_report():
    current_year = datetime.now().year
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(['Tax Type', 'Amount'])
    
    # Get tax summary
    tax_summary = get_tax_summary()
    
    # Write tax data
    writer.writerow(['CGST', f"Rs. {tax_summary['cgst']:.2f}"])
    writer.writerow(['SGST', f"Rs. {tax_summary['sgst']:.2f}"])
    writer.writerow(['Total Tax', f"Rs. {tax_summary['total']:.2f}"])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'tax_report_{current_year}.csv'
    )

#pdf report
@app.route('/generate_pdf_report')
def generate_pdf_report():
    year = request.args.get('year')
    month = request.args.get('month')
    return generate_detailed_monthly_report()

# backup database
@app.route('/backup_database')
def backup_database():
    # Path to your main SQLite DB file
    src_path = 'instance/invoice_tool.db'

    # Create timestamped backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f'invoice_tool_backup_{timestamp}.db'
    backup_path = os.path.join('backups', backup_filename)

    # Make sure the backups folder exists
    os.makedirs('backups', exist_ok=True)

    # Copy the SQLite DB to the backup file
    shutil.copy(src_path, backup_path)

    # Send the file as a downloadable attachment
    return send_file(
        backup_path,
        as_attachment=True,
        download_name=backup_filename,
        mimetype='application/octet-stream'
    )
# export excel
@app.route('/export_excel')
def export_excel_route():
    return export_excel()

# API Routes
@app.route('/api/client/<int:id>')
def get_client_api(id):
    client = Client.query.get_or_404(id)
    return jsonify({
        'id': client.id,
        'name': client.name,
        'address': client.address,
        'city': client.city,
        'state': client.state,
        'gstin': client.gstin,
        'phone': client.phone,
        'email': client.email
    })

@app.route('/api/client/<int:id>/invoices')
def get_client_invoices_api(id):
    client = Client.query.get_or_404(id)
    invoices = []
    
    for invoice in client.invoices:
        line_items = []
        for item in invoice.line_items:
            line_items.append({
                'description': item.description,
                'hsn_code': item.hsn_code,
                'quantity': item.quantity,
                'unit': item.unit,
                'unit_price': item.unit_price
            })
        
        invoices.append({
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'total_amount': invoice.total_amount,
            'line_items': line_items
        })
    
    return jsonify({'invoices': invoices})

@app.route('/api/dashboard/stats')
def dashboard_stats_api():
    total_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
        Invoice.payment_status == 'Paid'
    ).scalar() or 0
    
    outstanding_amount = db.session.query(func.sum(Invoice.total_amount - Invoice.amount_paid)).filter(
        Invoice.payment_status.in_(['Unpaid', 'Partially Paid'])
    ).scalar() or 0
    
    return jsonify({
        'total_revenue': float(total_revenue),
        'outstanding_amount': float(outstanding_amount),
        'total_invoices': Invoice.query.count(),
        'total_clients': Client.query.count()
    })

@app.route('/api/product-suggestions')
def product_suggestions_api():
    query = request.args.get('q', '')
    if len(query) < 3:
        return jsonify([])
    
    # Get unique product descriptions from line items
    suggestions = db.session.query(InvoiceLineItem.description.distinct()).filter(
        InvoiceLineItem.description.contains(query)
    ).limit(10).all()
    
    return jsonify([s[0] for s in suggestions])

@app.route('/update_payment_status', methods=['POST'])
def update_payment_status():
    try:
        invoice_id = request.form.get('invoice_id')
        payment_status = request.form.get('payment_status')
        amount_paid_str = request.form.get('amount_paid', '').strip()
        amount_paid = float(amount_paid_str) if amount_paid_str else 0.0
        payment_mode = request.form.get('payment_mode')
        payment_date_str = request.form.get('payment_date')
        payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date() if payment_date_str else None
        
        invoice = Invoice.query.get_or_404(invoice_id)
        invoice.payment_status = payment_status
        invoice.amount_paid = amount_paid
        invoice.payment_mode = payment_mode
        invoice.payment_date = payment_date
        
        db.session.commit()
        flash('Payment status updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating payment status: {str(e)}', 'error')
    
    return redirect(request.referrer or url_for('invoices'))

@app.route('/duplicate_invoice/<int:id>')
def duplicate_invoice(id):
    try:
        original_invoice = Invoice.query.get_or_404(id)
        
        # Create new invoice
        invoice_number = generate_invoice_number()
        new_invoice = Invoice(
            invoice_number=invoice_number,
            client_id=original_invoice.client_id,
            invoice_date=datetime.now().date(),
            due_date=None,
            subtotal=original_invoice.subtotal,
            cgst=original_invoice.cgst,
            sgst=original_invoice.sgst,
            igst=original_invoice.igst,
            total_amount=original_invoice.total_amount,
            notes=original_invoice.notes,
            terms_conditions=original_invoice.terms_conditions
        )
        
        db.session.add(new_invoice)
        db.session.flush()
        
        # Copy line items
        for original_item in original_invoice.line_items:
            new_item = InvoiceLineItem(
                invoice_id=new_invoice.id,
                sr_no=original_item.sr_no,
                hsn_code=original_item.hsn_code,
                description=original_item.description,
                quantity=original_item.quantity,
                unit=original_item.unit,
                unit_price=original_item.unit_price,
                tax_percentage=original_item.tax_percentage,
                tax_amount=original_item.tax_amount,
                total_amount=original_item.total_amount,
                cost_price=original_item.cost_price
            )
            db.session.add(new_item)
        
        db.session.commit()
        flash(f'Invoice duplicated as {invoice_number}', 'success')
        return redirect(url_for('invoice_detail', id=new_invoice.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error duplicating invoice: {str(e)}', 'error')
        return redirect(url_for('invoices'))

# Initialization is now handled in app.py

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Context processors
@app.context_processor
def utility_processor():
    return dict(
        today=datetime.now().date(),
        current_year=datetime.now().year
    )

# Template filters
@app.template_filter('currency')
def currency_filter(amount):
    return f"₹{amount:,.2f}" if amount else "₹0.00"

@app.template_filter('percentage')
def percentage_filter(value):
    return f"{value:.1f}%" if value else "0.0%"
