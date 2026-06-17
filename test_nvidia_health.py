# ============================================================================
# MARKETMIND AI - NVIDIA NIM HEALTH CHECKER
# ============================================================================

import asyncio
import sys
from openai import AsyncOpenAI
from app.core.config import settings


async def run_health_check():
    print("="*80)
    print(" Running NVIDIA NIM Health Check ")
    print("="*80)
    print(f"Base URL: {settings.NVIDIA_NIM_BASE_URL}")
    print(f"Configured Model: {settings.NVIDIA_LLM_MODEL}")
    print(f"API Key Present: {bool(settings.NVIDIA_API_KEY)}")
    print("-"*80)

    try:
        client = AsyncOpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url=settings.NVIDIA_NIM_BASE_URL
        )

        # 1. List available models
        print("1. Listing available models from NVIDIA integrate API...")
        models_response = await client.models.list()
        available_models = [m.id for m in models_response.data]
        
        print(f"Found {len(available_models)} available models:")
        for idx, model_id in enumerate(sorted(available_models)):
            print(f"  {idx + 1:02d}. {model_id}")
            
        print("-"*80)

        # 2. Check if configured model exists
        print("2. Checking if configured model exists in the list...")
        if settings.NVIDIA_LLM_MODEL in available_models:
            print(f"SUCCESS: Configured model '{settings.NVIDIA_LLM_MODEL}' exists in the available models list.")
        else:
            print(f"WARNING: Configured model '{settings.NVIDIA_LLM_MODEL}' was NOT found in the list.")
            print("Please choose one of the available models listed above.")

        print("-"*80)

        # 3. Simple chat completion test
        print("3. Testing chat completion with prompt: 'Respond with the word SUCCESS'...")
        completion = await client.chat.completions.create(
            model=settings.NVIDIA_LLM_MODEL,
            messages=[{"role": "user", "content": "Respond with the word SUCCESS"}],
            temperature=0.0,
            max_tokens=10
        )
        
        response_text = completion.choices[0].message.content.strip()
        print(f"Response Received: '{response_text}'")
        if "SUCCESS" in response_text.upper():
            print("SUCCESS: Chat completion test passed successfully!")
        else:
            print(f"FAILURE: Received unexpected response: '{response_text}'")

    except Exception as e:
        print(f"ERROR: Health check encountered an exception: {e}")
        sys.exit(1)

    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_health_check())
