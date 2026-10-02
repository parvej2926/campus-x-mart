from unittest.mock import MagicMock

from llm_assistant import LLMAssistant


def test_assistant_uses_local_ollama_by_default(monkeypatch):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {"content": "Try the Products page to browse items."}}
    post = MagicMock(return_value=response)
    monkeypatch.setattr("llm_assistant.requests.post", post)

    result = LLMAssistant().ask("How do I find a book?")

    assert result == {"reply": "Try the Products page to browse items.", "model": "mistral:latest"}
    assert post.call_args.args[0] == "http://localhost:11434/api/chat"
    assert post.call_args.kwargs["json"]["model"] == "mistral:latest"
    assert post.call_args.kwargs["json"]["stream"] is False


def test_assistant_returns_reply_and_model_for_authenticated_user(client, make_user, monkeypatch):
    user = make_user(verified=True)

    class FakeAssistant:
        def ask(self, prompt):
            return {"reply": f"Marketplace help for: {prompt}", "model": "test-model"}

    monkeypatch.setattr("main.LLMAssistant", FakeAssistant)
    response = client.post(
        "/api/assistant/chat",
        headers=user["headers"],
        json={"query": "How do I sell a book?"},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "reply": "Marketplace help for: How do I sell a book?",
        "model": "test-model",
    }


def test_assistant_rejects_blank_prompt(client, auth_headers):
    headers = auth_headers(verified=True)
    response = client.post("/api/assistant/chat", headers=headers, json={"query": " "})
    assert response.status_code == 422


def test_assistant_reports_upstream_failure_without_leaking_provider_error(client, make_user, monkeypatch):
    user = make_user(verified=True)

    class FailingAssistant:
        def ask(self, prompt):
            raise RuntimeError("provider response contained private details")

    monkeypatch.setattr("main.LLMAssistant", FailingAssistant)
    response = client.post(
        "/api/assistant/chat",
        headers=user["headers"],
        json={"query": "Help me list a bicycle."},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "The marketplace assistant is temporarily unavailable. Please try again."
    assert "private details" not in response.text
