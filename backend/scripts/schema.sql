CREATE TABLE users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(120),
    role VARCHAR(8) NOT NULL DEFAULT 'CUSTOMER',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX ix_users_email ON users (email);

CREATE TABLE refresh_tokens (
    id VARCHAR(36) PRIMARY KEY,
    jti VARCHAR(64) NOT NULL UNIQUE,
    user_id VARCHAR(36) NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME,
    created_at DATETIME NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX ix_refresh_tokens_jti ON refresh_tokens (jti);
CREATE INDEX ix_refresh_tokens_user_id ON refresh_tokens (user_id);

CREATE TABLE products (
    id VARCHAR(36) PRIMARY KEY,
    sku VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    description TEXT,
    price NUMERIC(12, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX ix_products_sku ON products (sku);
CREATE INDEX ix_products_name ON products (name);

CREATE TABLE sales (
    id VARCHAR(36) PRIMARY KEY,
    customer_id VARCHAR(36) NOT NULL,
    status VARCHAR(9) NOT NULL DEFAULT 'PENDING',
    subtotal NUMERIC(12, 2) NOT NULL,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12, 2) NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES users (id)
);

CREATE INDEX ix_sales_customer_id ON sales (customer_id);

CREATE TABLE sale_items (
    id VARCHAR(36) PRIMARY KEY,
    sale_id VARCHAR(36) NOT NULL,
    product_id VARCHAR(36) NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    line_total NUMERIC(12, 2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales (id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products (id)
);

CREATE INDEX ix_sale_items_sale_id ON sale_items (sale_id);
CREATE INDEX ix_sale_items_product_id ON sale_items (product_id);

