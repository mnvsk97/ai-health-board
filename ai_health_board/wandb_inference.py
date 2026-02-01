from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

import httpx

from .config import load_settings
from .observability import init_weave, trace_op, trace_attrs


@lru_cache(maxsize=1)
def _inference_config() -> dict[str, str]:
    settings = load_settings()
    project_header = ""
    entity = str(settings.get("wandb_entity") or "")
    project = str(settings.get("wandb_project") or "")
    weave_project = str(settings.get("weave_project") or "")
    if entity and project:
        project_header = f"{entity}/{project}"
    elif weave_project and "/" in weave_project:
        project_header = weave_project
    return {
        "api_key": str(settings.get("wandb_api_key") or ""),
        "base_url": "https://api.inference.wandb.ai/v1",
        "default_model": str(settings.get("wandb_inference_model") or "meta-llama/Llama-3.1-8B-Instruct"),
        "project_header": project_header,
    }


def get_default_model() -> str:
    return _inference_config()["default_model"]


def _resolve_model(model: str | None) -> str:
    default_model = get_default_model()
    if not model or model.startswith("gpt-"):
        return default_model
    return model


@trace_op("wandb_inference.chat")
def inference_chat(
    model: str | None,
    messages: list[dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 800,
) -> str:
    init_weave()
    cfg = _inference_config()
    resolved_model = _resolve_model(model)
    with trace_attrs({"llm.model": resolved_model, "llm.provider": "wandb_inference"}):
        headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
        if cfg["project_header"]:
            headers["OpenAI-Project"] = cfg["project_header"]
        payload = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{cfg['base_url']}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]


def _extract_json(text: str) -> str:
    """Extract JSON from text that might include markdown code blocks or other content."""
    import re

    # Try to find JSON in code blocks
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Try to find a JSON object or array
    json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if json_match:
        return json_match.group(1).strip()

    # Return as-is and let json.loads fail with a clear error
    return text.strip()


@trace_op("wandb_inference.chat_json")
def inference_chat_json(
    model: str | None,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 800,
) -> Any:
    text = inference_chat(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    json_str = _extract_json(text)
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Log the raw response for debugging
        print(f"Failed to parse JSON from LLM response: {text[:500]}...")
        raise
