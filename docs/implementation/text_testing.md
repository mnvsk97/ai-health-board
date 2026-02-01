# Text Testing (Local + Frontend)

This guide shows how to trigger a text test case against the intake agent, either via script or from a frontend.

## 1) Start the local server

From the repo root:

```
python3 -m uvicorn ai_health_board.agents.server:app --host 0.0.0.0 --port 7860
```

If you use a virtualenv:

```
.venv/bin/python -m uvicorn ai_health_board.agents.server:app --host 0.0.0.0 --port 7860
```

## 2) Run a scripted test case

Default 6-turn test:

```
scripts/run_local_text_test.py --turns 6
```

Custom test case file (JSON list of user messages):

```
scripts/run_local_text_test.py --case-file ./data/my_text_case.json --turns 10 --session-id demo_case
```

Example `data/my_text_case.json`:

```
[
  "Hi, I need help with a health issue.",
  "I have chest pressure and shortness of breath.",
  "I'm 54 with high blood pressure."
]
```

## 3) Trigger from a frontend

Call the `/message` endpoint and keep a local `messages` array per session.

Endpoint:

```
POST http://127.0.0.1:7860/message
```

Request body:

```
{
  "agent_type": "intake",
  "session_id": "frontend_session_123",
  "message": "I've had chest pain for an hour.",
  "messages": [
    {"role": "system", "content": "You are the intake agent..."},
    {"role": "user", "content": "Hi, I need help."},
    {"role": "assistant", "content": "Hello! Is it okay if I collect some info?"}
  ]
}
```

Response body:

```
{
  "text": "...assistant reply...",
  "messages": [ ...updated history... ]
}
```

Frontend usage pattern:
- Keep `messages` in app state.
- For each user input, POST with the latest `messages`.
- Replace local `messages` with the response `messages`.

## Notes
- The server expects `session_id` + `message`.
- Avoid sending `tool` role messages; the backend filters them for safety.
