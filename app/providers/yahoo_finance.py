# ============================================================================
# MARKETMIND AI - YAHOO FINANCE DATA INGESTION PROVIDER
# ============================================================================

import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
import yfinance as yf

logger = logging.getLogger("marketmind_ai")


class YahooFinanceProvider:
    """Synchronous Yahoo Finance wrapper with async threading execution."""

    def __init__(self) -> None:
        pass

    async def get_stock_metadata(self, symbol: str) -> Dict[str, Any]:
        """Fetches basic stock information asynchronously."""
        return await asyncio.to_thread(self._get_stock_metadata_sync, symbol)

    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Fetches detailed company profile asynchronously."""
        return await asyncio.to_thread(self._get_company_profile_sync, symbol)

    async def get_analyst_consensus(self, symbol: str) -> Dict[str, Any]:
        """Fetches analyst ratings consensus asynchronously."""
        return await asyncio.to_thread(self._get_analyst_consensus_sync, symbol)

    async def get_historical_prices(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetches historical price bars asynchronously."""
        return await asyncio.to_thread(self._get_historical_prices_sync, symbol, start_date, end_date)

    async def get_fundamentals(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches both annual and quarterly fundamentals asynchronously."""
        return await asyncio.to_thread(self._get_fundamentals_sync, symbol)

    # ------------------------------------------------------------------------
    # Synchronous Implementations (Executed in ThreadPool)
    # ------------------------------------------------------------------------

    def _get_stock_metadata_sync(self, symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        name = info.get("longName") or info.get("shortName") or symbol
        exchange = info.get("exchange") or "Unknown"
        sector = info.get("sector")
        industry = info.get("industry")
        
        return {
            "ticker": symbol.upper(),
            "name": name,
            "exchange": exchange,
            "sector": sector,
            "industry": industry,
            "is_active": True
        }

    def _get_company_profile_sync(self, symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Build headquarters string
        hq_parts = []
        for key in ["city", "state", "country"]:
            val = info.get(key)
            if val:
                hq_parts.append(str(val))
        headquarters = ", ".join(hq_parts) if hq_parts else None

        # Parse CEO name
        ceo = None
        officers = info.get("companyOfficers", [])
        if officers:
            # Look for CEO in titles
            for officer in officers:
                title = officer.get("title", "").lower()
                if "ceo" in title or "chief executive" in title or "president" in title:
                    ceo = officer.get("name")
                    break
            # Fallback to first officer
            if not ceo:
                ceo = officers[0].get("name")

        return {
            "description": info.get("longBusinessSummary"),
            "headquarters": headquarters,
            "ceo": ceo,
            "employees": info.get("fullTimeEmployees"),
            "website": info.get("website"),
            "founded_year": None,  # Not present in standard yfinance info
            "market_cap": info.get("marketCap"),
            "shares_outstanding": info.get("sharesOutstanding"),
        }

    def _get_analyst_consensus_sync(self, symbol: str) -> Dict[str, Any]:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Default counts
        buy_count = 0
        hold_count = 0
        sell_count = 0
        
        try:
            recs = ticker.recommendations
            if recs is not None and not recs.empty:
                # Find current month (period '0m')
                current_recs = recs[recs["period"] == "0m"]
                if current_recs.empty:
                    current_recs = recs.iloc[0:1]
                
                # Sum strongBuy + buy
                strong_buy = current_recs.get("strongBuy", pd.Series([0])).values[0]
                buy = current_recs.get("buy", pd.Series([0])).values[0]
                buy_count = int(strong_buy + buy)
                
                # Hold
                hold_count = int(current_recs.get("hold", pd.Series([0])).values[0])
                
                # Sum sell + strongSell
                sell = current_recs.get("sell", pd.Series([0])).values[0]
                strong_sell = current_recs.get("strongSell", pd.Series([0])).values[0]
                sell_count = int(sell + strong_sell)
        except Exception as e:
            logger.warning("Failed to retrieve analyst consensus counts for %s: %s", symbol, e)
            
        average_target_price = info.get("targetMeanPrice")
        
        return {
            "buy_count": buy_count,
            "hold_count": hold_count,
            "sell_count": sell_count,
            "average_target_price": average_target_price
        }

    def _get_historical_prices_sync(
        self, symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        ticker = yf.Ticker(symbol)
        
        # Determine parameters
        if start_date or end_date:
            df = ticker.history(start=start_date, end=end_date, auto_adjust=False)
        else:
            df = ticker.history(period="2y", auto_adjust=False)
            
        if df.empty:
            return []
            
        prices = []
        for idx, row in df.iterrows():
            # Index is typically a DatetimeIndex
            price_date = idx.date() if hasattr(idx, "date") else idx
            
            # Close/Adj Close logic
            close_val = float(row["Close"])
            adj_close_val = float(row.get("Adj Close", close_val))
            
            # Ensure none of the prices are NaN
            if pd.isna(close_val) or pd.isna(row["Open"]):
                continue
                
            prices.append({
                "price_date": price_date,
                "open_price": float(row["Open"]),
                "high_price": float(row["High"]),
                "low_price": float(row["Low"]),
                "close_price": close_val,
                "volume": int(row["Volume"]),
                "adjusted_close": adj_close_val,
            })
            
        return prices

    def _get_fundamentals_sync(self, symbol: str) -> List[Dict[str, Any]]:
        ticker = yf.Ticker(symbol)
        
        fundamentals = []
        
        # We query both annual and quarterly statements
        annual_financials = ticker.financials
        annual_balance_sheet = ticker.balance_sheet
        annual_cashflow = ticker.cashflow
        
        quarterly_financials = ticker.quarterly_financials
        quarterly_balance_sheet = ticker.quarterly_balance_sheet
        quarterly_cashflow = ticker.quarterly_cashflow
        
        # Helper to extract from dataframe with tolerance date matching
        def extract_value(df, row_label, target_date):
            if df is None or df.empty or row_label not in df.index:
                return None
            for col in df.columns:
                col_date = col.date() if hasattr(col, "date") else col
                if abs((col_date - target_date).days) <= 3:
                    val = df.loc[row_label, col]
                    if pd.isna(val):
                        return None
                    return float(val)
            return None

        # Process Annual
        if annual_financials is not None and not annual_financials.empty:
            for col in annual_financials.columns:
                target_date = col.date() if hasattr(col, "date") else col
                
                # Fetch properties
                rev = extract_value(annual_financials, "Total Revenue", target_date)
                net_inc = extract_value(annual_financials, "Net Income", target_date)
                eps = extract_value(annual_financials, "Diluted EPS", target_date) or extract_value(annual_financials, "Basic EPS", target_date)
                ebitda = extract_value(annual_financials, "EBITDA", target_date)
                
                assets = extract_value(annual_balance_sheet, "Total Assets", target_date)
                liabilities = extract_value(annual_balance_sheet, "Total Liabilities Net Minority Interest", target_date) or extract_value(annual_balance_sheet, "Total Liabilities", target_date)
                
                cf = extract_value(annual_cashflow, "Operating Cash Flow", target_date) or extract_value(annual_cashflow, "Free Cash Flow", target_date)
                
                fundamentals.append({
                    "report_date": target_date,
                    "period_type": "annual",
                    "revenue": rev,
                    "net_income": net_inc,
                    "eps": eps,
                    "ebitda": ebitda,
                    "assets": assets,
                    "liabilities": liabilities,
                    "cash_flow": cf,
                    "metadata": {}
                })
                
        # Process Quarterly
        if quarterly_financials is not None and not quarterly_financials.empty:
            for col in quarterly_financials.columns:
                target_date = col.date() if hasattr(col, "date") else col
                
                # Fetch properties
                rev = extract_value(quarterly_financials, "Total Revenue", target_date)
                net_inc = extract_value(quarterly_financials, "Net Income", target_date)
                eps = extract_value(quarterly_financials, "Diluted EPS", target_date) or extract_value(quarterly_financials, "Basic EPS", target_date)
                ebitda = extract_value(quarterly_financials, "EBITDA", target_date)
                
                assets = extract_value(quarterly_balance_sheet, "Total Assets", target_date)
                liabilities = extract_value(quarterly_balance_sheet, "Total Liabilities Net Minority Interest", target_date) or extract_value(quarterly_balance_sheet, "Total Liabilities", target_date)
                
                cf = extract_value(quarterly_cashflow, "Operating Cash Flow", target_date) or extract_value(quarterly_cashflow, "Free Cash Flow", target_date)
                
                fundamentals.append({
                    "report_date": target_date,
                    "period_type": "quarterly",
                    "revenue": rev,
                    "net_income": net_inc,
                    "eps": eps,
                    "ebitda": ebitda,
                    "assets": assets,
                    "liabilities": liabilities,
                    "cash_flow": cf,
                    "metadata": {}
                })

        return fundamentals
