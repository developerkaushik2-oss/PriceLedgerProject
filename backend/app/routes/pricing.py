from flask import Blueprint, request, jsonify
from werkzeug.exceptions import BadRequest
from app.utils.csv_parser import allowed_file, parse_csv_file, validate_csv_data, save_uploaded_file
from app.services.pricing_service import ImportService, PricingService
import os

bp = Blueprint('pricing', __name__, url_prefix='/api/pricing')


@bp.route('/upload_csv', methods=['POST'])
def upload_csv():
    """
    Upload and process CSV file
    Expected file format: Store ID, SKU, Product Name, Price, Date
    """
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File must be a CSV file'}), 400
    
    try:
        # Save uploaded file
        file_path, error = save_uploaded_file(file)
        if error:
            return jsonify({'error': error}), 400
        
        # Parse CSV
        df, parse_error, invalid_info = parse_csv_file(file_path)
        if parse_error:
            return jsonify({'error': parse_error}), 400
        
        # Validate data
        is_valid, validation_errors = validate_csv_data(df)
        if not is_valid:
            return jsonify({
                'error': 'CSV validation failed',
                'details': validation_errors
            }), 400
        
        # Import records
        success_count, import_errors, import_summary = ImportService.import_pricing_records(df, file.filename)
        
        # Clean up uploaded file after processing
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Combine all errors/warnings from parsing and importing
        all_messages = []
        if invalid_info and invalid_info['invalid_rows'] > 0:
            all_messages.append(f"Skipped {invalid_info['invalid_rows']} rows with invalid data (malformed price/date)")
            for detail in invalid_info['invalid_details'][:5]:  # Show first 5
                all_messages.append(f"  Line {detail['line']}: {detail['reason']}")
            if len(invalid_info['invalid_details']) > 5:
                all_messages.append(f"  ... and {len(invalid_info['invalid_details']) - 5} more")
        
        if import_errors:
            all_messages.extend(import_errors)
        
        return jsonify({
            'success': True,
            'message': f'Successfully imported {success_count} pricing records',
            'imported_records': success_count,
            'total_in_file': invalid_info['total_rows'] if invalid_info else len(df) + success_count,
            'invalid_records': invalid_info['invalid_rows'] if invalid_info else 0,
            'duplicates_skipped': import_summary.get('duplicates_skipped', 0) if import_summary else 0,
            'errors': all_messages if all_messages else []
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@bp.route('/search', methods=['GET'])
def search_pricing():
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
        # Build filters from query parameters
        filters = {}
        
        if request.args.get('store_id'):
            filters['store_id'] = request.args.get('store_id')
        
        if request.args.get('sku'):
            filters['sku'] = request.args.get('sku')
        
        if request.args.get('product_name'):
            filters['product_name'] = request.args.get('product_name')
        
        if request.args.get('price_min'):
            try:
                filters['price_min'] = float(request.args.get('price_min'))
            except ValueError:
                return jsonify({'error': 'Invalid price_min value'}), 400
        
        if request.args.get('price_max'):
            try:
                filters['price_max'] = float(request.args.get('price_max'))
            except ValueError:
                return jsonify({'error': 'Invalid price_max value'}), 400
        
        if request.args.get('date_from'):
            from datetime import datetime
            try:
                filters['date_from'] = datetime.strptime(request.args.get('date_from'), '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date_from format (use YYYY-MM-DD)'}), 400
        
        if request.args.get('date_to'):
            from datetime import datetime
            try:
                filters['date_to'] = datetime.strptime(request.args.get('date_to'), '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date_to format (use YYYY-MM-DD)'}), 400
        
        if request.args.get('country'):
            filters['country'] = request.args.get('country')
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 500)  # Max 500 per page
        
        if page < 1:
            return jsonify({'error': 'Page must be >= 1'}), 400
        
        # Search
        results = PricingService.search_pricing_records(filters, page, per_page)
        
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({'error': f'Search failed: {str(e)}'}), 500


@bp.route('/record/<record_id>', methods=['GET'])
def get_record(record_id):
    """Get a specific pricing record by ID"""
    try:
        record = PricingService.get_pricing_record(record_id)
        
        if not record:
            return jsonify({'error': 'Record not found'}), 404
        
        return jsonify(record), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch record: {str(e)}'}), 500


@bp.route('/record/<record_id>', methods=['PUT'])
def update_record(record_id):
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
            return jsonify({'error': 'Content-Type must be application/json'}), 400
        
        data = request.get_json()
        
        # Validate required fields
        if 'price' not in data:
            return jsonify({'error': 'Price is required'}), 400
        
        try:
            price = float(data['price'])
            if price <= 0:
                return jsonify({'error': 'Price must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid price value'}), 400
        
        # Update record
        updated_record = PricingService.update_pricing_record(
            record_id,
            data,
            updated_by=request.headers.get('X-User', 'api_user')
        )
        
        return jsonify({
            'success': True,
            'message': 'Record updated successfully',
            'record': updated_record
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Update failed: {str(e)}'}), 500


@bp.route('/record/<record_id>', methods=['DELETE'])
def delete_record(record_id):
    """Delete a pricing record"""
    try:
        PricingService.delete_pricing_record(
            record_id,
            deleted_by=request.headers.get('X-User', 'api_user')
        )
        
        return jsonify({
            'success': True,
            'message': 'Record deleted successfully'
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500
