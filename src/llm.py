"""Groq LLM client — free tier, no credit card needed after signup at console.groq.com"""
from __future__ import annotations
import os
import json
import time
from typing import Optional

_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY not set.\n"
                "1. Sign up free at https://console.groq.com\n"
                "2. Create an API key (no credit card needed)\n"
                "3. Copy .env.example -> .env and paste your key"
            )
        _client = Groq(api_key=api_key)
    return _client


def llm_json(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama-3.3-70b-versatile",
    retries: int = 2,
) -> Optional[dict]:
    """Call Groq and return parsed JSON. Returns None on failure."""
    for attempt in range(retries):
        try:
            client = _get_client()
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.05,
                max_tokens=4096,
            )
            return json.loads(resp.choices[0].message.content)
        except json.JSONDecodeError as e:
            print(f"[LLM] JSON parse error (attempt {attempt+1}): {e}")
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() and attempt < retries - 1:
                print(f"[LLM] Rate limited — waiting 60s before retry...")
                time.sleep(60)
            else:
                print(f"[LLM] Error (attempt {attempt+1}): {err}")
    return None


def llm_text(
    system_prompt: str,
    user_prompt: str,
    model: str = "llama-3.3-70b-versatile",
) -> Optional[str]:
    """Call Groq and return plain text response."""
    try:
        client = _get_client()
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.05,
            max_tokens=2048,
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return None
