-- ============================================================================
-- FINANCIAL AI RESEARCH PLATFORM - DATABASE ARCHITECTURE SCHEMA DDL
-- Target: PostgreSQL 13+ (with pgvector extension)
-- Author: Antigravity AI Architect
-- Description: Production-grade database schema for analyzing stocks, prices,
--              company profiles, analyst consensus, filings, news sentiment,
--              earnings call transcripts, research run costs, alerts,
--              scheduled jobs, report sections, and dynamic vector embeddings.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. EXTENSIONS & SYSTEM UTILITIES
-- ----------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- For fuzzy text searching (trigrams)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- For cryptographically secure operations
CREATE EXTENSION IF NOT EXISTS "vector";        -- pgvector extension for dynamic RAG embeddings

-- Setup time zone handling
SET TIME ZONE 'UTC';

-- Trigger function to automate "updated_at" timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- 2. CUSTOM TYPES & ENUMS
-- ----------------------------------------------------------------------------
CREATE TYPE period_type_enum AS ENUM ('annual', 'quarterly', 'trailing_twelve_months');
CREATE TYPE rating_type_enum AS ENUM ('strong_buy', 'buy', 'hold', 'sell', 'strong_sell');
CREATE TYPE report_status_enum AS ENUM ('draft', 'generating', 'completed', 'failed');
CREATE TYPE run_status_enum AS ENUM ('pending', 'running', 'completed', 'failed');
CREATE TYPE sentiment_label_enum AS ENUM ('positive', 'neutral', 'negative');
CREATE TYPE source_type_enum AS ENUM ('news_article', 'earnings_transcript', 'research_report');
CREATE TYPE event_impact_enum AS ENUM ('high', 'medium', 'low');
CREATE TYPE alert_type_enum AS ENUM ('price_above', 'price_below', 'sentiment_above', 'sentiment_below', 'new_research_report');
CREATE TYPE report_section_type_enum AS ENUM (
    'EXECUTIVE_SUMMARY', 
    'BULL_CASE', 
    'BEAR_CASE', 
    'RISKS', 
    'CATALYSTS', 
    'VALUATION', 
    'SENTIMENT_ANALYSIS', 
    'INVESTMENT_THESIS'
);

-- ----------------------------------------------------------------------------
-- 3. CORE PLATFORM TABLES
-- ----------------------------------------------------------------------------

-- Users (Financial analysts, administrators, and client readers)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Stocks (Tracked companies catalog)
CREATE TABLE stocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(50) NOT NULL, -- e.g. "NASDAQ", "NYSE", "LSE"
    sector VARCHAR(100),
    industry VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Company Profiles (Detailed metadata fetched from Yahoo Finance or other providers)
CREATE TABLE company_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL UNIQUE REFERENCES stocks(id) ON DELETE CASCADE,
    description TEXT,
    headquarters VARCHAR(255),
    ceo VARCHAR(150),
    employees INT CONSTRAINT chk_employees_positive CHECK (employees >= 0),
    website VARCHAR(255),
    founded_year INT CONSTRAINT chk_founded_year CHECK (founded_year >= 1600 AND founded_year <= EXTRACT(YEAR FROM CURRENT_DATE)),
    market_cap NUMERIC(20, 2) CONSTRAINT chk_market_cap CHECK (market_cap >= 0),
    shares_outstanding NUMERIC(20, 2) CONSTRAINT chk_shares_outstanding CHECK (shares_outstanding >= 0),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Analyst Consensus (Consensus recommendations and average targets)
