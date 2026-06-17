import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_NIM_BASE_URL")
    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    
    try:
        models = await client.models.list()
        print("Available NVIDIA NIM models:")
        for model in models.data:
            print(f"- {model.id}")
    except Exception as e:
        print("Error listing models:", e)

if __name__ == "__main__":
    asyncio.run(main())
