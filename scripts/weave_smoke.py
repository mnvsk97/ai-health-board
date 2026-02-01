from __future__ import annotations

import os

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

from ai_health_board.observability import init_weave, trace_op, trace_attrs
from ai_health_board.wandb_inference import inference_chat, get_default_model


@trace_op("smoke.weave_inference")
def main() -> None:
    if load_dotenv:
        load_dotenv()
    if not os.getenv("WANDB_API_KEY"):
        raise SystemExit("WANDB_API_KEY is required")

    init_weave()
    with trace_attrs({"smoke": True}):
        response = inference_chat(
            get_default_model(),
            [{"role": "user", "content": "Respond with the single word: ok"}],
            temperature=0,
            max_tokens=5,
        )
    print(response.strip())


if __name__ == "__main__":
    main()
