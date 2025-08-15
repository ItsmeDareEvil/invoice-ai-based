import os
from datetime import timedelta

# Company Information
COMPANY_NAME = "Revolutionary Invoice Systems"
COMPANY_ADDRESS = "Innovation Hub, Tech City, Digital District, Futureville"
COMPANY_CITY = "Futureville"
COMPANY_STATE = "Technology State"
COMPANY_PINCODE = "100001"
COMPANY_PHONE = "+91-9999999999"
COMPANY_EMAIL = "hello@revolutionaryinvoice.ai"
COMPANY_WEBSITE = "https://revolutionaryinvoice.ai"

# Tax Information
GSTIN = "33REVAA0000A1Z5"
PAN = "REVAA0000A"
TIN = "33999888777"

# Bank Details
BANK_NAME = "REVOLUTIONARY DIGITAL BANK"
ACCOUNT_NO = "999888777666555"
ACCOUNT_NAME = "Revolutionary Invoice Systems"
IFSC_CODE = "RDIG0001001"
BRANCH = "Tech City Branch"

# Application Configuration
SECRET_KEY = os.environ.get("SESSION_SECRET", "revolutionary-invoice-ai-system-2025")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///revolutionary_invoice.db")

# AI Configuration
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
AI_FEATURES_ENABLED = os.environ.get("AI_FEATURES_ENABLED", "true").lower() == "true"
AI_MODEL = "gpt-4o"  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024

# Blockchain Configuration
BLOCKCHAIN_ENABLED = os.environ.get("BLOCKCHAIN_ENABLED", "true").lower() == "true"
BLOCKCHAIN_NETWORK = os.environ.get("BLOCKCHAIN_NETWORK", "ethereum")
BLOCKCHAIN_CONTRACT_ADDRESS = os.environ.get("BLOCKCHAIN_CONTRACT_ADDRESS")

# File Upload Configuration
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

# Voice Command Configuration
VOICE_COMMANDS_ENABLED = os.environ.get("VOICE_COMMANDS_ENABLED", "true").lower() == "true"
SPEECH_RECOGNITION_LANGUAGE = "en-IN"  # English (India)

# OCR Configuration
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "/usr/bin/tesseract")
OCR_LANGUAGES = ["eng", "hin"]  # English and Hindi support

# Email Configuration
MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", COMPANY_EMAIL)

# SMS/WhatsApp Configuration (Twilio)
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")
TWILIO_WHATSAPP_NUMBER = os.environ.get("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# Redis Configuration (for real-time features)
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.environ.get("REDIS_ENABLED", "false").lower() == "true"

# Celery Configuration (for background tasks)
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

# Security Configuration
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

# Invoice Configuration
DEFAULT_PAYMENT_TERMS_DAYS = 30
DEFAULT_TAX_RATE = 18.0  # GST rate in percentage
INVOICE_NUMBER_PREFIX = "AI-INV"
CHALLAN_NUMBER_PREFIX = "AI-CH"

# Currency Configuration
DEFAULT_CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"
CURRENCY_FORMAT = "indian"  # indian/international

# Pagination Configuration
ITEMS_PER_PAGE = 20
MAX_ITEMS_PER_PAGE = 100

# Dashboard Configuration
DASHBOARD_CACHE_TIMEOUT = 300  # 5 minutes
RECENT_ACTIVITIES_LIMIT = 10
ANALYTICS_DEFAULT_PERIOD = 12  # months

# AI Features Configuration
AI_CONFIDENCE_THRESHOLD = 0.7
AI_SUGGESTIONS_LIMIT = 10
AI_RETRY_ATTEMPTS = 3
AI_TIMEOUT_SECONDS = 30

# Blockchain Configuration
BLOCKCHAIN_GAS_LIMIT = 21000
BLOCKCHAIN_GAS_PRICE = 20  # Gwei
BLOCKCHAIN_CONFIRMATION_BLOCKS = 3

# Multi-language Configuration
SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'हिन्दी',
    'ta': 'தமிழ்',
    'te': 'తెలుగు',
    'kn': 'ಕನ್ನಡ',
    'ml': 'മലയാളം',
    'gu': 'ગુજરાતી',
    'mr': 'मराठी',
    'bn': 'বাংলা',
    'pa': 'ਪੰਜਾਬੀ'
}
DEFAULT_LANGUAGE = 'en'

