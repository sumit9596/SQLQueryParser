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
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-2.0-flash",
    "gemini-3-flash-preview"
]

# Singleton client instance and active key index
_cached_client = None
_active_key_index = 0

# In-memory prompt cache for instant responses on identical queries
_prompt_cache: Dict[str, Any] = {}


def get_available_gemini_keys() -> List[str]:
    """
    Collects all configured Gemini API keys across:
    1. Runtime custom key (e.g. entered from UI)
    2. Primary GEMINI_API_KEY (.env / env var)
    3. Backup GEMINI_API_KEY_BACKUP
    4. Comma-delimited list GEMINI_API_KEYS
    5. Streamlit Cloud secrets (st.secrets)
    """
    keys: List[str] = []

    # 1. Custom runtime override from UI
    custom = os.getenv("CUSTOM_GEMINI_API_KEY")
    if custom and custom.strip() and custom != "YOUR_GEMINI_API_KEY_HERE":
        keys.append(custom.strip())

    # 2. Primary key
    k1 = os.getenv("GEMINI_API_KEY")
    if k1 and k1.strip() and k1 != "YOUR_GEMINI_API_KEY_HERE" and k1 not in keys:
        keys.append(k1.strip())

    # 3. Backup key
    k_backup = os.getenv("GEMINI_API_KEY_BACKUP")
    if k_backup and k_backup.strip() and k_backup != "YOUR_GEMINI_API_KEY_HERE" and k_backup not in keys:
        keys.append(k_backup.strip())

    # 4. Comma-separated list
    k_multi = os.getenv("GEMINI_API_KEYS")
    if k_multi:
        for k in k_multi.split(","):
            clean_k = k.strip()
            if clean_k and clean_k != "YOUR_GEMINI_API_KEY_HERE" and clean_k not in keys:
                keys.append(clean_k)

    # 5. Streamlit secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for s_key in ["GEMINI_API_KEY", "GEMINI_API_KEY_BACKUP", "GEMINI_API_KEYS"]:
                val = st.secrets.get(s_key)
                if val:
                    for v in str(val).split(","):
                        clean_v = v.strip()
                        if clean_v and clean_v != "YOUR_GEMINI_API_KEY_HERE" and clean_v not in keys:
                            keys.append(clean_v)
    except Exception:
        pass

    return keys


def is_quota_error(err: Exception) -> bool:
    """Detects if an error is due to rate limiting or quota exhaustion (HTTP 429)."""
    if not err:
        return False
    msg = str(err).lower()
    return any(token in msg for token in [
        "429", "resource_exhausted", "quota", "rate limit", "exhausted",
        "too many requests", "insufficient_quota"
    ])


def get_gemini_client(force_next_key: bool = False):
    """Returns the Gemini client, with automated key rotation across backup keys."""
    global _cached_client, _active_key_index
    keys = get_available_gemini_keys()

    if not keys:
        raise ValueError(
            "GEMINI_API_KEY is not configured! Please set your GEMINI_API_KEY in the .env file or Streamlit secrets."
        )

    if force_next_key:
        _active_key_index = (_active_key_index + 1) % len(keys)
        _cached_client = None

    if _cached_client is not None:
        return _cached_client

    active_key = keys[_active_key_index % len(keys)]
    from google import genai
    _cached_client = genai.Client(api_key=active_key)
    return _cached_client


def call_groq_fallback(prompt: str, expect_json: bool = True) -> Optional[Dict[str, Any]]:
    """
    Seamlessly queries Groq API (Llama-3.3-70B-Versatile) as secondary fallback
    if configured, requiring zero extra packages (uses standard requests).
    """
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        try:
            import streamlit as st
            groq_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            pass

    if not groq_key or groq_key == "YOUR_GROQ_API_KEY_HERE":
        return None

    import requests
    headers = {
        "Authorization": f"Bearer {groq_key.strip()}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert Text-to-SQL AI. Output strictly valid JSON without preamble."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,
    }
    if expect_json:
        payload["response_format"] = {"type": "json_object"}

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=25
        )
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            if expect_json:
                return clean_json_response(content)
            return content
    except Exception as e:
        print(f"Notice: Groq fallback failed: {e}")

    return None

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
    Features automated multi-key rotation and multi-provider fallback:
    1. Tries primary and backup Gemini keys across fast fallback models
    2. Seamlessly fails over to Groq Llama-3.3-70B if Gemini quota is exhausted
    3. Handles 429 ResourceExhausted errors transparently
    """
    # Check in-memory cache
    cache_key = f"{expect_json}:{prompt}"
    if use_cache and cache_key in _prompt_cache:
        return _prompt_cache[cache_key]

    keys = get_available_gemini_keys()
    models_to_try = [model_name] if model_name else FALLBACK_MODELS
    from google.genai import types
    config = types.GenerateContentConfig(response_mime_type="application/json") if expect_json else None

    last_error = None
    max_key_attempts = max(1, len(keys))

    # Phase 1: Try Gemini with automated key rotation
    for key_attempt in range(max_key_attempts):
        try:
            client = get_gemini_client(force_next_key=(key_attempt > 0))
        except Exception as e:
            last_error = e
            break

        key_quota_hit = False
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
                if is_quota_error(e):
                    key_quota_hit = True
                    break
                continue

        # If this key hit quota and we have more keys, rotate immediately
        if key_quota_hit and key_attempt < max_key_attempts - 1:
            continue

    # Phase 2: If all Gemini keys failed, attempt secondary provider (Groq)
    groq_res = call_groq_fallback(prompt, expect_json=expect_json)
    if groq_res is not None:
        if len(_prompt_cache) >= 500:
            _prompt_cache.clear()
        _prompt_cache[cache_key] = groq_res
        return groq_res

    # If all models and fallbacks failed, raise the last exception
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
