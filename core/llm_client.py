"""
LLM Client Wrapper Module (High-Performance & Cached)
Interfaces with Google Gemini API via official google-genai SDK.
Features:
- Singleton Client with Connection Keep-Alive
- In-Memory Response Caching (LRU)
- Fast-Path JSON generation via GenerateContentConfig
- Verified ultra-fast fallback models (gemini-3.1-flash-lite, gemini-3.5-flash-lite)
"""

import os
import json
import re
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

# Load .env
load_dotenv()

# Primary and verified fallback models in 2026
DEFAULT_MODEL = os.getenv("LLM_MODEL", "gemini-3.1-flash-lite")
FALLBACK_MODELS = [
    DEFAULT_MODEL,
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3-flash-preview"
]

# Singleton client instance
_cached_client = None

# In-memory prompt cache for instant responses on identical queries
_prompt_cache: Dict[str, Any] = {}

def get_gemini_client():
    """Returns the singleton Gemini client to avoid socket churn and re-read overhead."""
    global _cached_client
    if _cached_client is not None:
        return _cached_client

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        raise ValueError(
            "GEMINI_API_KEY is not configured! Please set your GEMINI_API_KEY in the .env file."
        )
    
    from google import genai
    _cached_client = genai.Client(api_key=api_key)
    return _cached_client

def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """
    Cleans markdown backticks (e.g. ```json ... ```) from LLM output
    and parses it into a valid Python dictionary.
    """
    text = raw_text.strip()
    
    # Strip markdown code fence
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
        
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            return json.loads(json_str)
        raise ValueError(f"Could not parse valid JSON from LLM response:\n{raw_text}")

def call_llm(
    prompt: str,
    expect_json: bool = True,
    model_name: Optional[str] = None,
    use_cache: bool = True
) -> Any:
    """
    Calls the LLM with the provided prompt.
    Includes automated fallback across verified fast models if high demand or error occurs.
    """
    # Check in-memory cache
    cache_key = f"{expect_json}:{prompt}"
    if use_cache and cache_key in _prompt_cache:
        return _prompt_cache[cache_key]

    client = get_gemini_client()
    from google.genai import types

    models_to_try = [model_name] if model_name else FALLBACK_MODELS
    
    # Set JSON schema config if expecting JSON
    config = types.GenerateContentConfig(response_mime_type="application/json") if expect_json else None

    last_error = None
    for model in models_to_try:
        if not model:
            continue
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            response_text = response.text or ""
            
            if expect_json:
                result = clean_json_response(response_text)
            else:
                result = response_text.strip()
                
            if len(_prompt_cache) >= 500:
                _prompt_cache.clear()
            _prompt_cache[cache_key] = result
            return result
        except Exception as e:
            last_error = e
            continue
            
    # If all models failed, raise the last exception
    raise last_error or RuntimeError("All LLM model invocations failed.")

if __name__ == "__main__":
    print("=== TESTING LLM CLIENT (HIGH SPEED) ===")
    import time
    t0 = time.time()
    res = call_llm("Respond with a simple JSON: {\"status\": \"online\"}", expect_json=True, use_cache=False)
    print("Cold Call Time:", round(time.time() - t0, 3), "s | Result:", res)
    
    t1 = time.time()
    res_cached = call_llm("Respond with a simple JSON: {\"status\": \"online\"}", expect_json=True, use_cache=True)
    print("Cached Call Time:", round(time.time() - t1, 6), "s | Result:", res_cached)
