# ============================================================================
# MARKETMIND AI - ALERTS INTEGRATION FLOW TESTER
# ============================================================================

import asyncio
import uuid
import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from app.models import User, Alert, Stock

BASE_URL = "http://127.0.0.1:8000/v1"


def print_section(title: str):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)


async def run_alerts_test() -> None:
    # 0. Set up database connection to clean up before/after test
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    print_section("1. User Registration and Login")
    email = f"alerts.tester.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": "Alerts",
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

        # Resolve Stock ID for NVDA and get latest price
        async with async_session() as session:
            nvda = (await session.execute(select(Stock).where(Stock.ticker == "NVDA"))).scalars().first()
            if not nvda:
                from app.services.stock import StockService
                stock_service = StockService(session)
                nvda = await stock_service.get_stock("NVDA")
                await session.commit()
            
            nvda_id = nvda.id
            
            # Fetch latest price
            from app.repositories.stock import StockRepository
            stock_repo = StockRepository(session)
            latest_price_rec = await stock_repo.get_latest_price(nvda_id)
            current_price = float(latest_price_rec.close_price) if latest_price_rec else 120.0
            print(f" -> Stock NVDA ID resolved: {nvda_id}, Current Price: ${current_price:.2f}")

        print_section("2. Alerts CRUD Operations")
        
        # A. Create Alerts
        # Create an alert that triggers when price goes below a value higher than current price (triggers immediately)
        target_trigger_immediate = current_price + 10.0
        # Create an alert that triggers when price goes above a value higher than current price (does not trigger yet)
        target_no_trigger = current_price + 50.0

        print("\n[A] POST /v1/alerts/ (Create Price Alerts)")
        payload_immediate = {
            "ticker": "NVDA",
            "alert_type": "price_below",
            "target_value": target_trigger_immediate
        }
        create_immediate_resp = await client.post(f"{BASE_URL}/alerts/", json=payload_immediate, headers=headers)
        print(f"  Immediate alert creation status: {create_immediate_resp.status_code}")
        alert_immediate_data = create_immediate_resp.json()
        alert_immediate_id = alert_immediate_data["id"]
        print(f"  Created Immediate Alert: ID={alert_immediate_id}, Type={alert_immediate_data['alert_type']}, Target=${alert_immediate_data['target_value']}")

        payload_no_trigger = {
            "stock_id": str(nvda_id),
            "alert_type": "price_above",
            "target_value": target_no_trigger
        }
        create_no_trigger_resp = await client.post(f"{BASE_URL}/alerts/", json=payload_no_trigger, headers=headers)
        print(f"  No-trigger alert creation status: {create_no_trigger_resp.status_code}")
        alert_no_trigger_data = create_no_trigger_resp.json()
        alert_no_trigger_id = alert_no_trigger_data["id"]
        print(f"  Created No-Trigger Alert: ID={alert_no_trigger_id}, Type={alert_no_trigger_data['alert_type']}, Target=${alert_no_trigger_data['target_value']}")

        # B. List Alerts
        print("\n[B] GET /v1/alerts/ (List User Alerts)")
        list_resp = await client.get(f"{BASE_URL}/alerts/", headers=headers)
        print(f"  List alerts status: {list_resp.status_code}")
        alerts_list = list_resp.json()
        print(f"  Total Alerts found: {len(alerts_list)}")
        assert len(alerts_list) == 2, "Should list exactly 2 alerts"

        # C. Get Alert by ID
        print("\n[C] GET /v1/alerts/{id} (Get Alert Details)")
        get_resp = await client.get(f"{BASE_URL}/alerts/{alert_immediate_id}", headers=headers)
        print(f"  Get alert status: {get_resp.status_code}")
        alert_detail = get_resp.json()
        assert alert_detail["id"] == alert_immediate_id
        print(f"  Retrieved details for alert {alert_immediate_id}: Type={alert_detail['alert_type']}, Target=${alert_detail['target_value']}")

        print_section("3. Alert Evaluation Endpoints")
        
        # A. Trigger Alert Evaluation
        print("\n[A] POST /v1/alerts/evaluate/{symbol} (Evaluate NVDA Alerts)")
        eval_resp = await client.post(f"{BASE_URL}/alerts/evaluate/NVDA", headers=headers)
        print(f"  Evaluate NVDA alerts status: {eval_resp.status_code}")
        eval_results = eval_resp.json()
        
        print("  Evaluation Results:")
        for r in eval_results:
            print(f"    - Alert ID={r['alert_id']}, Type={r['alert_type']}, Target={r['target_value']}, Current={r['current_value']}, Triggered={r['triggered']}, Message: {r['message']}")
            if r["alert_id"] == alert_immediate_id:
                assert r["triggered"] is True, "Immediate alert should be triggered!"
            elif r["alert_id"] == alert_no_trigger_id:
                assert r["triggered"] is False, "No-trigger alert should NOT be triggered!"

        # B. Check Triggered Alert status in Database via GET
        print("\n[B] GET /v1/alerts/{id} (Check trigger state updates)")
        get_immediate_resp = await client.get(f"{BASE_URL}/alerts/{alert_immediate_id}", headers=headers)
        get_immediate_data = get_immediate_resp.json()
        print(f"  Immediate Alert is_triggered = {get_immediate_data['is_triggered']}")
        assert get_immediate_data["is_triggered"] is True, "Alert should show is_triggered=True in DB"

        get_no_trigger_resp = await client.get(f"{BASE_URL}/alerts/{alert_no_trigger_id}", headers=headers)
        get_no_trigger_data = get_no_trigger_resp.json()
        print(f"  No-trigger Alert is_triggered = {get_no_trigger_data['is_triggered']}")
        assert get_no_trigger_data["is_triggered"] is False, "Alert should show is_triggered=False in DB"

        print_section("4. Alert Deletion and Clean-up")
        
        # Delete alerts
        print("\n[A] DELETE /v1/alerts/{id} (Delete Alert 1)")
        del_1_resp = await client.delete(f"{BASE_URL}/alerts/{alert_immediate_id}", headers=headers)
        print(f"  Delete immediate alert status: {del_1_resp.status_code}")
        assert del_1_resp.status_code == 204

        print("\n[B] DELETE /v1/alerts/{id} (Delete Alert 2)")
        del_2_resp = await client.delete(f"{BASE_URL}/alerts/{alert_no_trigger_id}", headers=headers)
        print(f"  Delete no-trigger alert status: {del_2_resp.status_code}")
        assert del_2_resp.status_code == 204

        # Verify List is empty
        print("\n[C] GET /v1/alerts/ (Verify Alerts are deleted)")
        final_list_resp = await client.get(f"{BASE_URL}/alerts/", headers=headers)
        final_list = final_list_resp.json()
        print(f"  Alerts count after deletion: {len(final_list)}")
        assert len(final_list) == 0

        # Clean up database test user
        print_section("5. Database Clean-up")
        async with async_session() as session:
            # Delete user record which cascades to alerts (if any were left, but they are deleted)
            await session.execute(delete(User).where(User.email == email))
            await session.commit()
            print(f" -> Cleaned up test user {email} successfully.")

    await engine.dispose()
    print("\nALL ALERTS API INTEGRATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_alerts_test())
