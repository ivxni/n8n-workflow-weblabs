-- Weblabs Lead Generator - Datenbank Schema
-- Erstellt automatisch bei Docker-Start

-- Weblabs Datenbank erstellen
CREATE DATABASE weblabs;

-- Zur Weblabs Datenbank wechseln
\c weblabs;

-- Leads Tabelle
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    
    -- Unternehmensdaten
    company_name VARCHAR(255) NOT NULL,
    industry VARCHAR(100),
    address TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(20),
    phone VARCHAR(50),
    email VARCHAR(255),
    
    -- Website-Analyse
    current_website VARCHAR(500),
    has_website BOOLEAN DEFAULT FALSE,
    website_quality_score INTEGER DEFAULT 0, -- 0-100
    website_issues TEXT[], -- Array von Problemen
    
    -- Google/Maps Daten
    google_rating DECIMAL(2,1),
    google_reviews_count INTEGER,
    google_place_id VARCHAR(255),
    
    -- AI-generierte Inhalte
    generated_email_subject TEXT,
    generated_email_body TEXT,
    generated_website_concept TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'new', -- new, reviewed, approved, sent, responded, rejected
    priority INTEGER DEFAULT 0, -- Höher = wichtiger
    
    -- Tracking
    email_sent_at TIMESTAMP,
    email_opened_at TIMESTAMP,
    response_received_at TIMESTAMP,
    
    -- Metadaten
    source VARCHAR(100), -- google_maps, yellow_pages, manual, etc.
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index für schnelle Suche
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_city ON leads(city);
CREATE INDEX idx_leads_created_at ON leads(created_at DESC);

-- Settings Tabelle
CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(100) PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Default settings (override via .env or dashboard)
INSERT INTO settings (key, value) VALUES 
    ('sender_name', 'Your Name'),
    ('sender_email', 'contact@example.com'),
    ('website_url', 'https://example.com'),
    ('target_radius_km', '50'),
    ('target_city', 'Stuttgart'),
    ('email_signature', 'Mit freundlichen Grüßen,\nYour Name\nYourCompany\nexample.com')
ON CONFLICT (key) DO NOTHING;

-- Email Templates Tabelle
CREATE TABLE IF NOT EXISTS email_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    industry VARCHAR(100), -- Optional: Branchenspezifisch
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Standard Email Template
INSERT INTO email_templates (name, subject_template, body_template, industry) VALUES (
    'Standard - Persönlich',
    'Ihre Online-Präsenz für {company_name}',
    'Guten Tag,

ich bin auf {company_name} aufmerksam geworden und war beeindruckt von {personalized_compliment}.

Als Webentwickler aus Stuttgart habe ich mich auf moderne, individuelle Webseiten spezialisiert, die nicht nur gut aussehen, sondern auch Kunden bringen.

{website_analysis}

Ich würde mich freuen, Ihnen unverbindlich zu zeigen, wie eine zeitgemäße Webpräsenz für {company_name} aussehen könnte.

Haben Sie diese Woche 15 Minuten Zeit für ein kurzes Telefonat?

Mit freundlichen Grüßen,
Can

P.S. Schauen Sie gerne auf weblabs.io vorbei, um einige meiner bisherigen Projekte zu sehen.',
    NULL
);
