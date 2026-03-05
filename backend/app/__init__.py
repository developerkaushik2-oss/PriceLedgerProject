from flask import Flask, jsonify
from flask_cors import CORS
from flask_restx import Api, Resource
from config import config
import os
from app.models import db
from app.routes.pricing_api import CSVUpload, SearchPricing, PricingRecord, UploadStatus
from app.routes.stats_api import OverviewStats, CountryStats


def create_app(config_name='development'):
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Celery
    from app.celery_tasks import make_celery
    celery = make_celery(app)
    app.celery = celery
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize Flask-RESTX API
    api = Api(
        app,
        version='1.0.0',
        title='Price Ledger API',
        description='Retail Pricing Management System API',
        prefix='/api',
        doc='/api/docs'
    )
    
    # Register resource classes using add_resource()
    # Pricing resources
    api.add_resource(CSVUpload, '/pricing/upload_csv')
    api.add_resource(UploadStatus, '/pricing/upload_status/<string:task_id>')
    api.add_resource(SearchPricing, '/pricing/search')
    api.add_resource(PricingRecord, '/pricing/record/<string:record_id>')
    
    # Statistics resources
    api.add_resource(OverviewStats, '/stats/overview')
    api.add_resource(CountryStats, '/stats/by_country')
    
    # Health check endpoint
    class HealthCheck(Resource):
        """Health check endpoint"""
        def get(self):
            """Get API health status"""
            return {'status': 'healthy', 'version': '1.0.0'}, 200
    
    api.add_resource(HealthCheck, '/health')
    
    # Create uploads directory
    if not os.path.exists(app.config.get('UPLOAD_FOLDER', 'uploads')):
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Endpoint not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    # Context for creating tables
    with app.app_context():
        db.create_all()
    
    return app
