from app.models import db, Store, Product, PricingRecord
from sqlalchemy import func
from datetime import datetime


class StatsService:
    """Service for handling statistics and aggregations"""
    
    @staticmethod
    def get_overview_stats():
        """
        Get overview statistics about the database
        Returns: {
            'total_stores': int,
            'total_products': int,
            'total_pricing_records': int,
            'average_price': float,
            'latest_import': str (ISO format)
        }
        """
        try:
            total_stores = Store.query.count()
            total_products = Product.query.count()
            total_records = PricingRecord.query.count()
            
            # Get average price using SQLAlchemy aggregation
            avg_price_result = db.session.query(
                func.avg(PricingRecord.price)
            ).scalar()
            
            avg_price = float(avg_price_result) if avg_price_result else 0.0
            
            # Get latest import date
            latest_record = PricingRecord.query.order_by(
                PricingRecord.created_at.desc()
            ).first()
            
            latest_import = latest_record.created_at.isoformat() if latest_record else None
            
            return {
                'total_stores': total_stores,
                'total_products': total_products,
                'total_pricing_records': total_records,
                'average_price': avg_price,
                'latest_import': latest_import
            }
        
        except Exception as e:
            raise Exception(f"Error fetching overview stats: {str(e)}")
    
    @staticmethod
    def get_stats_by_country():
        """
        Get pricing statistics grouped by country
        Returns: [
            {
                'country': str,
                'record_count': int,
                'avg_price': float,
                'min_price': float,
                'max_price': float
            }
        ]
        """
        try:
            # Use SQLAlchemy query with aggregations and group by
            stats = db.session.query(
                Store.country,
                func.count(PricingRecord.id).label('record_count'),
                func.avg(PricingRecord.price).label('avg_price'),
                func.min(PricingRecord.price).label('min_price'),
                func.max(PricingRecord.price).label('max_price')
            ).join(
                PricingRecord, Store.id == PricingRecord.store_id
            ).group_by(
                Store.country
            ).order_by(
                Store.country
            ).all()
            
            result = []
            for stat in stats:
                result.append({
                    'country': stat[0],
                    'record_count': stat[1],
                    'avg_price': float(stat[2]) if stat[2] else 0.0,
                    'min_price': float(stat[3]) if stat[3] else 0.0,
                    'max_price': float(stat[4]) if stat[4] else 0.0
                })
            
            return result
        
        except Exception as e:
            raise Exception(f"Error fetching country stats: {str(e)}")
    
    @staticmethod
    def get_stats_by_store():
        """
        Get pricing statistics grouped by store
        Returns: [
            {
                'store_id': str,
                'store_name': str,
                'country': str,
                'record_count': int,
                'avg_price': float,
                'min_price': float,
                'max_price': float
            }
        ]
        """
        try:
            stats = db.session.query(
                Store.store_id,
                Store.store_name,
                Store.country,
                func.count(PricingRecord.id).label('record_count'),
                func.avg(PricingRecord.price).label('avg_price'),
                func.min(PricingRecord.price).label('min_price'),
                func.max(PricingRecord.price).label('max_price')
            ).join(
                PricingRecord, Store.id == PricingRecord.store_id
            ).group_by(
                Store.id, Store.store_id, Store.store_name, Store.country
            ).order_by(
                Store.store_id
            ).all()
            
            result = []
            for stat in stats:
                result.append({
                    'store_id': stat[0],
                    'store_name': stat[1],
                    'country': stat[2],
                    'record_count': stat[3],
                    'avg_price': float(stat[4]) if stat[4] else 0.0,
                    'min_price': float(stat[5]) if stat[5] else 0.0,
                    'max_price': float(stat[6]) if stat[6] else 0.0
                })
            
            return result
        
        except Exception as e:
            raise Exception(f"Error fetching store stats: {str(e)}")
    
    @staticmethod
    def get_stats_by_product():
        """
        Get pricing statistics grouped by product
        Returns: [
            {
                'sku': str,
                'product_name': str,
                'record_count': int,
                'avg_price': float,
                'min_price': float,
                'max_price': float
            }
        ]
        """
        try:
            stats = db.session.query(
                Product.sku,
                Product.product_name,
                func.count(PricingRecord.id).label('record_count'),
                func.avg(PricingRecord.price).label('avg_price'),
                func.min(PricingRecord.price).label('min_price'),
                func.max(PricingRecord.price).label('max_price')
            ).join(
                PricingRecord, Product.id == PricingRecord.product_id
            ).group_by(
                Product.id, Product.sku, Product.product_name
            ).order_by(
                Product.sku
            ).all()
            
            result = []
            for stat in stats:
                result.append({
                    'sku': stat[0],
                    'product_name': stat[1],
                    'record_count': stat[2],
                    'avg_price': float(stat[3]) if stat[3] else 0.0,
                    'min_price': float(stat[4]) if stat[4] else 0.0,
                    'max_price': float(stat[5]) if stat[5] else 0.0
                })
            
            return result
        
        except Exception as e:
            raise Exception(f"Error fetching product stats: {str(e)}")
    
    @staticmethod
    def get_price_trends(store_id=None, product_id=None, limit=30):
        """
        Get price trends over time
        Returns: [
            {
                'date': str (ISO format),
                'price': float,
                'store_id': str (if product_id specified),
                'sku': str (if store_id specified)
            }
        ]
        """
        try:
            query = PricingRecord.query.join(Store).join(Product)
            
            if store_id:
                query = query.filter(Store.store_id == store_id)
            
            if product_id:
                query = query.filter(Product.sku == product_id)
            
            # Order by date ascending (oldest first)
            results = query.order_by(
                PricingRecord.price_date.asc()
            ).limit(limit).all()
            
            trend = []
            for record in results:
                trend.append({
                    'date': record.price_date.isoformat(),
                    'price': float(record.price),
                    'store_id': record.store.store_id,
                    'sku': record.product.sku
                })
            
            return trend
        
        except Exception as e:
            raise Exception(f"Error fetching price trends: {str(e)}")
    
    @staticmethod
    def get_price_variance_stats():
        """
        Get statistics on price variance across stores for same products
        Returns: [
            {
                'sku': str,
                'product_name': str,
                'avg_price': float,
                'min_price': float,
                'max_price': float,
                'variance': float,
                'store_count': int
            }
        ]
        """
        try:
            # Group by product to find variance across stores
            stats = db.session.query(
                Product.sku,
                Product.product_name,
                func.avg(PricingRecord.price).label('avg_price'),
                func.min(PricingRecord.price).label('min_price'),
                func.max(PricingRecord.price).label('max_price'),
                func.count(func.distinct(PricingRecord.store_id)).label('store_count')
            ).join(
                PricingRecord, Product.id == PricingRecord.product_id
            ).group_by(
                Product.id, Product.sku, Product.product_name
            ).all()
            
            result = []
            for stat in stats:
                avg_price = float(stat[2]) if stat[2] else 0.0
                min_price = float(stat[3]) if stat[3] else 0.0
                max_price = float(stat[4]) if stat[4] else 0.0
                variance = max_price - min_price
                
                result.append({
                    'sku': stat[0],
                    'product_name': stat[1],
                    'avg_price': avg_price,
                    'min_price': min_price,
                    'max_price': max_price,
                    'variance': variance,
                    'store_count': stat[5]
                })
            
            return result
        
        except Exception as e:
            raise Exception(f"Error fetching price variance stats: {str(e)}")
