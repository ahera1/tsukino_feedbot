import logging

from ai_base import AIServiceBase, AIServiceError


logger = logging.getLogger(__name__)


class ResponsesService(AIServiceBase):
    """OpenAI互換Responses API実装。"""

    endpoint_path = "responses"

    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        payload = {
            **self.config.parameters,
            "model": self.config.model,
            "input": prompt_template.format(title=title, content=content),
            "stream": False,
        }
        if self.config.system_prompt:
            payload["instructions"] = self.config.system_prompt

        result = self._post_json(payload)
        self._raise_for_response_status(result)
        summary = self._extract_text(result)
        self._log_usage(result, self.config.parameters.get("max_output_tokens"))
        logger.debug("%s: 要約生成成功 (文字数: %d)", self.name, len(summary))
        return summary

    def _raise_for_response_status(self, result: dict) -> None:
        error = result.get("error")
        if isinstance(error, dict) and error:
            message = error.get("message", "APIが失敗を返しました")
            raise AIServiceError(
                f"{self.name}: Responses APIエラー: {message}",
                service_name=self.name,
                error_category=AIServiceError.RESPONSE_ERROR,
            )
        status = result.get("status")
        if status in {"failed", "cancelled", "incomplete"}:
            reason = result.get("incomplete_details") or status
            raise AIServiceError(
                f"{self.name}: Responses APIの状態が{status}: {reason}",
                service_name=self.name,
                error_category=AIServiceError.RESPONSE_ERROR,
            )

    def _extract_text(self, result: dict) -> str:
        output_text = result.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        texts = []
        output = result.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                item_content = item.get("content")
                if not isinstance(item_content, list):
                    continue
                for part in item_content:
                    if not isinstance(part, dict) or part.get("type") != "output_text":
                        continue
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        texts.append(text.strip())
        if texts:
            return "\n".join(texts)
        raise AIServiceError(
            f"{self.name}: Responses APIレスポンスに生成テキストがありません",
            service_name=self.name,
            error_category=AIServiceError.RESPONSE_ERROR,
        )
