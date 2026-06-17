# ============================================================================
# MARKETMIND AI - WATCHLIST INTEGRATION FLOW TESTER
# ============================================================================

import asyncio
import uuid
import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models import User, Watchlist, WatchlistItem, Stock

BASE_URL = "http://127.0.0.1:8000/v1"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def run_watchlist_test() -> None:
    # 0. Set up database connection to clean up before/after test
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print_section("1. User Registration and Login")
    email = f"watchlist.tester.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "Watchlist",
        "last_name": "Tester"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Register user
        reg_resp = await client.post(f"{BASE_URL}/auth/register", json=register_payload)
        print(f"POST /auth/register status: {reg_resp.status_code}")
        if reg_resp.status_code != 201:
            print(f"Registration failed: {reg_resp.text}")
            await engine.dispose()
            return
            
        # Login user
        login_resp = await client.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
        print(f"POST /auth/login status: {login_resp.status_code}")
        if login_resp.status_code != 200:
            print(f"Login failed: {login_resp.text}")
            await engine.dispose()
            return
            
        token_data = login_resp.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(" -> Authentication Token acquired successfully.")

        # Resolve stock IDs for NVDA and AAPL
        async with async_session() as session:
            nvda = (await session.execute(select(Stock).where(Stock.ticker == "NVDA"))).scalars().first()
            if not nvda:
                # Ingest NVDA via stock service if needed
                from app.services.stock import StockService
                stock_service = StockService(session)
                nvda = await stock_service.get_stock("NVDA")
                await session.commit()
            
            aapl = (await session.execute(select(Stock).where(Stock.ticker == "AAPL"))).scalars().first()
            if not aapl:
                from app.services.stock import StockService
                stock_service = StockService(session)
                aapl = await stock_service.get_stock("AAPL")
                await session.commit()
                
            nvda_id = nvda.id
            aapl_id = aapl.id
            print(f" -> Stock IDs resolved: NVDA={nvda_id}, AAPL={aapl_id}")

        print_section("2. Watchlist CRUD Operations")
        
        # A. Create a Watchlist
        print("\n[A] POST /v1/watchlists (Create Watchlist)")
        watchlist_payload = {
            "name": "My Tech Portfolio",
            "description": "High growth semiconductor and tech stocks"
        }
        create_resp = await client.post(f"{BASE_URL}/watchlists/", json=watchlist_payload, headers=headers)
        print(f"  -> HTTP Status: {create_resp.status_code}")
        if create_resp.status_code != 201:
            print(f"  -> Error: {create_resp.text}")
            await engine.dispose()
            return
            
        wl_data = create_resp.json()
        wl_id = wl_data["id"]
        print(f"  -> Created Watchlist: ID={wl_id}, Name={wl_data['name']}, Desc={wl_data['description']}")
        
        # B. List Watchlists
        print("\n[B] GET /v1/watchlists (List User Watchlists)")
        list_resp = await client.get(f"{BASE_URL}/watchlists/", headers=headers)
        print(f"  -> HTTP Status: {list_resp.status_code}")
        lists_data = list_resp.json()
        print(f"  -> Watchlists Count: {len(lists_data)}")
        assert any(w["id"] == wl_id for w in lists_data), "Created watchlist should be in list"

        # C. Get Watchlist by ID
        print("\n[C] GET /v1/watchlists/{id} (Get Watchlist Details)")
        get_resp = await client.get(f"{BASE_URL}/watchlists/{wl_id}", headers=headers)
        print(f"  -> HTTP Status: {get_resp.status_code}")
        wl_get = get_resp.json()
        assert wl_get["name"] == "My Tech Portfolio"
        print(f"  -> Watchlist retrieved: Name={wl_get['name']}, Items={wl_get['items']}")

        # D. Update Watchlist
        print("\n[D] PUT /v1/watchlists/{id} (Update Watchlist)")
        update_payload = {
            "name": "My Core Growth Watchlist",
            "description": "Updated tech focus list"
        }
        update_resp = await client.put(f"{BASE_URL}/watchlists/{wl_id}", json=update_payload, headers=headers)
        print(f"  -> HTTP Status: {update_resp.status_code}")
        wl_updated = update_resp.json()
        assert wl_updated["name"] == "My Core Growth Watchlist"
        print(f"  -> Watchlist updated: Name={wl_updated['name']}, Desc={wl_updated['description']}")

        print_section("3. Watchlist Items CRUD Operations")
        
        # A. Add Stock item (by Ticker)
        print("\n[A] POST /v1/watchlists/{id}/items (Add Stock by Ticker)")
        item_payload_ticker = {"ticker": "NVDA"}
        add_ticker_resp = await client.post(f"{BASE_URL}/watchlists/{wl_id}/items", json=item_payload_ticker, headers=headers)
        print(f"  -> HTTP Status: {add_ticker_resp.status_code}")
        if add_ticker_resp.status_code != 201:
            print(f"  -> Error adding ticker: {add_ticker_resp.text}")
        else:
            item_data = add_ticker_resp.json()
            print(f"  -> Added item: ID={item_data['id']}, Stock={item_data['stock']['ticker']}")

        # B. Add Stock item (by Stock ID)
        print("\n[B] POST /v1/watchlists/{id}/items (Add Stock by Stock ID)")
        item_payload_id = {"stock_id": str(aapl_id)}
        add_id_resp = await client.post(f"{BASE_URL}/watchlists/{wl_id}/items", json=item_payload_id, headers=headers)
        print(f"  -> HTTP Status: {add_id_resp.status_code}")
        if add_id_resp.status_code != 201:
            print(f"  -> Error adding by stock ID: {add_id_resp.text}")
        else:
            item_data2 = add_id_resp.json()
            print(f"  -> Added item: ID={item_data2['id']}, Stock={item_data2['stock']['ticker']}")

        # C. Get Watchlist details to verify items
        print("\n[C] GET /v1/watchlists/{id} (Verify Items List)")
        get_items_resp = await client.get(f"{BASE_URL}/watchlists/{wl_id}", headers=headers)
        wl_details = get_items_resp.json()
        print(f"  -> Watchlist items count: {len(wl_details['items'])}")
        for i in wl_details["items"]:
            print(f"    - Stock: {i['stock']['ticker']}, Added At: {i['added_at']}")
        assert len(wl_details["items"]) == 2, "Watchlist should contain exactly 2 items"

        # D. Add duplicate item (should fail with 400)
        print("\n[D] POST /v1/watchlists/{id}/items (Verify Duplicate Protection)")
        dup_resp = await client.post(f"{BASE_URL}/watchlists/{wl_id}/items", json=item_payload_ticker, headers=headers)
        print(f"  -> HTTP Status: {dup_resp.status_code}")
        print(f"  -> Response Body: {dup_resp.json()}")
        assert dup_resp.status_code == 400

        # E. Remove Stock item
        print("\n[E] DELETE /v1/watchlists/{id}/items/{stock_id} (Remove item)")
        remove_resp = await client.delete(f"{BASE_URL}/watchlists/{wl_id}/items/{nvda_id}", headers=headers)
        print(f"  -> HTTP Status: {remove_resp.status_code}")
        
        # Verify item count is now 1
        get_after_remove = await client.get(f"{BASE_URL}/watchlists/{wl_id}", headers=headers)
        wl_after_remove = get_after_remove.json()
        print(f"  -> Watchlist items count after removal: {len(wl_after_remove['items'])}")
        assert len(wl_after_remove['items']) == 1
        assert wl_after_remove['items'][0]['stock']['ticker'] == "AAPL"

        # F. Delete Watchlist
        print("\n[F] DELETE /v1/watchlists/{id} (Delete Watchlist)")
        delete_resp = await client.delete(f"{BASE_URL}/watchlists/{wl_id}", headers=headers)
        print(f"  -> HTTP Status: {delete_resp.status_code}")

        # G. Verify Watchlist is deleted
        print("\n[G] GET /v1/watchlists/{id} (Verify Deletion)")
        final_get = await client.get(f"{BASE_URL}/watchlists/{wl_id}", headers=headers)
        print(f"  -> HTTP Status: {final_get.status_code}")
        assert final_get.status_code == 404

        # Clean up database test user
        print_section("4. Database Clean-up")
        async with async_session() as session:
            # Delete user record which cascades to watchlists (if any were left, but we deleted it)
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
            print(f" -> Cleaned up test user {email} successfully.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_watchlist_test())
