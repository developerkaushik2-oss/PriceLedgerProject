from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class Store(db.Model):
    """Store model - represents retail store locations"""
    __tablename__ = 'stores'
    
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    store_name = db.Column(db.String(255), nullable=False)
    country = db.Column(db.String(100), nullable=False, index=True)
    region = db.Column(db.String(100), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    pricing_records = db.relationship('PricingRecord', backref='store', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Store {self.store_id}>"


class Product(db.Model):
    """Product model - represents SKUs/products"""
    __tablename__ = 'products'
    
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    sku = db.Column(db.String(50), unique=True, nullable=False, index=True)
    product_name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True, index=True)
    
    # Relationships
    pricing_records = db.relationship('PricingRecord', backref='product', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f"<Product {self.sku}>"


class PricingRecord(db.Model):
    """Pricing Record model - represents price of a product at a specific store"""
    __tablename__ = 'pricing_records'
    
    id = db.Column(db.String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    store_id = db.Column(db.String(50), db.ForeignKey('stores.id'), nullable=False, index=True)
    product_id = db.Column(db.String(50), db.ForeignKey('products.id'), nullable=False, index=True)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD', nullable=False)
    price_date = db.Column(db.Date, nullable=False, index=True)
    source_file = db.Column(db.String(255), nullable=True)  # Track which CSV file this came from
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(255), nullable=True)  # Track who updated
    
    # Composite index for efficient querying
    __table_args__ = (
        db.Index('idx_store_product_date', 'store_id', 'product_id', 'price_date'),
        db.UniqueConstraint('store_id', 'product_id', 'price_date', name='uq_store_product_date'),
    )
    
    def __repr__(self):
        return f"<PricingRecord {self.id}>"


