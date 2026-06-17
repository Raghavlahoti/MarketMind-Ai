# ============================================================================
# MARKETMIND AI - AUTHENTICATION FLOW TESTER
# ============================================================================

import asyncio
import uuid
import httpx
from jose import jwt
from app.core.config import settings


async def run_auth_test() -> None:
    # 1. Generate unique registration data
    email = f"test.analyst.{uuid.uuid4().hex[:6]}@marketmind.ai"
    password = "securePassword123!"
    first_name = "Test"
    last_name = "User"
    
    register_payload = {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name
    }
    
    base_url = "http://127.0.0.1:8000/v1"
    
    async with httpx.AsyncClient() as client:
        print("======================================================================")
        print("1. RUNNING: POST /auth/register")
        print(f"Request Payload:\n{register_payload}\n")
        
        reg_response = await client.post(f"{base_url}/auth/register", json=register_payload)
        print(f"Response Status: {reg_response.status_code}")
        print(f"Response Body:\n{reg_response.json()}\n")
        
        if reg_response.status_code != 201:
            print("[ERROR] Registration failed. Exiting test.")
            return

        print("======================================================================")
        print("2. RUNNING: POST /auth/login")
        login_payload = {
            "email": email,
            "password": password
        }
        print(f"Request Payload:\n{login_payload}\n")
        
        login_response = await client.post(f"{base_url}/auth/login", json=login_payload)
        print(f"Response Status: {login_response.status_code}")
        print(f"Response Body:\n{login_response.json()}\n")
        
        if login_response.status_code != 200:
            print("[ERROR] Login failed. Exiting test.")
            return
            
        token_data = login_response.json()
        token = token_data["access_token"]

        print("======================================================================")
        print("3. VERIFYING JWT ACCESS TOKEN LOCAL SIGNATURE")
        try:
            payload = jwt.decode(
                token, 
                settings.JWT_SECRET_KEY, 
                algorithms=[settings.JWT_ALGORITHM]
            )
            print("  -> Signature: VALID (Decoded using settings.JWT_SECRET_KEY)")
            print(f"  -> Decoded Claims Payload:\n{payload}\n")
        except Exception as e:
            print(f"  -> Signature: INVALID ({e})")
            return

        print("======================================================================")
        print("4. RUNNING: GET /auth/me")
        headers = {"Authorization": f"Bearer {token}"}
        print(f"Request Headers:\n{headers}\n")
        
        me_response = await client.get(f"{base_url}/auth/me", headers=headers)
        print(f"Response Status: {me_response.status_code}")
        print(f"Response Body:\n{me_response.json()}\n")
        print("======================================================================")


if __name__ == "__main__":
    asyncio.run(run_auth_test())
