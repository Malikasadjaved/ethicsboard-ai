"""LLM Utilities — Reusable completion wrappers with robust retries and backoff.
"""

import asyncio
from typing import List, Dict, Any

async def call_llm_with_retry(
    client: Any,
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 15.0,
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    **kwargs: Any
) -> Any:
    """Call ChatCompletions.create with strict timeout and exponential backoff.
    
    Args:
        client: The AsyncOpenAI client instance.
        model: The model string.
        messages: The chat messages.
        timeout: Time limit for each attempt in seconds.
        max_retries: Total number of retry attempts before raising exception.
        backoff_factor: Multiplier for exponential backoff delay.
        **kwargs: Additional parameters passed to completion create.
    """
    delay = 1.5
    for attempt in range(max_retries):
        try:
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **kwargs
                ),
                timeout=timeout
            )
            return response
        except Exception as e:
            print(f"[LLM Retry] Attempt {attempt + 1}/{max_retries} failed for model {model}: {e}")
            if attempt == max_retries - 1:
                # Re-raise the exception on the final attempt
                raise e
            await asyncio.sleep(delay)
            delay *= backoff_factor