# Theme Configuration
SUPPORTED_THEMES = ['light', 'dark', 'auto']
DEFAULT_THEME = 'auto'

# PDF Configuration
PDF_DPI = 300
PDF_QUALITY = 95
PDF_WATERMARK_ENABLED = True
PDF_DIGITAL_SIGNATURE_ENABLED = True

# QR Code Configuration
QR_CODE_SIZE = 10
QR_CODE_BORDER = 4
QR_CODE_ERROR_CORRECTION = 'M'  # L, M, Q, H

# Inventory Configuration
INVENTORY_LOW_STOCK_THRESHOLD = 10
INVENTORY_REORDER_BUFFER_DAYS = 7
INVENTORY_ABC_ANALYSIS_ENABLED = True

# Analytics Configuration
ANALYTICS_RETENTION_DAYS = 365
ANALYTICS_BATCH_SIZE = 1000
ANALYTICS_CACHE_ENABLED = True

# Backup Configuration
BACKUP_ENABLED = os.environ.get("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_INTERVAL_HOURS = int(os.environ.get("BACKUP_INTERVAL_HOURS", "24"))
BACKUP_RETENTION_DAYS = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
BACKUP_STORAGE_PATH = os.environ.get("BACKUP_STORAGE_PATH", "./backups")

# API Rate Limiting
API_RATE_LIMIT = "100/hour"
API_RATE_LIMIT_STORAGE_URL = REDIS_URL

# Logging Configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = os.environ.get("LOG_FILE", "revolutionary_invoice.log")
LOG_MAX_SIZE = int(os.environ.get("LOG_MAX_SIZE", "10485760"))  # 10MB
LOG_BACKUP_COUNT = int(os.environ.get("LOG_BACKUP_COUNT", "5"))

# Performance Configuration
CACHE_TYPE = "simple"  # simple, redis, memcached
CACHE_DEFAULT_TIMEOUT = 300
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_timeout": 20,
    "max_overflow": 0
}

# Development Configuration
DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
TESTING = os.environ.get("FLASK_TESTING", "false").lower() == "true"

# Production Configuration
if not DEBUG:
    # Force HTTPS in production
    SESSION_COOKIE_SECURE = True
    # Enable additional security headers
    FORCE_HTTPS = True
    # Disable debug toolbar and profiling
    DEBUG_TB_ENABLED = False

# Feature Flags
FEATURE_VOICE_COMMANDS = os.environ.get("FEATURE_VOICE_COMMANDS", "true").lower() == "true"
FEATURE_BLOCKCHAIN = os.environ.get("FEATURE_BLOCKCHAIN", "true").lower() == "true"
FEATURE_AI_ASSISTANT = os.environ.get("FEATURE_AI_ASSISTANT", "true").lower() == "true"
FEATURE_OCR_SCANNING = os.environ.get("FEATURE_OCR_SCANNING", "true").lower() == "true"
FEATURE_REAL_TIME_COLLABORATION = os.environ.get("FEATURE_REAL_TIME_COLLABORATION", "true").lower() == "true"
FEATURE_AR_PREVIEW = os.environ.get("FEATURE_AR_PREVIEW", "true").lower() == "true"
FEATURE_MULTI_LANGUAGE = os.environ.get("FEATURE_MULTI_LANGUAGE", "true").lower() == "true"
FEATURE_INVENTORY_MANAGEMENT = os.environ.get("FEATURE_INVENTORY_MANAGEMENT", "true").lower() == "true"
FEATURE_EXPENSE_TRACKING = os.environ.get("FEATURE_EXPENSE_TRACKING", "true").lower() == "true"
FEATURE_SMART_CONTRACTS = os.environ.get("FEATURE_SMART_CONTRACTS", "true").lower() == "true"

