from flask_restx import Resource
from flask import request
from datetime import datetime
from celery.result import AsyncResult
from app.utils.csv_parser import allowed_file, save_uploaded_file
from app.services.pricing_service import PricingService
from app.celery_tasks import process_csv_upload
from app.models import db


# Constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 500
MIN_PAGE = 1


# ============================================================================
# Utility Functions (Module-level, not class methods)
# ============================================================================

def error_response(message, status_code):
    """Helper function for consistent error responses"""
    return {'error': message}, status_code


def parse_float(value, field_name):
    """Parse and validate float values"""
    try:
        return float(value)
    except (ValueError, TypeError):
        raise ValueError(f'Invalid {field_name} value')


def parse_date(value, field_name):
    """Parse and validate date values"""
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'Invalid {field_name} format (use YYYY-MM-DD)')


def validate_price(price):
    """Validate and parse price value"""
    try:
        price = float(price)
        if price <= 0:
            raise ValueError('Price must be positive')
        return price
    except (ValueError, TypeError) as e:
        raise ValueError('Invalid price value') from e


def build_search_filters():
    """Extract and validate filters from query parameters"""
    filters = {}
    
    # String filters (direct assignment)
    for field in ['store_id', 'sku', 'product_name', 'country']:
        if request.args.get(field):
            filters[field] = request.args.get(field)
    
    # Float filters (with validation)
    for field in ['price_min', 'price_max']:
        if request.args.get(field):
            filters[field] = parse_float(request.args.get(field), field)
    
    # Date filters (with validation)
    for field in ['date_from', 'date_to']:
        if request.args.get(field):
            filters[field] = parse_date(request.args.get(field), field)
    
    return filters


def get_pagination_params():
    """Extract and validate pagination parameters"""
    page = request.args.get('page', MIN_PAGE, type=int)
    per_page = min(request.args.get('per_page', DEFAULT_PAGE_SIZE, type=int), MAX_PAGE_SIZE)
    
    if page < MIN_PAGE:
        raise ValueError('Page must be >= 1')
    
    return page, per_page


# ============================================================================
# Resource Classes
# ============================================================================

class CSVUpload(Resource):
    """CSV file upload and processing"""
    
    def post(self):
        """
        Upload and process CSV file asynchronously
        Expected file format: Store ID, SKU, Product Name, Price, Date
        
        Returns:
            - task_id: ID to track the async processing task
            - status: Task status ('submitted')
        """
        # Check if file is present
        if 'file' not in request.files:
            return error_response('No file provided', 400)
        
        file = request.files['file']
        
        if file.filename == '':
            return error_response('No file selected', 400)
        
        if not allowed_file(file.filename):
            return error_response('File must be a CSV file', 400)
        
        try:
            # Save uploaded file
            file_path, error = save_uploaded_file(file)
            if error:
                return error_response(error, 400)
            
            # Submit async task to Celery
            task = process_csv_upload.delay(file_path, file.filename)
            
            return {
                'success': True,
                'message': 'File upload submitted for processing',
                'task_id': task.id,
                'status': 'submitted',
                'status_url': f'/api/pricing/upload_status/{task.id}'
            }, 202
            
        except Exception as e:
            return error_response(f'Upload submission failed: {str(e)}', 500)


class UploadStatus(Resource):
    """Check the status of a CSV upload task"""
    
    def get(self, task_id):
        """
        Get the status of a CSV upload task
        
        Args:
            task_id: The task ID returned from upload endpoint
            
        Returns:
            - status: Current task status (pending, processing, success, failure)
            - progress: Progress information if processing
            - result: Final result if completed
        """
        try:
            result = AsyncResult(task_id, app=process_csv_upload.app)
            print("continous polling is getting done!",result.state)
            if result.state == 'PENDING':
                response = {
                    'status': 'pending',
                    'percent': 0,
                    'current': 0,
                    'total': 100,
                    'message': 'Task is queued, waiting to be processed'
                }
            elif result.state == 'PROCESSING':
                response = {
                    'status': 'processing',
                    'current': result.info.get('current', 0),
                    'total': result.info.get('total', 100),
                    'percent': int(result.info.get('current', 0) / result.info.get('total', 100) * 100),
                    'message': result.info.get('status', 'Processing...')
                }
            elif result.state == 'SUCCESS':
                response = {
                    'status': 'success',
                    'current': 100,
                    'total': 100,
                    'percent': 100,
                    'result': result.result
                }
            elif result.state == 'FAILURE':
                response = {
                    'status': 'failure',
                    'error': str(result.info),
                    'message': 'Task processing failed'
                }
            else:
                response = {
                    'status': result.state,
                    'message': f'Task is in {result.state} state'
                }
            
            return response, 200
            
        except Exception as e:
            return error_response(f'Failed to get task status: {str(e)}', 500)


class SearchPricing(Resource):
    """Search pricing records with filters"""
    
    def get(self):
        """
        Search pricing records
        Query parameters:
        - store_id: Filter by store ID (partial match)
        - sku: Filter by SKU (partial match)
        - product_name: Filter by product name (partial match)
        - price_min: Filter by minimum price
        - price_max: Filter by maximum price
        - date_from: Filter by start date (YYYY-MM-DD)
        - date_to: Filter by end date (YYYY-MM-DD)
        - country: Filter by country (partial match)
        - page: Page number (default 1)
        - per_page: Records per page (default 50, max 500)
        """
        try:
            # Build filters and pagination params
            filters = build_search_filters()
            page, per_page = get_pagination_params()
            
            # Search using SQLAlchemy ORM service
            results = PricingService.search_pricing_records(filters, page, per_page)
            
            return results, 200
            
        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as e:
            return error_response(f'Search failed: {str(e)}', 500)


class PricingRecord(Resource):
    """Operations on a single pricing record"""
    
    def get(self, record_id):
        """Get a specific pricing record by ID"""
        try:
            record = PricingService.get_pricing_record(record_id)
            
            if not record:
                return error_response('Record not found', 404)
            
            return record, 200
            
        except Exception as e:
            return error_response(f'Failed to fetch record: {str(e)}', 500)
    
    def put(self, record_id):
        """
        Update a pricing record
        JSON body:
        {
            'price': 29.99,
            'change_reason': 'Price adjustment'
        }
        """
        try:
            if not request.is_json:
                return error_response('Content-Type must be application/json', 400)
            
            data = request.get_json()
            
            # Validate required fields
            if 'price' not in data:
                return error_response('Price is required', 400)
            
            # Validate and parse price
            data['price'] = validate_price(data['price'])
            
            # Update record using SQLAlchemy ORM service
            updated_record = PricingService.update_pricing_record(
                record_id,
                data,
                updated_by=request.headers.get('X-User', 'api_user')
            )
            
            return {
                'success': True,
                'message': 'Record updated successfully',
                'record': updated_record
            }, 200
            
        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as e:
            return error_response(f'Update failed: {str(e)}', 500)
    
    def delete(self, record_id):
        """Delete a pricing record"""
        try:
            # Delete using SQLAlchemy ORM service
            PricingService.delete_pricing_record(
                record_id,
                deleted_by=request.headers.get('X-User', 'api_user')
            )
            
            return {
                'success': True,
                'message': 'Record deleted successfully'
            }, 200
            
        except ValueError as e:
            return error_response(str(e), 404)
        except Exception as e:
            return error_response(f'Delete failed: {str(e)}', 500)