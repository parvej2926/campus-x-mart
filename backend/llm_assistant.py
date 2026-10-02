import requests

from settings import settings

FAQ = [
    (("sell", "list", "post", "upload"),
     "To sell an item, open 'Sell an item', fill in the name, description, price, category and condition, then save. You can also pick a meetup location and add a YouTube link, and add a photo to your listing after saving."),
    (("order", "buy", "purchase", "request"),
     "Open a product and send a purchase request. The seller confirms it (the item is then reserved), you agree on a meetup date, the seller marks it completed, and then you can leave a review."),
    (("verify", "verification", "code", "otp"),
     "Go to 'Account & verification', choose email or phone and request a 6-digit code. It expires in 10 minutes, allows 5 attempts, and can be resent after 60 seconds."),
    (("message", "chat", "contact"),
     "Use 'Messages' to chat with a buyer or seller in real time."),
    (("report", "scam", "fake"),
     "Use the report option on a product. Admins review reports in the moderation queue."),
]
DEFAULT_REPLY = "I can help with selling an item, placing an order, verifying your account, or messaging. Try asking about one of these."


def fallback_reply(prompt: str):
    text = prompt.split("Student:")[-1].lower()
    for keywords, answer in FAQ:
        if any(keyword in text for keyword in keywords):
            return {"reply": answer, "model": "rule-based-fallback"}
    return {"reply": DEFAULT_REPLY, "model": "rule-based-fallback"}


class LLMAssistant:
    def __init__(self, api_key: str = None, model: str = None, provider: str = None, base_url: str = None):
        self.api_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        self.provider = provider or settings.LLM_PROVIDER
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or ("gpt-4o-mini" if self.provider == "openai" else settings.OLLAMA_MODEL)

    def is_available(self):
        return bool(self.api_key) if self.provider == "openai" else True

    def ask(self, prompt: str):
        try:
            result = self._ask_provider(prompt)
        except (requests.RequestException, RuntimeError):
            return fallback_reply(prompt)
        if result.get("model") == "rule-based-fallback":
            return fallback_reply(prompt)
        return result

    def _ask_provider(self, prompt: str):
        if self.provider == "openai" and not self.api_key:
            return {"reply": "OpenAI is not configured.", "model": "rule-based-fallback"}

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