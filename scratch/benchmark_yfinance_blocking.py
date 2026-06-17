# ============================================================================
# MARKETMIND AI - YFINANCE EVENT LOOP BLOCKING BENCHMARK
# ============================================================================

import asyncio
import time
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.providers.yahoo_finance import YahooFinanceProvider

class EventLoopMonitor:
    def __init__(self, interval: float = 0.010):
        self.interval = interval
        self.max_delay = 0.0
        self.running = False

    async def start(self):
        self.running = True
        self.max_delay = 0.0
        asyncio.create_task(self._run())

    async def stop(self):
        self.running = False

    async def _run(self):
        while self.running:
            t0 = time.perf_counter()
            await asyncio.sleep(self.interval)
            t1 = time.perf_counter()
            delay = (t1 - t0) - self.interval
            if delay > self.max_delay:
                self.max_delay = delay


async def main():
    print("Initializing event loop monitor (ticking every 10ms)...")
    monitor = EventLoopMonitor(interval=0.010)
    await monitor.start()

    provider = YahooFinanceProvider()
    symbol = "NVDA"

    print(f"Starting concurrent fetching from YahooFinanceProvider for {symbol}...")
    start_time = time.perf_counter()

    # We will query all provider endpoints to simulate full data collection
    try:
        tasks = [
            provider.get_stock_metadata(symbol),
            provider.get_company_profile(symbol),
            provider.get_analyst_consensus(symbol),
            provider.get_historical_prices(symbol),
            provider.get_fundamentals(symbol)
        ]
        results = await asyncio.gather(*tasks)
        print("Successfully fetched all Yahoo Finance data.")
    except Exception as e:
        print(f"Error fetching Yahoo Finance data: {e}")

    duration = time.perf_counter() - start_time
    await monitor.stop()

    print(f"Benchmark finished in {duration:.2f} seconds.")
    print(f"Maximum event loop blockage delay: {monitor.max_delay * 1000:.2f} ms")
    
    # Assert event loop wasn't blocked for more than 100ms
    if monitor.max_delay < 0.100:
        print("PASS: Event loop was NOT blocked. All yfinance calls are properly offloaded to threads.")
    else:
        print("FAIL: Event loop was blocked! Maximum delay exceeded 100ms.")

if __name__ == "__main__":
    asyncio.run(main())