CREATE TABLE analyst_consensus (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL UNIQUE REFERENCES stocks(id) ON DELETE CASCADE,
    buy_count INT NOT NULL DEFAULT 0 CONSTRAINT chk_buy_count CHECK (buy_count >= 0),
    hold_count INT NOT NULL DEFAULT 0 CONSTRAINT chk_hold_count CHECK (hold_count >= 0),
    sell_count INT NOT NULL DEFAULT 0 CONSTRAINT chk_sell_count CHECK (sell_count >= 0),
    average_target_price NUMERIC(12, 2) CONSTRAINT chk_avg_target_price CHECK (average_target_price >= 0),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Stock Prices (Time-series historical daily bars)
CREATE TABLE stock_prices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    price_date DATE NOT NULL,
    open_price NUMERIC(12, 4) NOT NULL CONSTRAINT chk_open_price CHECK (open_price >= 0),
    high_price NUMERIC(12, 4) NOT NULL CONSTRAINT chk_high_price CHECK (high_price >= 0),
    low_price NUMERIC(12, 4) NOT NULL CONSTRAINT chk_low_price CHECK (low_price >= 0),
    close_price NUMERIC(12, 4) NOT NULL CONSTRAINT chk_close_price CHECK (close_price >= 0),
    volume BIGINT NOT NULL CONSTRAINT chk_volume CHECK (volume >= 0),
    adjusted_close NUMERIC(12, 4) NOT NULL CONSTRAINT chk_adj_close CHECK (adjusted_close >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_stock_price_date UNIQUE (stock_id, price_date),
    CONSTRAINT chk_price_extremes CHECK (high_price >= low_price AND high_price >= open_price AND high_price >= close_price)
);

-- Company Fundamentals (Structured income statement, balance sheet, and cash flow data)
CREATE TABLE company_fundamentals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    report_date DATE NOT NULL,
    period_type period_type_enum NOT NULL,
    revenue NUMERIC(18, 2),
    net_income NUMERIC(18, 2),
    eps NUMERIC(12, 4),
    ebitda NUMERIC(18, 2),
    assets NUMERIC(18, 2),
    liabilities NUMERIC(18, 2),
    cash_flow NUMERIC(18, 2),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, -- Store dynamic ratios, cash reserves, debt/equity calculations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_stock_fundamental_period UNIQUE (stock_id, report_date, period_type)
);

-- ----------------------------------------------------------------------------
-- 4. CONTENT & SEMANTIC RESEARCH SOURCES
-- ----------------------------------------------------------------------------

-- News Articles
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    source_name VARCHAR(100),
    url TEXT,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb, -- Scraper parameters, author tags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- News Article Stocks (Many-to-many relationship mapping news to multiple mentioned stocks)
CREATE TABLE news_article_stocks (
    article_id UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    PRIMARY KEY (article_id, stock_id)
);

-- Earnings Call Transcripts
CREATE TABLE earnings_transcripts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    quarter INT NOT NULL CONSTRAINT chk_transcript_quarter CHECK (quarter >= 1 AND quarter <= 4),
    year INT NOT NULL CONSTRAINT chk_transcript_year CHECK (year >= 1900 AND year <= 2100),
    publish_date DATE NOT NULL,
    raw_text TEXT NOT NULL,
    sections JSONB NOT NULL DEFAULT '[]'::jsonb, -- Parsed chat dialogues: [{"speaker": "CEO", "text": "..."}]
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_stock_transcript_period UNIQUE (stock_id, year, quarter)
);

-- ----------------------------------------------------------------------------
-- 5. RESEARCH ANALYSIS & EXECUTION RUNS
-- ----------------------------------------------------------------------------

-- Research Runs (Jobs tracking AI generation processes, configurations, and job statuses)
CREATE TABLE research_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    trigger_type VARCHAR(50) NOT NULL, -- e.g. "manual", "scheduled", "event_triggered"
    status run_status_enum NOT NULL DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    config JSONB NOT NULL DEFAULT '{}'::jsonb, -- Prompts custom variables, data window configurations
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Research Reports (The generated outputs containing AI analysis and analyst-curated metrics)
CREATE TABLE research_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    run_id UUID REFERENCES research_runs(id) ON DELETE SET NULL,
    title VARCHAR(255) NOT NULL,
    summary TEXT,
    target_price NUMERIC(12, 2) CONSTRAINT chk_target_price CHECK (target_price >= 0),
    rating rating_type_enum,
    status report_status_enum NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Research Report Sections (Detailed breakdowns instead of one large report blob)
