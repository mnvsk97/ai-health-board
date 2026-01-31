import os

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    load_dotenv = None


if load_dotenv:
    load_dotenv()


def _get(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def load_settings() -> dict[str, object]:
    return {
        "redis_cloud_url": os.getenv("REDIS_CLOUD_URL", ""),
        "redis_cloud_host": _get("REDIS_CLOUD_HOST"),
        "redis_cloud_port": int(_get("REDIS_CLOUD_PORT")),
        "redis_cloud_password": _get("REDIS_CLOUD_PASSWORD"),
        "wandb_api_key": _get("WANDB_API_KEY"),
        "wandb_entity": os.getenv("WANDB_ENTITY", ""),
        "wandb_project": os.getenv("WANDB_PROJECT", ""),
        "wandb_inference_model": os.getenv("WANDB_INFERENCE_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
        "weave_project": os.getenv("WEAVE_PROJECT", "preclinical-hackathon"),
        "browserbase_api_key": os.getenv("BROWSERBASE_API_KEY", ""),
        "browserbase_project_id": os.getenv("BROWSERBASE_PROJECT_ID", ""),
        "pipecat_cloud_api_key": os.getenv("PIPECAT_CLOUD_API_KEY", ""),
        "pipecat_cloud_project_id": os.getenv("PIPECAT_CLOUD_PROJECT_ID", ""),
        "daily_api_key": os.getenv("DAILY_API_KEY", ""),
        "daily_domain": os.getenv("DAILY_DOMAIN", ""),
        "daily_token": os.getenv("DAILY_TOKEN"),
        "cartesia_api_key": os.getenv("CARTESIA_API_KEY", ""),
        "cartesia_voice_id": os.getenv("CARTESIA_VOICE_ID", ""),
        "target_agent_url": os.getenv("TARGET_AGENT_URL", "http://localhost:7860"),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL"),
        # Embedding configuration (via TrueFoundry gateway)
        "openai_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        "embedding_dimensions": int(os.getenv("EMBEDDING_DIMENSIONS", "3072")),
    }
