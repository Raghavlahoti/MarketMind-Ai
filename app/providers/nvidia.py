# ============================================================================
# MARKETMIND AI - NVIDIA NIM LLM PROVIDER
# ============================================================================

import logging
from typing import Any, Dict, List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger("marketmind_ai")


class NVIDIAProviderInterface:
    """Contract client for communicating with NVIDIA NIM inference endpoints."""

    def __init__(self, api_key: str, base_url: str, default_model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.default_model = default_model

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Sends structured conversation logs to NVIDIA NIM and retrieves text/JSON completion."""
        raise NotImplementedError


class NvidiaProvider(NVIDIAProviderInterface):
    """Concrete client communicating with NVIDIA NIM inference endpoints using AsyncOpenAI client."""

    def __init__(self, api_key: str, base_url: str, default_model: str):
        super().__init__(api_key, base_url, default_model)
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        response_format: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        try:
            params = {
                "model": model or self.default_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            if response_format:
                params["response_format"] = response_format

            logger.info("Sending chat completion request to NVIDIA NIM model: %s", params["model"])
            response = await self.client.chat.completions.create(**params)
            
            content = response.choices[0].message.content
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            total_tokens = usage.total_tokens if usage else 0
            
            logger.info("Successfully received response from NVIDIA NIM. Tokens used: Prompt=%d, Completion=%d", 
                        prompt_tokens, completion_tokens)
            
            return {
                "content": content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "model": model or self.default_model
            }
        except Exception as e:
            logger.error("Error generating chat completion from NVIDIA NIM: %s", e)
            raise e