CREATE TABLE research_report_sections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID NOT NULL REFERENCES research_reports(id) ON DELETE CASCADE,
    section_type report_section_type_enum NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_report_section UNIQUE (report_id, section_type)
);

-- Research Sources (Audit table mapping specific news/transcripts used as context for a Research Run)
CREATE TABLE research_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
    source_type source_type_enum NOT NULL,
    source_id UUID NOT NULL, -- References news_articles, earnings_transcripts, or company_fundamentals
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- ----------------------------------------------------------------------------
-- 6. SENTIMENT ANALYSIS, EVENTS, & WATCHLISTS
-- ----------------------------------------------------------------------------

-- Sentiment Data logs
CREATE TABLE sentiments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    source_type source_type_enum NOT NULL,
    source_id UUID NOT NULL, -- Links to news_articles, earnings_transcripts, or research_reports
    sentiment_score NUMERIC(4, 3) NOT NULL CONSTRAINT chk_sentiment_score CHECK (sentiment_score >= -1.000 AND sentiment_score <= 1.000),
    sentiment_label sentiment_label_enum NOT NULL,
    explanation TEXT,
    confidence_score NUMERIC(4, 3) CONSTRAINT chk_confidence_score CHECK (confidence_score >= 0.000 AND confidence_score <= 1.000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- User Watchlists
CREATE TABLE watchlists (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Watchlist items mapping
CREATE TABLE watchlist_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    CONSTRAINT uq_watchlist_stock UNIQUE (watchlist_id, stock_id)
);

-- Scheduled Jobs (Allow automated recurring research generation)
CREATE TABLE scheduled_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    job_name VARCHAR(150) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL, -- standard cron string, e.g. "0 6 * * 1-5" (6 AM weekdays)
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Alerts (User triggers for price targets, sentiments, and report changes)
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    alert_type alert_type_enum NOT NULL,
    target_value NUMERIC(12, 4) NOT NULL, -- Trigger threshold (e.g. price, sentiment threshold)
    is_triggered BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Market Catalysts and Events
CREATE TABLE market_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    stock_id UUID REFERENCES stocks(id) ON DELETE CASCADE, -- Nullable implies general macroeconomic news/events
    event_type VARCHAR(100) NOT NULL, -- e.g. "earnings_release", "dividend", "merger", "interest_rate_decision"
    event_date TIMESTAMP WITH TIME ZONE NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    impact_level event_impact_enum NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- ----------------------------------------------------------------------------
-- 7. AI UTILITY & SEMANTIC EMBEDDINGS (RAG)
-- ----------------------------------------------------------------------------

-- AI Model Token Audit usage
CREATE TABLE ai_model_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES research_runs(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    model_name VARCHAR(100) NOT NULL, -- e.g. "gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro"
    prompt_tokens INT NOT NULL DEFAULT 0 CONSTRAINT chk_prompt_tokens CHECK (prompt_tokens >= 0),
    completion_tokens INT NOT NULL DEFAULT 0 CONSTRAINT chk_comp_tokens CHECK (completion_tokens >= 0),
    cost NUMERIC(10, 6) NOT NULL DEFAULT 0.000000 CONSTRAINT chk_usage_cost CHECK (cost >= 0),
    action_performed VARCHAR(100) NOT NULL, -- e.g. "sentiment_analysis", "report_generation", "chunk_embedding"
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Semantic Vector Chunks (For Retrieval-Augmented Generation)
-- Dimension is intentionally UNCONSTRAINED (vector) to support dynamic models
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_type source_type_enum NOT NULL,
    source_id UUID NOT NULL, -- References news_articles, earnings_transcripts, or research_reports
    chunk_index INT NOT NULL,
    content_chunk TEXT NOT NULL,
    embedding_model VARCHAR(100) NOT NULL,     -- e.g. "text-embedding-3-small", "text-embedding-ada-002"
    embedding_dimension INT NOT NULL CONSTRAINT chk_dimension_positive CHECK (embedding_dimension > 0),
    embedding vector NOT NULL,                 -- Variable-dimension pgvector column
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- ----------------------------------------------------------------------------
-- 8. AUTOMATIC TRIGGER REGISTRATION FOR TIMESTAMP MANAGEMENT
-- ----------------------------------------------------------------------------
CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_stocks_updated_at BEFORE UPDATE ON stocks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_company_profiles_updated_at BEFORE UPDATE ON company_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_analyst_consensus_updated_at BEFORE UPDATE ON analyst_consensus FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_stock_prices_updated_at BEFORE UPDATE ON stock_prices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_company_fundamentals_updated_at BEFORE UPDATE ON company_fundamentals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_news_articles_updated_at BEFORE UPDATE ON news_articles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_earnings_transcripts_updated_at BEFORE UPDATE ON earnings_transcripts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_research_reports_updated_at BEFORE UPDATE ON research_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_watchlists_updated_at BEFORE UPDATE ON watchlists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_market_events_updated_at BEFORE UPDATE ON market_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ----------------------------------------------------------------------------
-- 9. PERFORMANCE INDEXING DESIGN
-- ----------------------------------------------------------------------------

-- A. Foreign Key Indexes (Avoids sequential scans on JOINs and cascades)
CREATE INDEX idx_company_profiles_stock ON company_profiles(stock_id);
CREATE INDEX idx_analyst_consensus_stock ON analyst_consensus(stock_id);
CREATE INDEX idx_stock_prices_stock ON stock_prices(stock_id);
CREATE INDEX idx_company_fundamentals_stock ON company_fundamentals(stock_id);
CREATE INDEX idx_news_article_stocks_stock ON news_article_stocks(stock_id);
CREATE INDEX idx_news_article_stocks_art ON news_article_stocks(article_id);
CREATE INDEX idx_earnings_transcripts_stock ON earnings_transcripts(stock_id);
CREATE INDEX idx_research_runs_user ON research_runs(user_id);
CREATE INDEX idx_research_runs_stock ON research_runs(stock_id);
CREATE INDEX idx_research_reports_user ON research_reports(user_id);
CREATE INDEX idx_research_reports_stock ON research_reports(stock_id);
CREATE INDEX idx_research_reports_run ON research_reports(run_id);
CREATE INDEX idx_research_report_sections_rep ON research_report_sections(report_id);
CREATE INDEX idx_research_sources_run ON research_sources(run_id);
CREATE INDEX idx_sentiments_stock ON sentiments(stock_id);
CREATE INDEX idx_watchlists_user ON watchlists(user_id);
CREATE INDEX idx_watchlist_items_wl ON watchlist_items(watchlist_id);
CREATE INDEX idx_watchlist_items_stock ON watchlist_items(stock_id);
CREATE INDEX idx_scheduled_jobs_user ON scheduled_jobs(user_id);
CREATE INDEX idx_scheduled_jobs_stock ON scheduled_jobs(stock_id);
CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_stock ON alerts(stock_id);
CREATE INDEX idx_market_events_stock ON market_events(stock_id);
CREATE INDEX idx_ai_model_usage_run ON ai_model_usage(run_id);
CREATE INDEX idx_ai_model_usage_user ON ai_model_usage(user_id);

-- B. Time-Series and Chronological Indexes (Optimizes query paths for charts & date filters)
CREATE INDEX idx_stock_prices_timeline ON stock_prices(stock_id, price_date DESC);
CREATE INDEX idx_company_fundamentals_timeline ON company_fundamentals(stock_id, report_date DESC);
CREATE INDEX idx_news_articles_published ON news_articles(published_at DESC);
CREATE INDEX idx_market_events_date ON market_events(event_date DESC);
CREATE INDEX idx_sentiments_created ON sentiments(created_at DESC);

-- C. Logical Source Queries (Index composite source fields for dynamic entities)
CREATE INDEX idx_sentiments_logical_source ON sentiments(source_type, source_id);
CREATE INDEX idx_embeddings_logical_source ON embeddings(source_type, source_id);
CREATE INDEX idx_research_sources_logical ON research_sources(source_type, source_id);

-- D. GIN Indexes for Semi-Structured JSONB Search
CREATE INDEX idx_company_fundamentals_metadata ON company_fundamentals USING gin (metadata);
CREATE INDEX idx_research_runs_config ON research_runs USING gin (config);
CREATE INDEX idx_earnings_transcripts_sections ON earnings_transcripts USING gin (sections);

-- E. Full-Text Search (FTS) Indexes (Speeding up keyword scans)
CREATE INDEX idx_news_articles_content_tsv ON news_articles USING gin (to_tsvector('english', content));
CREATE INDEX idx_earnings_transcripts_text_tsv ON earnings_transcripts USING gin (to_tsvector('english', raw_text));
CREATE INDEX idx_report_sections_content_tsv ON research_report_sections USING gin (to_tsvector('english', content));

-- F. Trigram Indexes for Fuzzy Auto-complete Stocks Selection
CREATE INDEX idx_stocks_ticker_trgm ON stocks USING gin (ticker gin_trgm_ops);
CREATE INDEX idx_stocks_name_trgm ON stocks USING gin (name gin_trgm_ops);

-- To keep the base schema fully flexible, no index is registered on the variable-dimension vector column.
-- In production, if using a single static model (e.g. OpenAI 1536), execute:
--   CREATE INDEX idx_embeddings_vector_hnsw ON embeddings USING hnsw (embedding vector_cosine_ops);

-- ----------------------------------------------------------------------------
-- 10. SEED DATA EXAMPLES
-- ----------------------------------------------------------------------------
BEGIN;

-- 1. Users Seed
INSERT INTO users (id, email, password_hash, first_name, last_name) VALUES
('a37dbfb2-28df-4a60-a299-906cbbf8561d', 'analyst.jane@marketmind.ai', '$2b$12$N9qo8uLOoGCu2bQ3Zq987OaXN2sL09jLp3O8s1bL07a6s7e8r6f5t', 'Jane', 'Doe');

-- 2. Stocks Seed (Apple & Tesla)
INSERT INTO stocks (id, ticker, name, exchange, sector, industry, is_active) VALUES
('b19283e1-2a13-41bb-9876-0f81d11b332d', 'AAPL', 'Apple Inc.', 'NASDAQ', 'Technology', 'Consumer Electronics', TRUE),
('c29384f2-3b24-42cc-8765-1f92e22c443e', 'TSLA', 'Tesla Inc.', 'NASDAQ', 'Consumer Cyclical', 'Auto Manufacturers', TRUE);

-- 3. Company Profiles Seed
INSERT INTO company_profiles (id, stock_id, description, headquarters, ceo, employees, website, founded_year, market_cap, shares_outstanding) VALUES
('d18273f4-4c35-43dd-ba98-2a19e22c554a', 'b19283e1-2a13-41bb-9876-0f81d11b332d', 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.', 'Cupertino, CA, USA', 'Tim Cook', 164000, 'https://www.apple.com', 1976, 3050000000000.00, 15400000000.00),
('e29384f5-5d46-44ee-ca87-3b29f33d665b', 'c29384f2-3b24-42cc-8765-1f92e22c443e', 'Tesla, Inc. designs, develops, manufactures, sells, and leases fully electric vehicles, energy generation and storage systems.', 'Austin, TX, USA', 'Elon Musk', 140000, 'https://www.tesla.com', 2003, 560000000000.00, 3180000000.00);

-- 4. Analyst Consensus Seed
INSERT INTO analyst_consensus (id, stock_id, buy_count, hold_count, sell_count, average_target_price) VALUES
('f30495e6-6e57-45ff-da98-4c30a44e776c', 'b19283e1-2a13-41bb-9876-0f81d11b332d', 28, 6, 2, 215.50),
('a41506f7-7f68-46ff-ea87-5d41b55f887d', 'c29384f2-3b24-42cc-8765-1f92e22c443e', 14, 18, 9, 210.00);

-- 5. Stock Prices Seed (AAPL and TSLA daily values)
INSERT INTO stock_prices (id, stock_id, price_date, open_price, high_price, low_price, close_price, volume, adjusted_close) VALUES
(uuid_generate_v4(), 'b19283e1-2a13-41bb-9876-0f81d11b332d', '2026-06-05', 190.2500, 192.5000, 189.7500, 191.8500, 52000000, 191.8500),
(uuid_generate_v4(), 'b19283e1-2a13-41bb-9876-0f81d11b332d', '2026-06-04', 188.5000, 190.4000, 187.9000, 189.9500, 48000000, 189.9500),
(uuid_generate_v4(), 'c29384f2-3b24-42cc-8765-1f92e22c443e', '2026-06-05', 175.0000, 178.9000, 173.2000, 177.4600, 85000000, 177.4600),
(uuid_generate_v4(), 'c29384f2-3b24-42cc-8765-1f92e22c443e', '2026-06-04', 178.1000, 180.2000, 174.5000, 175.1000, 91000000, 175.1000);

-- 6. Company Fundamentals Seed
INSERT INTO company_fundamentals (id, stock_id, report_date, period_type, revenue, net_income, eps, ebitda, assets, liabilities, cash_flow, metadata) VALUES
('10495f8a-a9bb-41ff-87a2-f8c5b5f4ea1d', 'b19283e1-2a13-41bb-9876-0f81d11b332d', '2025-09-30', 'annual', 383285000000.00, 96995000000.00, 6.1300, 125820000000.00, 352583000000.00, 290400000000.00, 110543000000.00, '{"pe_ratio": 31.3, "roe": 156.0}'),
('20596f9b-bacc-42ff-98b3-09d6c6f5fb2e', 'c29384f2-3b24-42cc-8765-1f92e22c443e', '2025-12-31', 'annual', 96773000000.00, 14997000000.00, 4.3000, 16500000000.00, 104500000000.00, 43000000000.00, 13200000000.00, '{"pe_ratio": 41.2, "roe": 24.3}');

-- 7. News Articles Seed
INSERT INTO news_articles (id, title, content, summary, source_name, url, published_at) VALUES
('30697fa2-cbdd-43ff-a9c4-1ad7d7f6fc3f', 'Apple WWDC 2026 AI Strategy Announcements', 'At the Worldwide Developers Conference, Apple debuted a suite of new Siri improvements powered by on-device and private cloud LLM integration. Analyst expectations are highly positive regarding smartphone hardware upgrade cycles.', 'Apple announced upgraded AI capabilities for iOS devices, driving positive analyst target revisions.', 'Bloomberg', 'https://bloomberg.com/news/apple-wwdc-2026', '2026-06-05 14:00:00+00'),
('40798fb3-dcee-44ff-bad5-2be8d8f7fd4a', 'Tesla Autopilot Regulatory Approvals Approaching in Europe', 'Tesla shares closed up 3% after reports emerged that EU regulators are finishing their safety assessment of the FSD beta module. A tentative green light is expected by September.', 'EU regulatory clearance for Tesla FSD looks close, triggering stock price action.', 'Reuters', 'https://reuters.com/news/tesla-fsd-eu-approval', '2026-06-05 16:30:00+00');

-- 8. News Article Stocks Linkage
INSERT INTO news_article_stocks (article_id, stock_id) VALUES
('30697fa2-cbdd-43ff-a9c4-1ad7d7f6fc3f', 'b19283e1-2a13-41bb-9876-0f81d11b332d'),
('40798fb3-dcee-44ff-bad5-2be8d8f7fd4a', 'c29384f2-3b24-42cc-8765-1f92e22c443e');

-- 9. Earnings Call Transcripts Seed
INSERT INTO earnings_transcripts (id, stock_id, quarter, year, publish_date, raw_text, sections) VALUES
('50899fc4-edff-45ff-bce6-3cf9d9f8fe5b', 'b19283e1-2a13-41bb-9876-0f81d11b332d', 1, 2026, '2026-05-01', 'CEO Tim Cook: We had a solid quarter. iPhone revenue hit records. CFO Luca Maestri: Gross margin was strong at 46.5%. Q&A session focused heavily on device-side AI implementation.', '[{"speaker": "Tim Cook", "role": "CEO", "text": "We had a solid quarter. iPhone revenue hit records."}, {"speaker": "Luca Maestri", "role": "CFO", "text": "Gross margin was strong at 46.5%."}]');

-- 10. Research Runs Seed
INSERT INTO research_runs (id, user_id, stock_id, trigger_type, status, config) VALUES
('60990fd5-feaa-46ff-cde7-4df0da09ff6c', 'a37dbfb2-28df-4a60-a299-906cbbf8561d', 'b19283e1-2a13-41bb-9876-0f81d11b332d', 'manual', 'completed', '{"include_news": true, "include_transcripts": true}');

-- 11. Research Reports Seed
INSERT INTO research_reports (id, user_id, stock_id, run_id, title, summary, target_price, rating, status) VALUES
('70aa1fe6-0fbb-47ff-dee8-5e01eb1aff7d', 'a37dbfb2-28df-4a60-a299-906cbbf8561d', 'b19283e1-2a13-41bb-9876-0f81d11b332d', '60990fd5-feaa-46ff-cde7-4df0da09ff6c', 'Apple Inc. - WWDC Catalyst and Valuation Review', 'We issue a BUY recommendation on AAPL post-WWDC. AI-driven consumer device upgrades are anticipated to accelerate replacement velocity.', 220.00, 'buy', 'completed');

-- 12. Research Report Sections Seed
INSERT INTO research_report_sections (id, report_id, section_type, content) VALUES
(uuid_generate_v4(), '70aa1fe6-0fbb-47ff-dee8-5e01eb1aff7d', 'EXECUTIVE_SUMMARY', 'We maintain our bullish stance on Apple following their WWDC developers conference. The new private LLM cloud architecture offers solid security features.'),
(uuid_generate_v4(), '70aa1fe6-0fbb-47ff-dee8-5e01eb1aff7d', 'BULL_CASE', 'A faster hardware replacement cycle where consumers buy new iPhones to access local AI capabilities.'),
(uuid_generate_v4(), '70aa1fe6-0fbb-47ff-dee8-5e01eb1aff7d', 'RISKS', 'Delayed software updates in major international markets and antitrust compliance over local model integration.');

-- 13. Research Sources Seed
INSERT INTO research_sources (id, run_id, source_type, source_id) VALUES
(uuid_generate_v4(), '60990fd5-feaa-46ff-cde7-4df0da09ff6c', 'news_article', '30697fa2-cbdd-43ff-a9c4-1ad7d7f6fc3f'),
(uuid_generate_v4(), '60990fd5-feaa-46ff-cde7-4df0da09ff6c', 'earnings_transcript', '50899fc4-edff-45ff-bce6-3cf9d9f8fe5b');

-- 14. Sentiments Seed
INSERT INTO sentiments (id, stock_id, source_type, source_id, sentiment_score, sentiment_label, explanation, confidence_score) VALUES
(uuid_generate_v4(), 'b19283e1-2a13-41bb-9876-0f81d11b332d', 'news_article', '30697fa2-cbdd-43ff-a9c4-1ad7d7f6fc3f', 0.850, 'positive', 'Positive WWDC comments regarding product upgrades.', 0.950),
(uuid_generate_v4(), 'c29384f2-3b24-42cc-8765-1f92e22c443e', 'news_article', '40798fb3-dcee-44ff-bad5-2be8d8f7fd4a', 0.700, 'positive', 'Anticipated regulatory FSD safety clearances in the EU.', 0.880);

-- 15. Watchlists Seed
INSERT INTO watchlists (id, user_id, name, description) VALUES
('80bb2fe7-1fcc-48ff-eff9-6f12fc2b0f8e', 'a37dbfb2-28df-4a60-a299-906cbbf8561d', 'My Core Tech List', 'Watchlist for high cap technology stocks');

-- 16. Watchlist Items Seed
INSERT INTO watchlist_items (id, watchlist_id, stock_id, sort_order) VALUES
(uuid_generate_v4(), '80bb2fe7-1fcc-48ff-eff9-6f12fc2b0f8e', 'b19283e1-2a13-41bb-9876-0f81d11b332d', 1),
(uuid_generate_v4(), '80bb2fe7-1fcc-48ff-eff9-6f12fc2b0f8e', 'c29384f2-3b24-42cc-8765-1f92e22c443e', 2);

-- 17. Scheduled Jobs Seed
INSERT INTO scheduled_jobs (id, user_id, stock_id, job_name, cron_expression, is_active) VALUES
(uuid_generate_v4(), 'a37dbfb2-28df-4a60-a299-906cbbf8561d', 'b19283e1-2a13-41bb-9876-0f81d11b332d', 'AAPL Post-Market Report Gen', '0 17 * * 1-5', TRUE);

-- 18. Alerts Seed
INSERT INTO alerts (id, user_id, stock_id, alert_type, target_value, is_triggered) VALUES
(uuid_generate_v4(), 'a37dbfb2-28df-4a60-a299-906cbbf8561d', 'c29384f2-3b24-42cc-8765-1f92e22c443e', 'price_below', 170.00, FALSE);

-- 19. Market Events Seed
INSERT INTO market_events (id, stock_id, event_type, event_date, title, description, impact_level) VALUES
(uuid_generate_v4(), 'b19283e1-2a13-41bb-9876-0f81d11b332d', 'earnings_release', '2026-07-30 20:30:00+00', 'Apple Q3 2026 Earnings Release', 'Quarterly earnings reporting date and investor conference call.', 'high');

-- 20. AI Model Usage Seed
INSERT INTO ai_model_usage (id, run_id, user_id, model_name, prompt_tokens, completion_tokens, cost, action_performed) VALUES
(uuid_generate_v4(), '60990fd5-feaa-46ff-cde7-4df0da09ff6c', 'a37dbfb2-28df-4a60-a299-906cbbf8561d', 'gpt-4o', 1450, 480, 0.014550, 'report_generation');

-- 21. Vector Embeddings Seed (Arbitrary dimension vectors cast to vector type)
INSERT INTO embeddings (id, source_type, source_id, chunk_index, content_chunk, embedding_model, embedding_dimension, embedding) VALUES
(uuid_generate_v4(), 'news_article', '30697fa2-cbdd-43ff-a9c4-1ad7d7f6fc3f', 1, 'At WWDC, Apple debuted Siri improvements backed by private clouds.', 'text-embedding-3-small', 1536, ARRAY_FILL(0.015::float, ARRAY[1536])::vector),
(uuid_generate_v4(), 'news_article', '40798fb3-dcee-44ff-bad5-2be8d8f7fd4a', 1, 'EU safety regulators assessment of FSD beta is nearing completion.', 'text-embedding-3-small', 1536, ARRAY_FILL(-0.024::float, ARRAY[1536])::vector);

COMMIT;
