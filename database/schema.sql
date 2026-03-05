-- PriceLedger Database Schema (PostgreSQL)
-- This script creates all tables and indexes for the pricing ledger system

-- Stores Table
CREATE TABLE IF NOT EXISTS stores (
    id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(20) UNIQUE NOT NULL,
    store_name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    region VARCHAR(100),
    city VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for stores table
CREATE INDEX IF NOT EXISTS idx_store_id ON stores(store_id);
CREATE INDEX IF NOT EXISTS idx_country ON stores(country);
CREATE INDEX IF NOT EXISTS idx_is_active ON stores(is_active);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
    id VARCHAR(50) PRIMARY KEY,
    sku VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

-- Create indexes for products table
CREATE INDEX IF NOT EXISTS idx_sku ON products(sku);
CREATE INDEX IF NOT EXISTS idx_product_is_active ON products(is_active);

-- Pricing Records Table
CREATE TABLE IF NOT EXISTS pricing_records (
    id VARCHAR(50) PRIMARY KEY,
    store_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(50) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    price_date DATE NOT NULL,
    source_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    FOREIGN KEY (store_id) REFERENCES stores(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    CONSTRAINT uq_store_product_date UNIQUE (store_id, product_id, price_date)
);

-- Create indexes for pricing_records table
CREATE INDEX IF NOT EXISTS idx_pricing_store_id ON pricing_records(store_id);
CREATE INDEX IF NOT EXISTS idx_pricing_product_id ON pricing_records(product_id);
CREATE INDEX IF NOT EXISTS idx_pricing_date ON pricing_records(price_date);
CREATE INDEX IF NOT EXISTS idx_store_product_date ON pricing_records(store_id, product_id, price_date);
CREATE INDEX IF NOT EXISTS idx_pricing_created_at ON pricing_records(created_at);

-- Create additional performance indexes
CREATE INDEX IF NOT EXISTS idx_pricing_records_date_range ON pricing_records(price_date DESC, store_id, product_id);
-- File Uploads Table
CREATE TABLE IF NOT EXISTS file_uploads (
    id VARCHAR(50) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    upload_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'Processing',
    errors TEXT,
    records_imported INTEGER DEFAULT 0,
    total_records INTEGER DEFAULT 0,
    invalid_records INTEGER DEFAULT 0,
    duplicates_skipped INTEGER DEFAULT 0
);

-- Create indexes for file_uploads table
CREATE INDEX IF NOT EXISTS idx_file_upload_time ON file_uploads(upload_time DESC);
CREATE INDEX IF NOT EXISTS idx_file_upload_status ON file_uploads(status);