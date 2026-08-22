import unittest
from unittest.mock import Mock

from ai_base import AIConfig, AIServiceError
from ai_manager import AIServiceManager


def config(target_id, api_type):
    return AIConfig(
        id=target_id,
        provider="provider",
        model="model",
        api_type=api_type,
        base_url="https://example.com/v1",
        auth_type="none",
    )


class AIManagerTests(unittest.TestCase):
    def test_falls_back_in_declared_order(self):
        manager = AIServiceManager.from_configs(
            [config("first", "responses"), config("second", "chat_completions")]
        )
        manager.services[0].generate_summary = Mock(
            side_effect=AIServiceError(
                "failed",
                service_name="first",
                error_category=AIServiceError.SERVER_ERROR,
            )
        )
        manager.services[1].generate_summary = Mock(return_value="summary")

        result = manager.generate_summary("title", "content", "{content}")

        self.assertEqual("summary", result)
        manager.services[0].generate_summary.assert_called_once()
        manager.services[1].generate_summary.assert_called_once()

    def test_status_keeps_duplicate_provider_targets(self):
        manager = AIServiceManager.from_configs(
            [config("model-a", "responses"), config("model-b", "responses")]
        )

        status = manager.get_status()

        self.assertEqual(["model-a", "model-b"], list(status))
        self.assertEqual(1, status["model-a"]["priority"])
        self.assertEqual(2, status["model-b"]["priority"])


if __name__ == "__main__":
    unittest.main()
