# ============================================================================
# MARKETMIND AI - SERVICE UNIT & CACHE TESTS
# ============================================================================

import asyncio
import datetime
import unittest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from tests.conftest import create_test_schema, drop_test_schema
from app.core.config import settings
from app.models import Stock, CompanyProfile
from app.services.stock import StockService


class TestStockService(unittest.IsolatedAsyncioTestCase):
    """Unit and cache policy tests for StockService using transactional rollback."""

    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine(settings.DATABASE_URL, echo=False)
        
        # Create schema tables for SQLite (no-op against PostgreSQL with existing schema)
        await create_test_schema(self.engine)
        
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)
        self.session = self.session_factory()
        
        # Start a transaction to ensure rollback after each test
        self.transaction = await self.session.begin()

        # Initialize the service
        self.stock_service = StockService(self.session)

        
        # Mock responses
        self.mock_metadata = {
            "ticker": f"MOCK{uuid4().hex[:4]}".upper(),
            "name": "Mock Ingest Inc",
            "exchange": "NASDAQ",
            "sector": "Financials",
            "industry": "Asset Management",
            "is_active": True
        }
        
        self.mock_profile = {
            "description": "Mocked company profile description.",
            "headquarters": "San Francisco, CA, USA",
            "ceo": "Jane Mock",
            "employees": 120,
            "website": "https://mockingest.com",
            "market_cap": 250000000.0,
            "shares_outstanding": 5000000.0,
        }
        
        self.mock_consensus = {
            "buy_count": 12,
            "hold_count": 4,
            "sell_count": 1,
            "average_target_price": 55.0,
        }
        
        self.mock_prices = [
            {
                "price_date": datetime.date(2026, 6, 1),
                "open_price": 48.0,
                "high_price": 52.0,
                "low_price": 47.5,
                "close_price": 50.0,
                "volume": 50000,
                "adjusted_close": 50.0,
            }
        ]
        
        self.mock_fundamentals = [
            {
                "report_date": datetime.date(2025, 12, 31),
                "period_type": "annual",
                "revenue": 10000000.0,
                "net_income": 1500000.0,
                "eps": 0.30,
                "ebitda": 2200000.0,
                "assets": 15000000.0,
                "liabilities": 5000000.0,
                "cash_flow": 1200000.0,
                "metadata": {}
            }
        ]

    async def asyncTearDown(self) -> None:
        await self.transaction.rollback()
        await self.session.close()
        await self.engine.dispose()

    @patch("app.services.stock.YahooFinanceProvider")
    async def test_stock_caching_and_refresh_policies(self, mock_provider_class) -> None:
        # Configure provider mocks
        mock_provider = mock_provider_class.return_value
        mock_provider.get_stock_metadata = AsyncMock(return_value=self.mock_metadata)
        mock_provider.get_company_profile = AsyncMock(return_value=self.mock_profile)
        mock_provider.get_analyst_consensus = AsyncMock(return_value=self.mock_consensus)
        mock_provider.get_historical_prices = AsyncMock(return_value=self.mock_prices)
        mock_provider.get_fundamentals = AsyncMock(return_value=self.mock_fundamentals)

        # Re-assign provider in service to use the mocked instance
        self.stock_service.yf_provider = mock_provider

        ticker_symbol = self.mock_metadata["ticker"]

        # --- FIRST CALL: Database is empty, Ingestion is triggered ---
        stock1 = await self.stock_service.get_stock(ticker_symbol)
        self.assertEqual(stock1.ticker, ticker_symbol)
        self.assertEqual(stock1.name, "Mock Ingest Inc")
        mock_provider.get_stock_metadata.assert_called_once_with(ticker_symbol)

        # Reset call count
        mock_provider.get_stock_metadata.reset_mock()

        # --- SECOND CALL: Cache is fresh, returns directly from DB ---
        stock2 = await self.stock_service.get_stock(ticker_symbol)
        self.assertEqual(stock2.id, stock1.id)
        mock_provider.get_stock_metadata.assert_not_called()

        # --- TEST COMPANY PROFILE CACHING ---
        # First call gets profile from mock provider
        profile1 = await self.stock_service.get_profile(ticker_symbol)
        self.assertEqual(profile1.ceo, "Jane Mock")
        mock_provider.get_company_profile.assert_called_once_with(ticker_symbol)
        
        # Reset and query again (should hit cache)
        mock_provider.get_company_profile.reset_mock()
        profile2 = await self.stock_service.get_profile(ticker_symbol)
        self.assertEqual(profile2.id, profile1.id)
        mock_provider.get_company_profile.assert_not_called()

        # --- TEST STALE CACHE REFRESH POLICY ---
        # Modify the updated_at of the profile to be 25 hours in the past
        profile2.updated_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=25)
        # Flush to DB
        await self.session.flush()

        # Query profile again (stale cache should trigger yfinance refresh)
        mock_provider.get_company_profile.reset_mock()
        self.mock_profile["ceo"] = "Updated CEO name"
        mock_provider.get_company_profile.return_value = self.mock_profile
        
        profile3 = await self.stock_service.get_profile(ticker_symbol)
        self.assertEqual(profile3.ceo, "Updated CEO name")
        mock_provider.get_company_profile.assert_called_once_with(ticker_symbol)


if __name__ == "__main__":
    unittest.main()
