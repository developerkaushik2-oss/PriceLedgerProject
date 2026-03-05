from flask import Blueprint, jsonify
from app.models import db, Store, Product, PricingRecord
from sqlalchemy import func
from datetime import datetime, timedelta

bp = Blueprint('stats', __name__, url_prefix='/api/stats')


@bp.route('/overview', methods=['GET'])
def get_overview():
    """Get general statistics about the database"""
    try:
        total_stores = Store.query.count()
        total_products = Product.query.count()
        total_records = PricingRecord.query.count()
        
        # Get average price
        avg_price = db.session.query(func.avg(PricingRecord.price)).scalar() or 0
        
        # Get latest import date
        latest_import = PricingRecord.query.order_by(PricingRecord.created_at.desc()).first()
        latest_import_date = latest_import.created_at if latest_import else None
        
        return jsonify({
            'total_stores': total_stores,
            'total_products': total_products,
            'total_pricing_records': total_records,
            'average_price': float(avg_price) if avg_price else 0,
            'latest_import': latest_import_date.isoformat() if latest_import_date else None
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch stats: {str(e)}'}), 500


@bp.route('/by_country', methods=['GET'])
def get_stats_by_country():
    """Get pricing statistics grouped by country"""
    try:
        stats = db.session.query(
            Store.country,
            func.count(PricingRecord.id).label('record_count'),
            func.avg(PricingRecord.price).label('avg_price'),
            func.min(PricingRecord.price).label('min_price'),
            func.max(PricingRecord.price).label('max_price')
        ).join(Store).group_by(Store.country).all()
        
        result = [
            {
                'country': s[0],
                'record_count': s[1],
                'avg_price': float(s[2]) if s[2] else 0,
                'min_price': float(s[3]) if s[3] else 0,
                'max_price': float(s[4]) if s[4] else 0
            }
            for s in stats
        ]
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch country stats: {str(e)}'}), 500
