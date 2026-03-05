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