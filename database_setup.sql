-- consultation_system データベースの初期化
USE consultation_system;

-- テナントテーブル
CREATE TABLE IF NOT EXISTS tenant (
    tenant_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_tenant_domain (domain),
    INDEX idx_tenant_active (is_active)
);

-- 業界カテゴリテーブル
CREATE TABLE IF NOT EXISTS industry_category (
    category_id VARCHAR(255) PRIMARY KEY,
    category_code VARCHAR(100) NOT NULL UNIQUE,
    category_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category_code (category_code),
    INDEX idx_category_active (is_active),
    INDEX idx_category_sort (sort_order)
);

-- アルコール種別テーブル
CREATE TABLE IF NOT EXISTS alcohol_type (
    type_id VARCHAR(255) PRIMARY KEY,
    type_code VARCHAR(100) NOT NULL UNIQUE,
    type_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    sort_order INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_type_code (type_code),
    INDEX idx_type_active (is_active),
    INDEX idx_type_sort (sort_order)
);

-- ユーザーテーブル
CREATE TABLE IF NOT EXISTS user (
    user_id VARCHAR(255) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    industry_category_id VARCHAR(255),
    alcohol_type_id VARCHAR(255),
    email VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    department VARCHAR(255),
    role VARCHAR(100),
    expertise_area VARCHAR(255),
    contact_email VARCHAR(255),
    contact_teams VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (industry_category_id) REFERENCES industry_category(category_id) ON DELETE SET NULL,
    FOREIGN KEY (alcohol_type_id) REFERENCES alcohol_type(type_id) ON DELETE SET NULL,
    UNIQUE KEY unique_email_tenant (email, tenant_id),
    INDEX idx_user_tenant (tenant_id),
    INDEX idx_user_email (email),
    INDEX idx_user_active (is_active)
);

-- 相談テーブル
CREATE TABLE IF NOT EXISTS consultation (
    consultation_id VARCHAR(255) PRIMARY KEY,
    tenant_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    industry_category_id VARCHAR(255),
    alcohol_type_id VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    summary_title VARCHAR(500),
    initial_content TEXT NOT NULL,
    information_sufficiency_level INT DEFAULT 0,
    key_issues JSON,
    suggested_questions JSON,
    relevant_regulations JSON,
    action_items JSON,
    detected_terms JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (tenant_id) REFERENCES tenant(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(user_id) ON DELETE CASCADE,
    FOREIGN KEY (industry_category_id) REFERENCES industry_category(category_id) ON DELETE SET NULL,
    FOREIGN KEY (alcohol_type_id) REFERENCES alcohol_type(type_id) ON DELETE SET NULL,
    INDEX idx_consultation_tenant (tenant_id),
    INDEX idx_consultation_user (user_id),
    INDEX idx_consultation_created (created_at),
    FULLTEXT idx_consultation_content (title, initial_content)
);

-- 初期データ挿入
-- テナントデータ
INSERT INTO tenant (tenant_id, name, domain) VALUES
('tenant_001', 'デモテナント', 'demo.omukoro.local'),
('tenant_002', 'テストテナント', 'test.omukoro.local')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- 業界カテゴリデータ
INSERT INTO industry_category (category_id, category_code, category_name, description, is_default, sort_order) VALUES
('cat_001', 'FOOD', '食品製造業', '食品の製造・加工業', TRUE, 1),
('cat_002', 'BEVERAGE', '飲料製造業', '飲料の製造業', FALSE, 2),
('cat_003', 'RETAIL', '小売業', '小売販売業', FALSE, 3),
('cat_004', 'RESTAURANT', '飲食業', '飲食店業', FALSE, 4)
ON DUPLICATE KEY UPDATE category_name = VALUES(category_name);

-- アルコール種別データ
INSERT INTO alcohol_type (type_id, type_code, type_name, description, is_default, sort_order) VALUES
('alc_001', 'BEER', 'ビール', 'ビール類', TRUE, 1),
('alc_002', 'SAKE', '日本酒', '清酒', FALSE, 2),
('alc_003', 'WINE', 'ワイン', 'ワイン', FALSE, 3),
('alc_004', 'SPIRITS', '蒸留酒', '蒸留酒類', FALSE, 4),
('alc_005', 'SHOCHU', '焼酎', '焼酎', FALSE, 5)
ON DUPLICATE KEY UPDATE type_name = VALUES(type_name);

-- テストユーザーデータ
INSERT INTO user (user_id, tenant_id, industry_category_id, alcohol_type_id, email, password, name, department, role) VALUES
('user_001', 'tenant_001', 'cat_001', 'alc_001', 'test@demo.local', 'password123', '山田太郎', '法務部', 'manager'),
('user_002', 'tenant_001', 'cat_002', 'alc_002', 'test2@demo.local', 'password123', '佐藤花子', '営業部', 'staff'),
('user_003', 'tenant_002', 'cat_003', 'alc_003', 'test@test.local', 'password123', '田中次郎', '企画部', 'manager')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- テスト相談データ
INSERT INTO consultation (
    consultation_id, tenant_id, user_id, industry_category_id, alcohol_type_id, 
    title, initial_content, information_sufficiency_level,
    key_issues, suggested_questions, action_items
) VALUES
(
    'cons_001', 'tenant_001', 'user_001', 'cat_001', 'alc_001',
    'ビール製造における酒税法の適用について', 
    '弊社ではビール製造を検討しており、酒税法の適用範囲や必要な手続きについて相談したいと思います。特に製造免許の取得手続きと税率について詳しく知りたいです。',
    3,
    '["製造免許取得", "税率計算", "申告手続き"]',
    '["製造免許の申請に必要な書類は何ですか？", "ビールの税率はどのように計算されますか？"]',
    '["製造免許申請書の準備", "税務署への事前相談", "製造設備の準備"]'
),
(
    'cons_002', 'tenant_001', 'user_002', 'cat_002', 'alc_002',
    '日本酒の輸出に関する酒税法上の取り扱い',
    '日本酒を海外に輸出する際の酒税法上の手続きや優遇措置について教えてください。輸出免税の適用条件や必要な書類について具体的に知りたいです。',
    4,
    '["輸出免税", "必要書類", "手続き期間"]',
    '["輸出免税の適用条件は？", "輸出証明書の取得方法は？"]',
    '["輸出業者の選定", "輸出証明書の申請", "税務署への届出"]'
),
(
    'cons_003', 'tenant_002', 'user_003', 'alc_003',
    'ワイン小売業での酒類販売業免許について',
    'ワインの小売販売を開始したいのですが、酒類販売業免許の取得について相談です。一般酒類小売業免許と通信販売酒類小売業免許の違いや申請方法を教えてください。',
    2,
    '["販売業免許", "通信販売", "申請要件"]',
    '["一般酒類小売業免許の申請要件は？", "通信販売での制限事項は？"]',
    '["申請書類の準備", "営業所の準備", "人的要件の確認"]'
)
ON DUPLICATE KEY UPDATE title = VALUES(title);

SELECT 'Database setup completed!' as status;
SELECT COUNT(*) as tenant_count FROM tenant;
SELECT COUNT(*) as category_count FROM industry_category;
SELECT COUNT(*) as alcohol_type_count FROM alcohol_type;
SELECT COUNT(*) as user_count FROM user;
SELECT COUNT(*) as consultation_count FROM consultation;