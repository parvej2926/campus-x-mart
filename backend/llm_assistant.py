import requests

from settings import settings


class LLMAssistant:
    def __init__(self, api_key: str = None, model: str = None, provider: str = None, base_url: str = None):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.provider = provider or settings.LLM_PROVIDER
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or ("gpt-4o-mini" if self.provider == "openai" else settings.OLLAMA_MODEL)

    def is_available(self):
        return bool(self.api_key) if self.provider == "openai" else True

    def ask(self, prompt: str):
        if self.provider == "openai" and not self.api_key:
            return {
                "reply": (
                    "OpenAI is not configured. Select the local Ollama provider or configure an API key."
                ),
                "model": "rule-based-fallback",
            }

        if self.provider == "ollama":
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=(3, 120),
            )
            if response.status_code >= 400:
                raise RuntimeError(f"Ollama request failed: {response.text}")
            payload = response.json()
            reply = payload.get("message", {}).get("content")
            if not reply:
                raise RuntimeError("Ollama returned an empty response.")
            return {"reply": reply, "model": self.model}

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
            timeout=20,
        )

        if response.status_code >= 400:
            raise RuntimeError(f"LLM request failed: {response.text}")

        payload = response.json()
        reply = payload["choices"][0]["message"]["content"]
        return {"reply": reply, "model": self.model}
