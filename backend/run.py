from app import create_app
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app = create_app(os.environ.get('FLASK_ENV', 'development'))
celery = app.celery

if __name__ == '__main__':
    app.run(
        host=os.environ.get('API_HOST', '0.0.0.0'),
        port=int(os.environ.get('API_PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )

