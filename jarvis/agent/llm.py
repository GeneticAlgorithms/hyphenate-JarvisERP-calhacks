"""Optional Claude layer. JarvisERP works without a key (deterministic templates); with a key, Claude
writes the narration, plays the personas, defends decisions under questioning and parses free-text
scenarios. Claude never produces a number that the code does not recompute."""
from __future__ import annotations

import json
import re

from jarvis import config

_client = None
_llm_test_result = None  # cache: None = not tested, True = live, False = failed
_selected_models = None  # cache: {"fast": model_id, "reasoning": model_id}


def available() -> bool:
    import os
    llm_env = os.getenv("JARVIS_LLM", "").lower()
    if llm_env in ("off", "false", "0", "no"):
        return False
    return bool(config.ANTHROPIC_API_KEY)


def _select_models() -> dict[str, str]:
    """Query Anthropic API for available models and pick newest Sonnet/Haiku.
    
    Env vars JARVIS_MODEL_REASONING and JARVIS_MODEL_FAST override selection.
    Verified working models: claude-sonnet-4-5, claude-haiku-4-5
    """
    global _selected_models
    if _selected_models is not None:
        return _selected_models
    
    # Check for env var overrides first
    import os
    env_reasoning = os.getenv("JARVIS_MODEL_REASONING")
    env_fast = os.getenv("JARVIS_MODEL_FAST")
    
    # Fallback to configured models
    fallback = {"fast": config.MODEL_FAST, "reasoning": config.MODEL_REASONING}
    
    # If both env vars are set, use them and skip API query
    if env_reasoning and env_fast:
        _selected_models = {"reasoning": env_reasoning, "fast": env_fast}
        return _selected_models
    
    if not available():
        _selected_models = fallback
        return _selected_models
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, base_url=config.ANTHROPIC_URL)
        models_response = client.models.list()
        
        # Extract model IDs
        available_models = [m.id for m in models_response.data if hasattr(m, 'id')]
        
        # Find best sonnet (reasoning) and haiku (fast) by family name
        # Handle all naming schemes: claude-sonnet-4-5, claude-sonnet-5-5, claude-3-5-sonnet-YYYYMMDD
        sonnet_pattern = re.compile(r'claude.*sonnet', re.IGNORECASE)
        haiku_pattern = re.compile(r'claude.*haiku', re.IGNORECASE)
        
        # Filter by family
        sonnets = [m for m in available_models if sonnet_pattern.search(m)]
        haikus = [m for m in available_models if haiku_pattern.search(m)]
        
        # Sort: prefer higher version numbers (5-5 > 4-5 > 3-5), then dates if present
        def model_sort_key(model_id: str) -> tuple:
            # Extract version numbers like 5-5, 4-5, or 3-5
            version_match = re.search(r'(\d+)[-.]\s*(\d+)', model_id)
            if version_match:
                major, minor = int(version_match.group(1)), int(version_match.group(2))
            else:
                major, minor = 0, 0
            # Extract date if present (YYYYMMDD at end)
            date_match = re.search(r'(\d{8})$', model_id)
            date = int(date_match.group(1)) if date_match else 0
            return (major, minor, date)
        
        sonnets.sort(key=model_sort_key, reverse=True)
        haikus.sort(key=model_sort_key, reverse=True)
        
        # Use env var override if provided, else use discovered model, else fallback
        _selected_models = {
            "reasoning": env_reasoning or (sonnets[0] if sonnets else fallback["reasoning"]),
            "fast": env_fast or (haikus[0] if haikus else fallback["fast"])
        }
        
    except Exception as e:
        # Fall back to configured models on any error
        _selected_models = {
            "reasoning": env_reasoning or fallback["reasoning"],
            "fast": env_fast or fallback["fast"]
        }
    
    return _selected_models


def client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, base_url=config.ANTHROPIC_URL)
    return _client


def complete(system: str, user: str, fast: bool = False, max_tokens: int = 2000, timeout: float | None = None) -> str | None:
    if not available():
        return None
    try:
        models = _select_models()
        model_id = models["fast"] if fast else models["reasoning"]
        
        # Create kwargs for client call
        kwargs = {
            "model": model_id,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}]
        }
        
        # Add timeout if specified
        if timeout is not None:
            kwargs["timeout"] = timeout
        
        msg = client().messages.create(**kwargs)
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    except Exception as e:  # network / quota / timeout - fall back to templates
        return None


def complete_json(system: str, user: str, fast: bool = True, timeout: float | None = None) -> dict | None:
    """Complete with JSON response. Returns dict on success, None on failure."""
    out = complete(system + "\nRespond with a single JSON object and nothing else.", user, fast=fast, timeout=timeout)
    if not out:
        return None
    try:
        start, end = out.index("{"), out.rindex("}") + 1
        return json.loads(out[start:end])
    except Exception:
        return None


def test_live() -> dict:
    """Test if LLM is actually working with a real call. Returns status dict."""
    global _llm_test_result
    
    if _llm_test_result is not None:
        models = _select_models()
        return {"status": "live" if _llm_test_result else "fallback", "tested": True, "cached": True,
                "models": models if _llm_test_result else None}
    
    if not available():
        _llm_test_result = False
        import os
        llm_env = os.getenv("JARVIS_LLM", "").lower()
        if llm_env in ("off", "false", "0", "no"):
            reason = "LLM disabled (JARVIS_LLM=off)"
        else:
            reason = "no API key"
        return {"status": "fallback", "tested": True, "reason": reason, "cached": False}
    
    try:
        models = _select_models()
        result = complete("You are a test system.", "Respond with exactly: OK", fast=True, max_tokens=10)
        _llm_test_result = (result is not None)
        if _llm_test_result:
            return {"status": "live", "tested": True, "models": models, "cached": False}
        else:
            return {"status": "fallback", "tested": True, "reason": "API call failed", "cached": False}
    except Exception as e:
        _llm_test_result = False
        return {"status": "fallback", "tested": True, "reason": str(e)[:100], "cached": False}
