"""initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-06 18:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # 2. Create trigger function
    op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)

    # 3. Create ENUMs
    op.execute("CREATE TYPE period_type_enum AS ENUM ('annual', 'quarterly', 'trailing_twelve_months');")
    op.execute("CREATE TYPE rating_type_enum AS ENUM ('strong_buy', 'buy', 'hold', 'sell', 'strong_sell');")
    op.execute("CREATE TYPE report_status_enum AS ENUM ('draft', 'generating', 'completed', 'failed');")
    op.execute("CREATE TYPE run_status_enum AS ENUM ('pending', 'running', 'completed', 'failed');")
    op.execute("CREATE TYPE sentiment_label_enum AS ENUM ('positive', 'neutral', 'negative');")
    op.execute("CREATE TYPE source_type_enum AS ENUM ('news_article', 'earnings_transcript', 'research_report');")
    op.execute("CREATE TYPE event_impact_enum AS ENUM ('high', 'medium', 'low');")
    op.execute("CREATE TYPE alert_type_enum AS ENUM ('price_above', 'price_below', 'sentiment_above', 'sentiment_below', 'new_research_report');")
    op.execute("""
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
    """)

    # 4. Create Tables
    op.execute("""
    CREATE TABLE users (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        email VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(100),
        last_name VARCHAR(100),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE stocks (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        ticker VARCHAR(20) NOT NULL UNIQUE,
        name VARCHAR(255) NOT NULL,
        exchange VARCHAR(50) NOT NULL,
        sector VARCHAR(100),
        industry VARCHAR(100),
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
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
    """)

    op.execute("""
    CREATE TABLE analyst_consensus (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        stock_id UUID NOT NULL UNIQUE REFERENCES stocks(id) ON DELETE CASCADE,
        buy_count INT NOT NULL DEFAULT 0 CONSTRAINT chk_buy_count CHECK (buy_count >= 0),
        hold_count INT NOT NULL DEFAULT 0 CONSTRAINT chk_hold_count CHECK (hold_count >= 0),
        sell_count INT NOT NULL DEFAULT 0 CONSTRAINT chk_sell_count CHECK (sell_count >= 0),
        average_target_price NUMERIC(12, 2) CONSTRAINT chk_avg_target_price CHECK (average_target_price >= 0),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
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
    """)

    op.execute("""
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
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        CONSTRAINT uq_stock_fundamental_period UNIQUE (stock_id, report_date, period_type)
    );
    """)

    op.execute("""
    CREATE TABLE news_articles (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        title VARCHAR(512) NOT NULL,
        content TEXT NOT NULL,
        summary TEXT,
        source_name VARCHAR(100),
        url TEXT,
        published_at TIMESTAMP WITH TIME ZONE NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE news_article_stocks (
        article_id UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        PRIMARY KEY (article_id, stock_id)
    );
    """)

    op.execute("""
    CREATE TABLE earnings_transcripts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        quarter INT NOT NULL CONSTRAINT chk_transcript_quarter CHECK (quarter >= 1 AND quarter <= 4),
        year INT NOT NULL CONSTRAINT chk_transcript_year CHECK (year >= 1900 AND year <= 2100),
        publish_date DATE NOT NULL,
        raw_text TEXT NOT NULL,
        sections JSONB NOT NULL DEFAULT '[]'::jsonb,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        CONSTRAINT uq_stock_transcript_period UNIQUE (stock_id, year, quarter)
    );
    """)

    op.execute("""
    CREATE TABLE research_runs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        trigger_type VARCHAR(50) NOT NULL,
        status run_status_enum NOT NULL DEFAULT 'pending',
        started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        completed_at TIMESTAMP WITH TIME ZONE,
        error_message TEXT,
        config JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
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
    """)

    op.execute("""
    CREATE TABLE research_report_sections (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        report_id UUID NOT NULL REFERENCES research_reports(id) ON DELETE CASCADE,
        section_type report_section_type_enum NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        CONSTRAINT uq_report_section UNIQUE (report_id, section_type)
    );
    """)

    op.execute("""
    CREATE TABLE research_sources (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        run_id UUID NOT NULL REFERENCES research_runs(id) ON DELETE CASCADE,
        source_type source_type_enum NOT NULL,
        source_id UUID NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE sentiments (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        source_type source_type_enum NOT NULL,
        source_id UUID NOT NULL,
        sentiment_score NUMERIC(4, 3) NOT NULL CONSTRAINT chk_sentiment_score CHECK (sentiment_score >= -1.000 AND sentiment_score <= 1.000),
        sentiment_label sentiment_label_enum NOT NULL,
        explanation TEXT,
        confidence_score NUMERIC(4, 3) CONSTRAINT chk_confidence_score CHECK (confidence_score >= 0.000 AND confidence_score <= 1.000),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE watchlists (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name VARCHAR(100) NOT NULL,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE watchlist_items (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        watchlist_id UUID NOT NULL REFERENCES watchlists(id) ON DELETE CASCADE,
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        sort_order INT NOT NULL DEFAULT 0,
        CONSTRAINT uq_watchlist_stock UNIQUE (watchlist_id, stock_id)
    );
    """)

    op.execute("""
    CREATE TABLE scheduled_jobs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        job_name VARCHAR(150) NOT NULL,
        cron_expression VARCHAR(100) NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        last_run_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE alerts (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        stock_id UUID NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
        alert_type alert_type_enum NOT NULL,
        target_value NUMERIC(12, 4) NOT NULL,
        is_triggered BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE market_events (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        stock_id UUID REFERENCES stocks(id) ON DELETE CASCADE,
        event_type VARCHAR(100) NOT NULL,
        event_date TIMESTAMP WITH TIME ZONE NOT NULL,
        title VARCHAR(255) NOT NULL,
        description TEXT,
        impact_level event_impact_enum NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE ai_model_usage (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        run_id UUID REFERENCES research_runs(id) ON DELETE SET NULL,
        user_id UUID REFERENCES users(id) ON DELETE SET NULL,
        model_name VARCHAR(100) NOT NULL,
        prompt_tokens INT NOT NULL DEFAULT 0 CONSTRAINT chk_prompt_tokens CHECK (prompt_tokens >= 0),
        completion_tokens INT NOT NULL DEFAULT 0 CONSTRAINT chk_comp_tokens CHECK (completion_tokens >= 0),
        cost NUMERIC(10, 6) NOT NULL DEFAULT 0.000000 CONSTRAINT chk_usage_cost CHECK (cost >= 0),
        action_performed VARCHAR(100) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    op.execute("""
    CREATE TABLE embeddings (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        source_type source_type_enum NOT NULL,
        source_id UUID NOT NULL,
        chunk_index INT NOT NULL,
        content_chunk TEXT NOT NULL,
        embedding_model VARCHAR(100) NOT NULL,
        embedding_dimension INT NOT NULL CONSTRAINT chk_dimension_positive CHECK (embedding_dimension > 0),
        embedding vector NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    """)

    # 5. Create Triggers
    op.execute("CREATE TRIGGER trg_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_stocks_updated_at BEFORE UPDATE ON stocks FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_company_profiles_updated_at BEFORE UPDATE ON company_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_analyst_consensus_updated_at BEFORE UPDATE ON analyst_consensus FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_stock_prices_updated_at BEFORE UPDATE ON stock_prices FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_company_fundamentals_updated_at BEFORE UPDATE ON company_fundamentals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_news_articles_updated_at BEFORE UPDATE ON news_articles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_earnings_transcripts_updated_at BEFORE UPDATE ON earnings_transcripts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_research_reports_updated_at BEFORE UPDATE ON research_reports FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_watchlists_updated_at BEFORE UPDATE ON watchlists FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_scheduled_jobs_updated_at BEFORE UPDATE ON scheduled_jobs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")
    op.execute("CREATE TRIGGER trg_market_events_updated_at BEFORE UPDATE ON market_events FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();")

    # 6. Create Indexes
    op.execute("CREATE INDEX idx_company_profiles_stock ON company_profiles(stock_id);")
    op.execute("CREATE INDEX idx_analyst_consensus_stock ON analyst_consensus(stock_id);")
    op.execute("CREATE INDEX idx_stock_prices_stock ON stock_prices(stock_id);")
    op.execute("CREATE INDEX idx_company_fundamentals_stock ON company_fundamentals(stock_id);")
    op.execute("CREATE INDEX idx_news_article_stocks_stock ON news_article_stocks(stock_id);")
    op.execute("CREATE INDEX idx_news_article_stocks_art ON news_article_stocks(article_id);")
    op.execute("CREATE INDEX idx_earnings_transcripts_stock ON earnings_transcripts(stock_id);")
    op.execute("CREATE INDEX idx_research_runs_user ON research_runs(user_id);")
    op.execute("CREATE INDEX idx_research_runs_stock ON research_runs(stock_id);")
    op.execute("CREATE INDEX idx_research_reports_user ON research_reports(user_id);")
    op.execute("CREATE INDEX idx_research_reports_stock ON research_reports(stock_id);")
    op.execute("CREATE INDEX idx_research_reports_run ON research_reports(run_id);")
    op.execute("CREATE INDEX idx_research_report_sections_rep ON research_report_sections(report_id);")
    op.execute("CREATE INDEX idx_research_sources_run ON research_sources(run_id);")
    op.execute("CREATE INDEX idx_sentiments_stock ON sentiments(stock_id);")
    op.execute("CREATE INDEX idx_watchlists_user ON watchlists(user_id);")
    op.execute("CREATE INDEX idx_watchlist_items_wl ON watchlist_items(watchlist_id);")
    op.execute("CREATE INDEX idx_watchlist_items_stock ON watchlist_items(stock_id);")
    op.execute("CREATE INDEX idx_scheduled_jobs_user ON scheduled_jobs(user_id);")
    op.execute("CREATE INDEX idx_scheduled_jobs_stock ON scheduled_jobs(stock_id);")
    op.execute("CREATE INDEX idx_alerts_user ON alerts(user_id);")
    op.execute("CREATE INDEX idx_alerts_stock ON alerts(stock_id);")
    op.execute("CREATE INDEX idx_market_events_stock ON market_events(stock_id);")
    op.execute("CREATE INDEX idx_ai_model_usage_run ON ai_model_usage(run_id);")
    op.execute("CREATE INDEX idx_ai_model_usage_user ON ai_model_usage(user_id);")
    op.execute("CREATE INDEX idx_stock_prices_timeline ON stock_prices(stock_id, price_date DESC);")
    op.execute("CREATE INDEX idx_company_fundamentals_timeline ON company_fundamentals(stock_id, report_date DESC);")
    op.execute("CREATE INDEX idx_news_articles_published ON news_articles(published_at DESC);")
    op.execute("CREATE INDEX idx_market_events_date ON market_events(event_date DESC);")
    op.execute("CREATE INDEX idx_sentiments_created ON sentiments(created_at DESC);")
    op.execute("CREATE INDEX idx_sentiments_logical_source ON sentiments(source_type, source_id);")
    op.execute("CREATE INDEX idx_embeddings_logical_source ON embeddings(source_type, source_id);")
    op.execute("CREATE INDEX idx_research_sources_logical ON research_sources(source_type, source_id);")
    op.execute("CREATE INDEX idx_company_fundamentals_metadata ON company_fundamentals USING gin (metadata);")
    op.execute("CREATE INDEX idx_research_runs_config ON research_runs USING gin (config);")
    op.execute("CREATE INDEX idx_earnings_transcripts_sections ON earnings_transcripts USING gin (sections);")
    op.execute("CREATE INDEX idx_news_articles_content_tsv ON news_articles USING gin (to_tsvector('english', content));")
    op.execute("CREATE INDEX idx_earnings_transcripts_text_tsv ON earnings_transcripts USING gin (to_tsvector('english', raw_text));")
    op.execute("CREATE INDEX idx_report_sections_content_tsv ON research_report_sections USING gin (to_tsvector('english', content));")
    op.execute("CREATE INDEX idx_stocks_ticker_trgm ON stocks USING gin (ticker gin_trgm_ops);")
    op.execute("CREATE INDEX idx_stocks_name_trgm ON stocks USING gin (name gin_trgm_ops);")


def downgrade() -> None:
    # Drop in reverse order
    op.execute("DROP TABLE IF EXISTS embeddings CASCADE;")
    op.execute("DROP TABLE IF EXISTS ai_model_usage CASCADE;")
    op.execute("DROP TABLE IF EXISTS market_events CASCADE;")
    op.execute("DROP TABLE IF EXISTS alerts CASCADE;")
    op.execute("DROP TABLE IF EXISTS scheduled_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS watchlist_items CASCADE;")
    op.execute("DROP TABLE IF EXISTS watchlists CASCADE;")
    op.execute("DROP TABLE IF EXISTS sentiments CASCADE;")
    op.execute("DROP TABLE IF EXISTS research_sources CASCADE;")
    op.execute("DROP TABLE IF EXISTS research_report_sections CASCADE;")
    op.execute("DROP TABLE IF EXISTS research_reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS research_runs CASCADE;")
    op.execute("DROP TABLE IF EXISTS earnings_transcripts CASCADE;")
    op.execute("DROP TABLE IF EXISTS news_article_stocks CASCADE;")
    op.execute("DROP TABLE IF EXISTS news_articles CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_fundamentals CASCADE;")
    op.execute("DROP TABLE IF EXISTS stock_prices CASCADE;")
    op.execute("DROP TABLE IF EXISTS analyst_consensus CASCADE;")
    op.execute("DROP TABLE IF EXISTS company_profiles CASCADE;")
    op.execute("DROP TABLE IF EXISTS stocks CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column CASCADE;")

    # Drop types
    op.execute("DROP TYPE IF EXISTS period_type_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS rating_type_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS report_status_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS run_status_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS sentiment_label_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS source_type_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS event_impact_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS alert_type_enum CASCADE;")
    op.execute("DROP TYPE IF EXISTS report_section_type_enum CASCADE;")
