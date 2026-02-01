"""Stagehand client for browser automation with Browserbase."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_health_board.config import load_settings

if TYPE_CHECKING:
    from stagehand import Stagehand
    from stagehand.types import Session


class StagehandClient:
    """Client for managing Stagehand browser sessions with Browserbase."""

    def __init__(self, model_name: str = "gpt-4o") -> None:
        """Initialize the Stagehand client.

        Args:
            model_name: The LLM model to use for browser automation.
        """
        self._client: Stagehand | None = None
        self._session: Session | None = None
        self._session_id: str | None = None
        self._settings = load_settings()
        self._model_name = self._settings.get("stagehand_model") or model_name

    def start(self) -> "StagehandClient":
        """Initialize Stagehand client and start a browser session.

        Returns:
            Self for method chaining.
        """
        from stagehand import Stagehand

        api_key = str(self._settings.get("browserbase_api_key") or "")
        project_id = str(self._settings.get("browserbase_project_id") or "")
        model_api_key = str(
            self._settings.get("stagehand_model_api_key")
            or self._settings.get("openai_api_key")
            or ""
        )

        self._client = Stagehand(
            browserbase_api_key=api_key,
            browserbase_project_id=project_id,
            model_api_key=model_api_key,
        )

        # Start a new browser session
        self._session = self._client.sessions.start(model_name=self._model_name)
        self._session_id = self._session.id
        print(f"Started Stagehand session: {self._session_id}")

        return self

    def close(self) -> None:
        """End the browser session and clean up resources."""
        if self._client and self._session_id:
            try:
                self._client.sessions.end(self._session_id)
                print(f"Ended Stagehand session: {self._session_id}")
            except Exception as e:
                print(f"Error ending session: {e}")
            finally:
                self._session_id = None
                self._session = None

        if self._client:
            self._client.close()
            self._client = None

    @property
    def session_id(self) -> str:
        """Get the current session ID."""
        if not self._session_id:
            raise RuntimeError("No active session. Call start() first.")
        return self._session_id

    @property
    def client(self) -> "Stagehand":
        """Get the Stagehand client."""
        if not self._client:
            raise RuntimeError("Client not initialized. Call start() first.")
        return self._client

    def navigate(self, url: str) -> Any:
        """Navigate to a URL.

        Args:
            url: The URL to navigate to.

        Returns:
            Navigation response.
        """
        return self.client.sessions.navigate(self.session_id, url=url)

    def observe(self, instruction: str) -> Any:
        """Observe the page and identify possible actions.

        Args:
            instruction: What to look for on the page.

        Returns:
            Observation response with available actions.
        """
        return self.client.sessions.observe(self.session_id, instruction=instruction)

    def extract(self, instruction: str, schema: dict | None = None) -> Any:
        """Extract structured data from the page.

        Args:
            instruction: What data to extract.
            schema: JSON schema for the extracted data.

        Returns:
            Extracted data.
        """
        kwargs: dict[str, Any] = {"instruction": instruction}
        if schema:
            kwargs["schema"] = schema
        return self.client.sessions.extract(self.session_id, **kwargs)

    def act(self, action: str) -> Any:
        """Perform an action on the page.

        Args:
            action: The action to perform.

        Returns:
            Action response.
        """
        return self.client.sessions.act(self.session_id, input={"action": action})

    def __enter__(self) -> "StagehandClient":
        """Context manager entry."""
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
