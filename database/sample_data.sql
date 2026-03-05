-- Sample data for testing PriceLedger application
-- This file contains sample stores, products, and pricing records

-- Insert sample stores across multiple countries
INSERT INTO stores (id, store_id, store_name, country, region, city, is_active) VALUES
('store-001', 'S0001', 'Manhattan Store', 'USA', 'New York', 'New York', TRUE),
('store-002', 'S0002', 'Los Angeles Store', 'USA', 'California', 'Los Angeles', TRUE),
('store-003', 'S0003', 'Chicago Store', 'USA', 'Illinois', 'Chicago', TRUE),
('store-004', 'S0004', 'London Store', 'UK', 'England', 'London', TRUE),
('store-005', 'S0005', 'Manchester Store', 'UK', 'England', 'Manchester', TRUE),
('store-006', 'S0006', 'Paris Store', 'France', 'Île-de-France', 'Paris', TRUE),
('store-007', 'S0007', 'Tokyo Store', 'Japan', 'Tokyo', 'Tokyo', TRUE),
('store-008', 'S0008', 'Sydney Store', 'Australia', 'New South Wales', 'Sydney', TRUE),
('store-009', 'S0009', 'Toronto Store', 'Canada', 'Ontario', 'Toronto', TRUE),
('store-010', 'S0010', 'Dubai Store', 'UAE', 'Dubai', 'Dubai', TRUE);

-- Insert sample products
INSERT INTO products (id, sku, product_name, category, is_active) VALUES
('prod-001', 'SKU-10001', 'Organic Apple - Gala', 'Fruits', TRUE),
('prod-002', 'SKU-10002', 'Fresh Milk - 2L', 'Dairy', TRUE),
('prod-003', 'SKU-10003', 'Whole Wheat Bread', 'Bakery', TRUE),
('prod-004', 'SKU-10004', 'Cheddar Cheese - 500g', 'Dairy', TRUE),
('prod-005', 'SKU-10005', 'Orange Juice - 1.5L', 'Beverages', TRUE),
('prod-006', 'SKU-10006', 'Chicken Breast - 1kg', 'Meat', TRUE),
('prod-007', 'SKU-10007', 'Tomato Sauce - 500ml', 'Condiments', TRUE),
('prod-008', 'SKU-10008', 'Pasta - Spaghetti 500g', 'Grains', TRUE),
('prod-009', 'SKU-10009', 'Olive Oil - 750ml', 'Oils', TRUE),
('prod-010', 'SKU-10010', 'Yogurt - Greek 500g', 'Dairy', TRUE);

-- Insert sample pricing records
INSERT INTO pricing_records (id, store_id, product_id, price, currency, price_date, source_file, updated_by) VALUES
('price-001', 'store-001', 'prod-001', 2.99, 'USD', '2026-02-25', 'sample_import.csv', 'admin'),
('price-002', 'store-001', 'prod-002', 3.49, 'USD', '2026-02-25', 'sample_import.csv', 'admin'),
('price-003', 'store-001', 'prod-003', 2.49, 'USD', '2026-02-25', 'sample_import.csv', 'admin'),
('price-004', 'store-002', 'prod-001', 3.19, 'USD', '2026-02-25', 'sample_import.csv', 'admin'),
('price-005', 'store-002', 'prod-002', 3.29, 'USD', '2026-02-25', 'sample_import.csv', 'admin'),
('price-006', 'store-004', 'prod-001', 1.85, 'GBP', '2026-02-25', 'sample_import.csv', 'admin'),
('price-007', 'store-004', 'prod-002', 1.95, 'GBP', '2026-02-25', 'sample_import.csv', 'admin'),
('price-008', 'store-006', 'prod-001', 1.99, 'EUR', '2026-02-25', 'sample_import.csv', 'admin'),
('price-009', 'store-007', 'prod-002', 4.50, 'JPY', '2026-02-25', 'sample_import.csv', 'admin'),
('price-010', 'store-008', 'prod-001', 4.20, 'AUD', '2026-02-25', 'sample_import.csv', 'admin');

-- Insert sample audit logs
INSERT INTO audit_logs (id, pricing_record_id, action, old_value, new_value, changed_by, change_reason) VALUES
('audit-001', 'price-001', 'CREATE', NULL, 2.99, 'system', 'Initial import'),
('audit-002', 'price-002', 'CREATE', NULL, 3.49, 'system', 'Initial import'),
('audit-003', 'price-001', 'UPDATE', 2.99, 3.05, 'admin_user', 'Price adjustment - market change');
