import os
import logging
from app import app

# Force debug mode ON during local development
app.debug = True

# Configure logging (optional in dev)
if not app.debug:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        handlers=[
            logging.FileHandler('revolutionary_invoice.log'),
            logging.StreamHandler()
        ]
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5004))
    host = os.environ.get('HOST', '0.0.0.0')
    
    app.run(
        host=host,
        port=port,
        debug=app.debug  # Now app.debug is True
    )
