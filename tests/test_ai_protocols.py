import unittest
from unittest.mock import patch

import requests

from ai_base import AIConfig, AIServiceError
from ai_chat_completions import ChatCompletionsService
from ai_responses import ResponsesService


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

    def json(self):
        return self.data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(response=self)


def make_config(api_type, **overrides):
    values = {
        "id": "target",
        "provider": "provider",
        "model": "model",
        "api_type": api_type,
        "base_url": "https://example.com/v1",
        "api_key": "secret",
        "system_prompt": "system prompt",
        "parameters": {},
        "retry_delay": 0,
    }
    values.update(overrides)
    return AIConfig(**values)


class AIProtocolTests(unittest.TestCase):
    @patch("ai_base.requests.request")
    def test_chat_completions_builds_and_parses_request(self, request):
        request.return_value = FakeResponse(
            {
                "choices": [{"message": {"content": " summary "}}],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 15,
                },
            }
        )
        service = ChatCompletionsService(
            make_config(
                "chat_completions",
                parameters={"max_tokens": 100, "temperature": 0.3},
            )
        )

        result = service.generate_summary("title", "content", "{title}: {content}")

        self.assertEqual("summary", result)
        _, url = request.call_args.args
        payload = request.call_args.kwargs["json"]
        self.assertEqual("https://example.com/v1/chat/completions", url)
        self.assertEqual("system", payload["messages"][0]["role"])
        self.assertEqual("title: content", payload["messages"][1]["content"])
        self.assertFalse(payload["stream"])
        self.assertEqual("Bearer secret", request.call_args.kwargs["headers"]["Authorization"])

    @patch("ai_base.requests.request")
    def test_responses_builds_and_parses_typed_output(self, request):
        request.return_value = FakeResponse(
            {
                "status": "completed",
                "output": [
                    {"type": "reasoning", "content": []},
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": " first "},
                            {"type": "output_text", "text": "second"},
                        ],
                    },
                ],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "total_tokens": 15,
                },
            }
        )
        service = ResponsesService(
            make_config(
                "responses",
                parameters={"max_output_tokens": 100, "store": False},
            )
        )

        result = service.generate_summary("title", "content", "{title}: {content}")

        self.assertEqual("first\nsecond", result)
        _, url = request.call_args.args
        payload = request.call_args.kwargs["json"]
        self.assertEqual("https://example.com/v1/responses", url)
        self.assertEqual("system prompt", payload["instructions"])
        self.assertEqual("title: content", payload["input"])
        self.assertFalse(payload["store"])

    @patch("ai_base.requests.request")
    def test_retries_transient_http_error(self, request):
        request.side_effect = [
            FakeResponse({"error": {"message": "busy"}}, status_code=429),
            FakeResponse({"choices": [{"message": {"content": "ok"}}]}),
        ]
        service = ChatCompletionsService(
            make_config("chat_completions", max_attempts=2)
        )

        self.assertEqual("ok", service.generate_summary("t", "c", "{content}"))
        self.assertEqual(2, request.call_count)

    @patch("ai_base.requests.request")
    def test_empty_responses_output_is_service_error(self, request):
        request.return_value = FakeResponse({"status": "completed", "output": []})
        service = ResponsesService(make_config("responses"))

        with self.assertRaises(AIServiceError) as context:
            service.generate_summary("t", "c", "{content}")
        self.assertEqual(AIServiceError.RESPONSE_ERROR, context.exception.error_category)


if __name__ == "__main__":
    unittest.main()
