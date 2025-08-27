-- Initialize PostgreSQL database for Iranian Price Intelligence Platform

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    api_tier VARCHAR(50) DEFAULT 'basic',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    api_calls_today INTEGER DEFAULT 0,
    total_api_calls INTEGER DEFAULT 0
);

-- Create price_alerts table
CREATE TABLE IF NOT EXISTS price_alerts (
    id SERIAL PRIMARY KEY,
    alert_id VARCHAR(50) UNIQUE NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    product_title VARCHAR(500),
    alert_type VARCHAR(50) NOT NULL,
    threshold DECIMAL(10,2),
    vendor VARCHAR(100),
    notification_method VARCHAR(50) DEFAULT 'email',
    webhook_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_count INTEGER DEFAULT 0,
    last_triggered TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_user_id ON price_alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_product_id ON price_alerts(product_id);

-- Insert default admin user (password: admin123)
INSERT INTO users (user_id, email, password_hash, company, api_tier, is_active)
VALUES (
    'admin_user_001',
    'admin@iranianprice.local',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LeX8B.XjDCwF8OhS2',
    'Iranian Price Intelligence',
    'enterprise',
    true
) ON CONFLICT (email) DO NOTHING;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO price_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO price_admin;
