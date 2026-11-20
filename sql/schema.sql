-- Olist database schema


CREATE DATABASE IF NOT EXISTS olist_db
CHARACTER SET utf8mb4
COLLATE utf8mb4_0900_ai_ci;

USE olist_db;

-- =========================================================
-- 1. CATEGORY TRANSLATION
-- =========================================================

CREATE TABLE IF NOT EXISTS category_translation (
    product_category_name VARCHAR(100) NOT NULL,
    product_category_name_english VARCHAR(100) NOT NULL,
    PRIMARY KEY (product_category_name)
) ENGINE=InnoDB;

-- =========================================================
-- 2. CUSTOMERS
-- =========================================================

CREATE TABLE IF NOT EXISTS customers (
    customer_id VARCHAR(32) NOT NULL,
    customer_unique_id VARCHAR(32) NOT NULL,
    customer_zip_code_prefix INT NOT NULL,
    customer_city VARCHAR(100) NOT NULL,
    customer_state CHAR(2) NOT NULL,
    PRIMARY KEY (customer_id),
    INDEX idx_customer_unique (customer_unique_id)
) ENGINE=InnoDB;

-- =========================================================
-- 3. GEOLOCATION
-- =========================================================

CREATE TABLE IF NOT EXISTS geolocation (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    geolocation_zip_code_prefix INT NOT NULL,
    geolocation_lat DECIMAL(10,7) NOT NULL,
    geolocation_lng DECIMAL(10,7) NOT NULL,
    geolocation_city VARCHAR(100) NOT NULL,
    geolocation_state CHAR(2) NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_geo_zip (geolocation_zip_code_prefix)
) ENGINE=InnoDB;

-- =========================================================
-- 4. SELLERS
-- =========================================================

CREATE TABLE IF NOT EXISTS sellers (
    seller_id VARCHAR(32) NOT NULL,
    seller_zip_code_prefix INT NOT NULL,
    seller_city VARCHAR(100) NOT NULL,
    seller_state CHAR(2) NOT NULL,
    PRIMARY KEY (seller_id)
) ENGINE=InnoDB;

-- =========================================================
-- 5. PRODUCTS
-- =========================================================

CREATE TABLE IF NOT EXISTS products (
    product_id VARCHAR(32) NOT NULL,
    product_category_name VARCHAR(100) NOT NULL,
    product_name_lenght DECIMAL(10,2) NOT NULL,
    product_description_lenght DECIMAL(10,2) NOT NULL,
    product_photos_qty DECIMAL(10,2) NOT NULL,
    product_weight_g DECIMAL(10,2) NOT NULL,
    product_length_cm DECIMAL(10,2) NOT NULL,
    product_height_cm DECIMAL(10,2) NOT NULL,
    product_width_cm DECIMAL(10,2) NOT NULL,
    PRIMARY KEY (product_id),
    INDEX idx_product_category (product_category_name),
    CONSTRAINT fk_products_category
        FOREIGN KEY (product_category_name)
        REFERENCES category_translation (product_category_name)
) ENGINE=InnoDB;

-- =========================================================
-- 6. ORDERS
-- =========================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(32) NOT NULL,
    customer_id VARCHAR(32) NOT NULL,
    order_status VARCHAR(30) NOT NULL,
    order_purchase_timestamp DATETIME NOT NULL,
    order_approved_at DATETIME NULL,
    order_delivered_carrier_date DATETIME NULL,
    order_delivered_customer_date DATETIME NULL,
    order_estimated_delivery_date DATETIME NOT NULL,
    PRIMARY KEY (order_id),
    INDEX idx_orders_customer (customer_id),
    CONSTRAINT fk_orders_customers
        FOREIGN KEY (customer_id)
        REFERENCES customers (customer_id)
) ENGINE=InnoDB;

-- =========================================================
-- 7. ORDER ITEMS
-- =========================================================

CREATE TABLE IF NOT EXISTS order_items (
    order_id VARCHAR(32) NOT NULL,
    order_item_id INT NOT NULL,
    product_id VARCHAR(32) NOT NULL,
    seller_id VARCHAR(32) NOT NULL,
    shipping_limit_date DATETIME NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    freight_value DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id),
    INDEX idx_items_product (product_id),
    INDEX idx_items_seller (seller_id),
    CONSTRAINT fk_items_orders
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id),
    CONSTRAINT fk_items_products
        FOREIGN KEY (product_id)
        REFERENCES products (product_id),
    CONSTRAINT fk_items_sellers
        FOREIGN KEY (seller_id)
        REFERENCES sellers (seller_id)
) ENGINE=InnoDB;

-- =========================================================
-- 8. ORDER PAYMENTS
-- =========================================================

CREATE TABLE IF NOT EXISTS order_payments (
    order_id VARCHAR(32) NOT NULL,
    payment_sequential INT NOT NULL,
    payment_type VARCHAR(30) NOT NULL,
    payment_installments INT NOT NULL,
    payment_value DECIMAL(12,2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_orders
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id)
) ENGINE=InnoDB;

-- =========================================================
-- 9. ORDER REVIEWS
-- =========================================================

CREATE TABLE IF NOT EXISTS order_reviews (
    review_id VARCHAR(32) NOT NULL,
    order_id VARCHAR(32) NOT NULL,
    review_score INT NOT NULL,
    review_comment_title TEXT NULL,
    review_comment_message TEXT NULL,
    review_creation_date DATETIME NOT NULL,
    review_answer_timestamp DATETIME NOT NULL,
    PRIMARY KEY (review_id, order_id),
    INDEX idx_reviews_order (order_id),
    CONSTRAINT fk_reviews_orders
        FOREIGN KEY (order_id)
        REFERENCES orders (order_id)
) ENGINE=InnoDB;
