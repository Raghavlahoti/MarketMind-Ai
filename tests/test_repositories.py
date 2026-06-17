# ============================================================================
# MARKETMIND AI - REPOSITORY INTEGRATION TESTS
# ============================================================================

import asyncio
import datetime
import unittest
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tests.conftest import create_test_schema, drop_test_schema
from app.core.config import settings
from app.models import Stock, PeriodTypeEnum
from app.repositories.stock import StockRepository
from app.repositories.company_profile import CompanyProfileRepository
from app.repositories.fundamentals import FundamentalsRepository


class TestRepositories(unittest.IsolatedAsyncioTestCase):
    """Integration tests for all database repositories using transactional rollback."""

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        # Create schema tables for SQLite (no-op against PostgreSQL with existing schema)
        await create_test_schema(self.engine)
        
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session = self.session_factory()
        
        # Start a transaction to ensure rollback after each test
        self.transaction = await self.session.begin()

        # Initialize repositories
        self.stock_repo = StockRepository(self.session)
        self.profile_repo = CompanyProfileRepository(self.session)
        self.fundamentals_repo = FundamentalsRepository(self.session)


    async def asyncTearDown(self) -> None:
        # Roll back all database operations to leave Supabase clean
        await self.transaction.rollback()
        await self.session.close()
        await self.engine.dispose()

    async def test_stock_and_prices_operations(self) -> None:
        # 1. Test Stock Creation
        unique_ticker = f"TEST{uuid4().hex[:4]}".upper()
        new_stock = Stock(
            ticker=unique_ticker,
            name="Test Repos Ltd",
            exchange="NASDAQ",
            sector="Technology",
            industry="Software",
            is_active=True
        )
        created_stock = await self.stock_repo.create(new_stock)
        self.assertIsNotNone(created_stock.id)
        self.assertEqual(created_stock.ticker, unique_ticker)

        # 2. Test Get Stock By Ticker (Case Insensitive)
        fetched_stock = await self.stock_repo.get_by_ticker(unique_ticker.lower())
        self.assertIsNotNone(fetched_stock)
        self.assertEqual(fetched_stock.id, created_stock.id)

        # 3. Test List Active Stocks
        active_stocks = await self.stock_repo.list_active_stocks(sector="Technology")
        self.assertTrue(any(s.id == created_stock.id for s in active_stocks))

        # 4. Test Upsert Prices
        prices_data = [
            {
                "price_date": datetime.date(2026, 6, 1),
                "open_price": 100.0,
                "high_price": 105.0,
                "low_price": 99.0,
                "close_price": 102.0,
                "volume": 1000000,
                "adjusted_close": 102.0,
            },
            {
                "price_date": datetime.date(2026, 6, 2),
                "open_price": 102.0,
                "high_price": 106.0,
                "low_price": 101.0,
                "close_price": 104.5,
                "volume": 1200000,
                "adjusted_close": 104.5,
            }
        ]
        await self.stock_repo.upsert_prices(created_stock.id, prices_data)
        
        # Verify range query
        prices = await self.stock_repo.get_prices_by_range(
            created_stock.id, datetime.date(2026, 6, 1), datetime.date(2026, 6, 2)
        )
        self.assertEqual(len(prices), 2)
        self.assertEqual(float(prices[0].close_price), 102.0)
        self.assertEqual(float(prices[1].close_price), 104.5)

        # Test latest price query
        latest = await self.stock_repo.get_latest_price(created_stock.id)
        self.assertIsNotNone(latest)
        self.assertEqual(latest.price_date, datetime.date(2026, 6, 2))

    async def test_company_profile_upsert(self) -> None:
        # Create stock dependency
        unique_ticker = f"PROF{uuid4().hex[:4]}".upper()
        new_stock = Stock(
            ticker=unique_ticker,
            name="Test Profile Corp",
            exchange="NYSE",
            is_active=True
        )
        stock = await self.stock_repo.create(new_stock)

        # Upsert Company Profile
        profile_data = {
            "description": "A test company description here.",
            "headquarters": "New York, NY, USA",
            "ceo": "Jane CEO",
            "employees": 500,
            "website": "https://testcorp.com",
            "market_cap": 1000000000.0,
            "shares_outstanding": 10000000.0,
        }
        profile = await self.profile_repo.upsert_profile(stock.id, profile_data)
        self.assertIsNotNone(profile.id)
        self.assertEqual(profile.ceo, "Jane CEO")
        self.assertEqual(profile.employees, 500)

        # Update Profile
        profile_data["ceo"] = "John CEO"
        profile_data["employees"] = 550
        updated_profile = await self.profile_repo.upsert_profile(stock.id, profile_data)
        self.assertEqual(updated_profile.ceo, "John CEO")
        self.assertEqual(updated_profile.employees, 550)

    async def test_fundamentals_upsert(self) -> None:
        # Create stock dependency
        unique_ticker = f"FUND{uuid4().hex[:4]}".upper()
        new_stock = Stock(
            ticker=unique_ticker,
            name="Test Fundamentals Corp",
            exchange="LSE",
            is_active=True
        )
        stock = await self.stock_repo.create(new_stock)

        # Upsert Fundamentals
        fundamentals_data = [
            {
                "report_date": datetime.date(2025, 12, 31),
                "period_type": "annual",
                "revenue": 50000000.0,
                "net_income": 5000000.0,
                "eps": 1.25,
                "ebitda": 7500000.0,
                "assets": 120000000.0,
                "liabilities": 40000000.0,
                "cash_flow": 6000000.0,
                "metadata": {"pe_ratio": 15.4}
            },
            {
                "report_date": datetime.date(2026, 3, 31),
                "period_type": "quarterly",
                "revenue": 14000000.0,
                "net_income": 1200000.0,
                "eps": 0.30,
                "ebitda": 2000000.0,
                "assets": 125000000.0,
                "liabilities": 42000000.0,
                "cash_flow": 1500000.0,
                "metadata": {}
            }
        ]
        await self.fundamentals_repo.upsert_fundamentals(stock.id, fundamentals_data)

        # Verify retrieval
        records = await self.fundamentals_repo.get_by_stock_id(stock.id)
        self.assertEqual(len(records), 2)
        
        # Verify filtering by period_type
        annuals = await self.fundamentals_repo.get_by_stock_id(stock.id, "annual")
        self.assertEqual(len(annuals), 1)
        self.assertEqual(annuals[0].period_type, PeriodTypeEnum.annual)
        self.assertEqual(float(annuals[0].revenue), 50000000.0)


if __name__ == "__main__":
    unittest.main()
