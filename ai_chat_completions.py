import logging

from ai_base import AIServiceBase, AIServiceError


logger = logging.getLogger(__name__)


class ChatCompletionsService(AIServiceBase):
    """OpenAI互換Chat Completions API実装。"""

    endpoint_path = "chat/completions"

    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        messages = []
        if self.config.system_prompt:
            messages.append({"role": "system", "content": self.config.system_prompt})
        messages.append(
            {
                "role": "user",
                "content": prompt_template.format(title=title, content=content),
            }
        )

        payload = {
            **self.config.parameters,
            "model": self.config.model,
            "messages": messages,
            "stream": False,
        }
        result = self._post_json(payload)
        summary = self._extract_text(result)
        output_limit = self.config.parameters.get(
            "max_completion_tokens", self.config.parameters.get("max_tokens")
        )
        self._log_usage(result, output_limit)
        logger.debug("%s: 要約生成成功 (文字数: %d)", self.name, len(summary))
        return summary

    def _extract_text(self, result: dict) -> str:
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices:
            raise self._response_error("choicesがありません")

        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            texts = []
            for part in content:
                if not isinstance(part, dict):
                    continue
                text = part.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())
            if texts:
                return "\n".join(texts)
        raise self._response_error("生成テキストがありません")

    def _response_error(self, reason: str) -> AIServiceError:
        return AIServiceError(
            f"{self.name}: Chat Completionsレスポンスに{reason}",
            service_name=self.name,
            error_category=AIServiceError.RESPONSE_ERROR,
        )
