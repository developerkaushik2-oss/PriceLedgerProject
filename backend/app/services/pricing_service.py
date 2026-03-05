from app.models import db, Store, Product, PricingRecord
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import selectinload
from decimal import Decimal


# Constants
SEARCH_STRING_FIELDS = ['store_id', 'sku', 'product_name', 'country']
SEARCH_NUMERIC_FIELDS = {'price_min': 'min', 'price_max': 'max'}
SEARCH_DATE_FIELDS = ['date_from', 'date_to']


def _to_decimal(value):
    """Convert value to Decimal safely"""
    return Decimal(str(value))


def _apply_text_filter(query, model_field, value):
    """Apply case-insensitive text filter"""
    return query.filter(model_field.ilike(f"%{value}%"))


class PricingService:
    """Service for handling pricing record operations"""
    
    @staticmethod
    def search_pricing_records(filters=None, page=1, per_page=5):
        """
        Search pricing records with various criteria
        filters: {
            'store_id': str, 'sku': str, 'product_name': str,
            'price_min': float, 'price_max': float,
            'date_from': date, 'date_to': date, 'country': str
        }
        """
        # Build query with eager loading to avoid N+1 queries
        query = PricingRecord.query.options(
            selectinload(PricingRecord.store),
            selectinload(PricingRecord.product)
        ).join(Store).join(Product)
        
        if filters:
            # Text filters (store_id, sku, product_name, country)
            if filters.get('store_id'):
                query = _apply_text_filter(query, Store.store_id, filters['store_id'])
            if filters.get('sku'):
                query = _apply_text_filter(query, Product.sku, filters['sku'])
            if filters.get('product_name'):
                query = _apply_text_filter(query, Product.product_name, filters['product_name'])
            if filters.get('country'):
                query = _apply_text_filter(query, Store.country, filters['country'])
            
            # Price range filters
            if filters.get('price_min'):
                query = query.filter(PricingRecord.price >= _to_decimal(filters['price_min']))
            if filters.get('price_max'):
                query = query.filter(PricingRecord.price <= _to_decimal(filters['price_max']))
            
            # Date range filters
            if filters.get('date_from'):
                query = query.filter(PricingRecord.price_date >= filters['date_from'])
            if filters.get('date_to'):
                query = query.filter(PricingRecord.price_date <= filters['date_to'])
        
        # Order by date descending and paginate
        query = query.order_by(PricingRecord.price_date.desc())
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return {
            'items': [PricingService._format_record(item) for item in paginated.items],
            'total': paginated.total,
            'pages': paginated.pages,
            'current_page': page,
            'per_page': per_page
        }
    
    @staticmethod
    def get_pricing_record(record_id):
        """Get a single pricing record with eager loading"""
        record = PricingRecord.query.options(
            selectinload(PricingRecord.store),
            selectinload(PricingRecord.product)
        ).filter_by(id=record_id).first()
        
        return PricingService._format_record(record) if record else None
    
    @staticmethod
    def update_pricing_record(record_id, data, updated_by='system'):
        """Update pricing record"""
        record = PricingRecord.query.get(record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")
        
        if 'price' in data:
            record.price = _to_decimal(data['price'])
            record.updated_by = updated_by
        
        db.session.commit()
        return PricingService._format_record(record)
    
    @staticmethod
    def delete_pricing_record(record_id, deleted_by='system'):
        """Delete pricing record"""
        record = PricingRecord.query.get(record_id)
        if not record:
            raise ValueError(f"Record {record_id} not found")
        
        db.session.delete(record)
        db.session.commit()
    
    @staticmethod
    def _format_record(record):
        """Format a pricing record for API response"""
        if not record:
            return None
        
        return {
            'id': record.id,
            'store_id': record.store.store_id,
            'store_name': record.store.store_name,
            'country': record.store.country,
            'sku': record.product.sku,
            'product_name': record.product.product_name,
            'price': float(record.price),
            'currency': record.currency,
            'date': record.price_date.isoformat(),
            'updated_at': record.updated_at.isoformat(),
            'updated_by': record.updated_by,
            'source_file': record.source_file
        }


class ImportService:
    """Service for handling CSV imports"""
    
    @staticmethod
    def import_pricing_records(dataframe, source_file):
        """
        Import pricing records from DataFrame using ATOMIC transaction
        - Checks for ALL duplicates FIRST before importing anything
        - If ANY duplicates found: rejects entire file (all or nothing)
        - If no duplicates: imports all records
        
        Returns: (success_count, error_list, summary_dict)
        """
        duplicate_details = []
        duplicates_found = 0
        
        # FIRST PASS: Check for ALL duplicates (all or nothing concept)
        records_in_file = {}  # Track records in current file
        
        for idx, row in dataframe.iterrows():
            try:
                store_id = str(row['store id'])
                sku = str(row['sku'])
                price_date = row['date'].date()
                
                # Create a unique key for this record
                record_key = (store_id, sku, str(price_date))
                
                # Check if this exact record exists in file (duplicate within file)
                if record_key in records_in_file:
                    duplicates_found += 1
                    detail = f"Line {idx + 2}: Duplicate in file (Store: {store_id}, SKU: {sku}, Date: {price_date})"
                    duplicate_details.append(detail)
                    continue
                
                # Check if this record already exists in database
                store = Store.query.filter_by(store_id=store_id).first()
                if store:
                    product = Product.query.filter_by(sku=sku).first()
                    if product:
                        existing = PricingRecord.query.filter_by(
                            store_id=store.id,
                            product_id=product.id,
                            price_date=price_date
                        ).first()
                        if existing:
                            duplicates_found += 1
                            detail = f"Line {idx + 2}: Record already exists in database (Store: {store_id}, SKU: {sku}, Date: {price_date})"
                            duplicate_details.append(detail)
                            continue
                
                records_in_file[record_key] = idx + 2
                
            except Exception as e:
                duplicates_found += 1
                duplicate_details.append(f"Row {idx + 2}: {str(e)}")
        
        # If ANY duplicates found: REJECT entire file (atomic transaction)
        if duplicates_found > 0:
            error_msg = f"Upload rejected: {duplicates_found} duplicate record(s) found. All records must be unique (all or nothing rule)."
            all_errors = [error_msg]
            all_errors.extend(duplicate_details)
            
            return 0, all_errors, {
                'duplicates_skipped': duplicates_found,
                'duplicate_details': duplicate_details
            }
        
        # SECOND PASS: Import all records (no duplicates found)
        success_count = 0
        errors = []
        store_cache = {}    # Cache stores to avoid duplicate queries
        product_cache = {}  # Cache products to avoid duplicate queries
        
        # Import all records since we verified no duplicates exist
        for idx, row in dataframe.iterrows():
                
            try:
                # Get or create store (with caching)
                store_id = str(row['store id'])
                if store_id not in store_cache:
                    store = Store.query.filter_by(store_id=store_id).first()
                    if not store:
                        store = Store(
                            store_id=store_id,
                            store_name=store_id,
                            country=row.get('country', 'Unknown')
                        )
                        db.session.add(store)
                        db.session.flush()
                    store_cache[store_id] = store
                else:
                    store = store_cache[store_id]
                
                # Get or create product (with caching)
                sku = str(row['sku'])
                if sku not in product_cache:
                    product = Product.query.filter_by(sku=sku).first()
                    if not product:
                        product = Product(
                            sku=sku,
                            product_name=str(row['product name'])
                        )
                        db.session.add(product)
                        db.session.flush()
                    product_cache[sku] = product
                else:
                    product = product_cache[sku]
                
                # Create new pricing record
                price_date = row['date'].date()
                pricing_record = PricingRecord(
                    store_id=store.id,
                    product_id=product.id,
                    price=_to_decimal(row['price']),
                    price_date=price_date,
                    source_file=source_file
                )
                db.session.add(pricing_record)
                success_count += 1
                
            except (KeyError, ValueError, TypeError) as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
            except Exception as e:
                errors.append(f"Row {idx + 2}: Database error - {str(e)}")
        # Commit all changes at once
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return 0, [f"Database error: {str(e)}"] + errors, {
                'duplicates_skipped': 0,
                'duplicate_details': []
            }
        
        # No duplicates found (all or nothing rule)
        summary = {
            'duplicates_skipped': 0,
            'duplicate_details': []
        }
        
        return success_count, errors, summary
