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
            # Extract version numbers like 5-5, 4-5, or 3-5 (but NOT YYYYMMDD date suffixes)
            # Match major-minor pattern but not 8-digit years
            version_match = re.search(r'(\d+)-(\d+)(?!-?\d{6})', model_id)
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


def complete(system: str, user: str, fast: bool = False, max_tokens: int = 2000, db=None, actor_name: str = "ai_agent") -> str | None:
    """Call LLM with optional audit logging. Pass db to log the call."""
    if not available():
        return None
    try:
        models = _select_models()
        model_id = models["fast"] if fast else models["reasoning"]
        
        # Log LLM call to audit (no secrets, just metadata)
        if db:
            from jarvis.work.transition import log as audit_log
            from jarvis.work.roles import actor
            audit_log(db, actor(actor_name), "llm_call", f"model:{model_id}", 
                     f"LLM call: {system[:100]}...", evidence=[{"user_prompt_length": len(user), "max_tokens": max_tokens}])
        
        msg = client().messages.create(
            model=model_id, max_tokens=max_tokens,
            system=system, messages=[{"role": "user", "content": user}])
        result = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        
        # Log success
        if db and result:
            from jarvis.work.transition import log as audit_log
            from jarvis.work.roles import actor
            audit_log(db, actor(actor_name), "llm_success", f"model:{model_id}", 
                     f"LLM returned {len(result)} chars")
        
        return result
    except Exception as e:
        # Log failure
        if db:
            from jarvis.work.transition import log as audit_log
            from jarvis.work.roles import actor
            audit_log(db, actor(actor_name), "llm_failed", f"model:{models.get('fast' if fast else 'reasoning', 'unknown')}", 
                     f"LLM call failed: {type(e).__name__}: {str(e)[:200]}")
        return None


def complete_json(system: str, user: str, fast: bool = True) -> dict | None:
    out = complete(system + "\nRespond with a single JSON object and nothing else.", user, fast=fast)
    if not out:
        return None
    try:
        start, end = out.index("{"), out.rindex("}") + 1
        return json.loads(out[start:end])
    except Exception:
        return None


def test_live(force_retest: bool = False) -> dict:
    """Test if LLM is actually working with a real call. Returns status dict."""
    global _llm_test_result
    
    if _llm_test_result is not None and not force_retest:
        models = _select_models()
        return {"status": "live" if _llm_test_result else "fallback", "tested": True, "cached": True,
                "models": models if _llm_test_result else None}
    
    if not available():
        # Don't cache no-API-key as permanent failure
        return {"status": "fallback", "tested": True, "reason": "no API key", "cached": False}
    
    try:
        models = _select_models()
        # Test both reasoning and fast models
        reasoning_test = complete("You are a test system.", "Respond with exactly: OK", fast=False, max_tokens=10)
        fast_test = complete("You are a test system.", "Respond with exactly: OK", fast=True, max_tokens=10)
        
        _llm_test_result = (reasoning_test is not None and fast_test is not None)
        if _llm_test_result:
            return {"status": "live", "tested": True, "models": models, "cached": False}
        else:
            # Don't cache API failures forever
            _llm_test_result = None
            return {"status": "fallback", "tested": True, "reason": "API call failed (one or both models)", "cached": False}
    except Exception as e:
        # Don't cache exceptions forever
        _llm_test_result = None
        return {"status": "fallback", "tested": True, "reason": str(e)[:100], "cached": False}
