import unittest

from ai_settings import (
    load_ai_configs,
    load_ai_configs_from_dict,
)


class AISettingsTests(unittest.TestCase):
    def test_example_config_is_valid_without_remote_api_keys(self):
        configs = load_ai_configs(
            "ai_config.example.json",
            "system",
            environ={},
        )

        self.assertEqual(["ollama-local"], [item.id for item in configs])
        self.assertEqual("responses", configs[0].api_type)

    def test_loads_fallbacks_in_declared_order_and_skips_missing_key(self):
        document = {
            "providers": {
                "missing": {
                    "base_url": "https://missing.example/v1",
                    "auth": {
                        "type": "bearer",
                        "api_key_env": "MISSING_API_KEY",
                    },
                },
                "local": {
                    "base_url": "http://localhost:11434/v1",
                    "auth": {"type": "none"},
                },
            },
            "fallbacks": [
                {
                    "id": "disabled",
                    "provider": "missing",
                    "model": "remote-model",
                    "api": "responses",
                },
                {
                    "id": "local-first",
                    "provider": "local",
                    "model": "model-a",
                    "api": "responses",
                },
                {
                    "id": "local-second",
                    "provider": "local",
                    "model": "model-b",
                    "api": "chat_completions",
                },
            ],
        }

        configs = load_ai_configs_from_dict(document, "system", environ={})

        self.assertEqual(["local-first", "local-second"], [item.id for item in configs])
        self.assertEqual("system", configs[0].system_prompt)
        self.assertEqual("responses", configs[0].api_type)

    def test_rejects_reserved_protocol_parameters(self):
        document = {
            "providers": {
                "local": {
                    "base_url": "http://localhost:11434/v1",
                    "auth": {"type": "none"},
                }
            },
            "fallbacks": [
                {
                    "id": "invalid",
                    "provider": "local",
                    "model": "model",
                    "api": "responses",
                    "parameters": {"input": "override"},
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "予約済み"):
            load_ai_configs_from_dict(document, "", environ={})

    def test_requires_config_file(self):
        with self.assertRaisesRegex(ValueError, "AI設定ファイル"):
            load_ai_configs("missing-ai-config.json", "system", environ={})


if __name__ == "__main__":
    unittest.main()
