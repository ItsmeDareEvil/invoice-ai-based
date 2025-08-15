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
app.secret_key = os.environ.get("SESSION_SECRET", "revolutionary-invoice-ai-system-2025")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database to use SQLite
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///revolutionary_invoice.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# AI and Advanced Features Configuration
app.config["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY")
app.config["BLOCKCHAIN_ENABLED"] = os.environ.get("BLOCKCHAIN_ENABLED", "true").lower() == "true"
app.config["AI_FEATURES_ENABLED"] = os.environ.get("AI_FEATURES_ENABLED", "true").lower() == "true"
app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)
db.init_app(app)

# Import models and routes after db initialization
with app.app_context():
    import models
    import routes
    from utils import number_to_words
    from ai_services import initialize_ai_models
    from blockchain_service import initialize_blockchain

    # Register custom Jinja2 filters
    app.jinja_env.filters['number_to_words'] = number_to_words

    db.create_all()
    
    # Initialize AI models if enabled
    if app.config["AI_FEATURES_ENABLED"]:
        try:
            initialize_ai_models()
            logging.info("AI models initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize AI models: {e}")
    
    # Initialize blockchain if enabled
    if app.config["BLOCKCHAIN_ENABLED"]:
        try:
            initialize_blockchain()
            logging.info("Blockchain service initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize blockchain: {e}")
    
    # Initialize default company data
    from models import Company, User
    from utils import generate_password_hash
    
    # Create default company if none exists
    if not Company.query.first():
        company = Company()
        company.name = 'Revolutionary Invoice Systems'
        company.address = 'Innovation Hub, Tech City, Digital District'
        company.city = 'Futureville'
        company.state = 'Technology State'
        company.pincode = '100001'
        company.phone = '+91-9999999999'
        company.email = 'hello@revolutionaryinvoice.ai'
        company.gstin = '33REVAA0000A1Z5'
        company.pan = 'REVAA0000A'
        company.website = 'https://revolutionaryinvoice.ai'
        company.logo_path = '/static/images/logo.svg'
        db.session.add(company)
        db.session.commit()
    
    # Create default admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@revolutionaryinvoice.ai',
            password_hash=generate_password_hash('RevolutionaryAI2025!'),
            is_admin=True,
            ai_features_enabled=True,
            voice_commands_enabled=True
        )
        db.session.add(admin_user)
        db.session.commit()
        logging.info("Default admin user created with advanced features enabled")
