import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "invoice-tool-secret-key-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database to use SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///invoice_tool.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import models and routes after db initialization
with app.app_context():
    import models
    import routes
    from utils import number_to_words

    # Register custom Jinja2 filter
    app.jinja_env.filters['number_to_words'] = number_to_words

    db.create_all()
    
    # Initialize default company data
    from models import Company
    
    # Create default company if none exists
    if not Company.query.first():
        company = Company()
        company.name = 'OMPS ENGINEERING INDUSTRIES'
        company.address = 'No.39, 9th Street, Kamaraj Nagar'
        company.city = 'Avadi'
        company.state = 'Tamil Nadu'
        company.pincode = '600071'
        company.phone = '+91-9876543210'
        company.email = 'contact@ompsengineering.com'
        company.gstin = '33AAAAA0000A1Z5'
        company.pan = 'AAAAA0000A'
        db.session.add(company)
        db.session.commit()
    
    # Create default admin user if not exists
    from models import User
    from utils import generate_password_hash

    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password_hash=generate_password_hash('admin123')
        )
        db.session.add(admin_user)
        db.session.commit()
    
    # Import BusinessSettings here only if needed
    # from models import BusinessSettings
