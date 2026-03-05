"""
Celery tasks for asynchronous processing
"""
from celery import Celery, Task
from flask import current_app
import os
import logging
from app.utils.csv_parser import parse_csv_file, validate_csv_data
from app.services.pricing_service import ImportService
from app.models import db

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Celery with development-friendly settings
celery = Celery(__name__)

# Load default config
celery.conf.update(
    broker_url=os.environ.get('CELERY_BROKER_URL', 'memory://'),
    result_backend=os.environ.get('CELERY_RESULT_BACKEND', 'cache+memory://'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    always_eager=True,  # Execute tasks synchronously in development
    eager_propagates_exceptions=True
)


class ContextTask(Task):
    """Make celery tasks work with Flask app context"""
    def __call__(self, *args, **kwargs):
        from app import create_app
        app = create_app(os.environ.get('FLASK_ENV', 'development'))
        with app.app_context():
            return self.run(*args, **kwargs)


def make_celery(app):
    """Create Celery instance bound to Flask app"""
    # Update celery config with Flask config
    celery.conf.update(app.config)
    celery.Task = ContextTask
    
    # Bind app to celery for later use
    celery.app = app
    
    return celery


@celery.task(bind=True, base=ContextTask, name='app.celery_tasks.process_csv_upload')
def process_csv_upload(self, file_path, original_filename, task_id=None):
    """
    Asynchronous task to process CSV file upload
    
    Args:
        file_path: Path to the uploaded CSV file
        original_filename: Original filename for tracking
        task_id: Task ID for tracking
        
    Returns:
        dict: Processing result with success status and counts
    """
    try:
        logger.info(f"Starting CSV processing for file: {original_filename}")
        
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Parsing CSV file...',
                'filename': original_filename
            }
        )
        
        # Parse CSV
        df, parse_error, invalid_info = parse_csv_file(file_path)
        if parse_error:
            logger.error(f"CSV parsing failed: {parse_error}")
            return {
                'success': False,
                'error': parse_error,
                'imported_records': 0,
                'total_in_file': 0,
                'errors': [parse_error]
            }
        
        self.update_state(
            state='PROCESSING',
            meta={
                'current': 30,
                'total': 100,
                'status': 'Validating data...',
                'filename': original_filename
            }
        )
        
        # Validate data
        is_valid, validation_errors = validate_csv_data(df)
        if not is_valid:
            logger.error(f"CSV validation failed: {validation_errors}")
            return {
                'success': False,
                'error': 'CSV validation failed',
                'imported_records': 0,
                'errors': validation_errors
            }
        
        self.update_state(
            state='PROCESSING',
            meta={
                'current': 60,
                'total': 100,
                'status': 'Importing records...',
                'filename': original_filename
            }
        )
        
        # Import records
        from app import create_app
        app = create_app(os.environ.get('FLASK_ENV', 'development'))
        with app.app_context():
            success_count, import_errors, import_summary = ImportService.import_pricing_records(df, original_filename)
        
        self.update_state(
            state='PROCESSING',
            meta={
                'current': 90,
                'total': 100,
                'status': 'Cleaning up...',
                'filename': original_filename
            }
        )
        
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up uploaded file: {file_path}")
        
        # Combine all messages
        all_messages = []
        if invalid_info and invalid_info['invalid_rows'] > 0:
            all_messages.append(f"Skipped {invalid_info['invalid_rows']} rows with invalid data (malformed price/date)")
            for detail in invalid_info['invalid_details']:
                all_messages.append(f"  Line {detail['line']}: {detail['reason']}")
        
        # Check if import was rejected due to duplicates
        if success_count == 0 and import_summary.get('duplicates_skipped', 0) > 0:
            # Upload rejected due to "all or nothing" rule
            duplicate_details = []
            for detail in import_summary.get('duplicate_details', []):
                duplicate_details.append(f"  {detail}")
            
            total_in_file = invalid_info.get('total_rows', len(df)) if invalid_info else len(df)
            result = {
                'success': False,
                'message': f'Upload rejected: {import_summary["duplicates_skipped"]} duplicate record(s) found',
                'imported_records': 0,
                'total_in_file': total_in_file,
                'invalid_records': invalid_info.get('invalid_rows', 0) if invalid_info else 0,
                'duplicates_skipped': import_summary.get('duplicates_skipped', 0),
                'errors': duplicate_details if duplicate_details else []
            }
            logger.warning(f"CSV upload REJECTED: {import_summary['duplicates_skipped']} duplicates found - 0 records imported (all or nothing rule)")
            return result
        
        # Normal success case (no duplicates)
        error_details = []
        if invalid_info and invalid_info['invalid_rows'] > 0:
            for detail in invalid_info['invalid_details']:
                error_details.append(f"  Line {detail['line']}: {detail['reason']}")
        
        if import_errors:
            error_details.extend(import_errors)
        
        # Calculate total records in file
        total_in_file = invalid_info.get('total_rows', len(df)) if invalid_info else len(df)
        
        result = {
            'success': True,
            'message': f'Successfully imported {success_count} pricing records',
            'imported_records': success_count,
            'total_in_file': total_in_file,
            'invalid_records': invalid_info.get('invalid_rows', 0) if invalid_info else 0,
            'duplicates_skipped': 0,  # No duplicates were found (all or nothing rule)
            'errors': error_details if error_details else []
        }
        
        logger.info(f"CSV processing completed: {success_count} records imported, {invalid_info.get('invalid_rows', 0) if invalid_info else 0} invalid")
        return result
        
    except Exception as e:
        logger.error(f"CSV processing failed with exception: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': f'Upload failed: {str(e)}',
            'imported_records': 0,
            'errors': [str(e)]
        }


@celery.task(bind=True, name='app.celery_tasks.get_task_status')
def get_task_status(self, task_id):
    """
    Get the status of a processing task
    
    Args:
        task_id: The task ID to check
        
    Returns:
        dict: Task status and progress
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery)
    
    if result.state == 'PENDING':
        response = {
            'status': 'pending',
            'current': 0,
            'total': 100,
            'percent': 0
        }
    elif result.state == 'PROCESSING':
        response = {
            'status': 'processing',
            'current': result.info.get('current', 0),
            'total': result.info.get('total', 100),
            'percent': int(result.info.get('current', 0) / result.info.get('total', 100) * 100),
            'message': result.info.get('status', '')
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
            'error': str(result.info)
        }
    else:
        response = {
            'status': result.state,
            'current': 0,
            'total': 100
        }
    
    return response
