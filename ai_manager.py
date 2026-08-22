from typing import List
import logging
import time

from ai_base import AIConfig, AIServiceBase, AIServiceError
from ai_chat_completions import ChatCompletionsService
from ai_responses import ResponsesService


logger = logging.getLogger(__name__)

SERVICE_TYPES = {
    "chat_completions": ChatCompletionsService,
    "responses": ResponsesService,
}


class AIServiceManager:
    """設定順にAI候補を試し、失敗時に次候補へフォールバックする。"""

    def __init__(self, services: List[AIServiceBase]):
        self.services = services
        if not services:
            raise ValueError("少なくとも1つのAIサービスが必要です")

    @classmethod
    def from_configs(cls, configs: List[AIConfig]) -> "AIServiceManager":
        services = []
        for config in configs:
            service_type = SERVICE_TYPES.get(config.api_type)
            if service_type is None:
                raise ValueError(f"{config.id}: 未対応のAPI形式です: {config.api_type}")
            services.append(service_type(config))
        return cls(services)

    def generate_summary(self, title: str, content: str, prompt_template: str) -> str:
        errors = []
        for index, service in enumerate(self.services):
            label = self._label(service)
            try:
                logger.info("%sで要約生成を試行中...", label)
                start_time = time.time()
                summary = service.generate_summary(title, content, prompt_template)
                elapsed = time.time() - start_time
                logger.info(
                    "%sで要約生成完了: %s... (%.1f秒)",
                    label,
                    title[:50],
                    elapsed,
                )
                logger.debug("要約結果: %s...", summary[:100])

                if errors:
                    fallback_chain = " → ".join(
                        self._format_error(name, reason, code)
                        for name, reason, code in errors
                    )
                    logger.info("フォールバック経緯: %s → %s: 成功", fallback_chain, label)
                return summary
            except AIServiceError as error:
                status_info = f" (HTTP {error.status_code})" if error.status_code else ""
                errors.append((label, error.category_label, error.status_code))
                logger.error(
                    "%s: %s%s - %s",
                    label,
                    error.category_label,
                    status_info,
                    error,
                )
            except Exception as error:
                errors.append((label, "不明なエラー", None))
                logger.error("%sでエラー: %s", label, error)

            if index < len(self.services) - 1:
                logger.warning("次のAI候補に切り替えます...")

        error_summary = ", ".join(
            self._format_error(name, reason, code)
            for name, reason, code in errors
        )
        raise AIServiceError(
            f"すべてのAI候補で要約生成に失敗: {error_summary}",
            error_category=AIServiceError.UNKNOWN,
        )

    def get_status(self) -> dict:
        return {
            service.config.id: {
                "provider": service.config.provider,
                "model": service.config.model,
                "api": service.config.api_type,
                "available": service.is_available(),
                "priority": priority,
            }
            for priority, service in enumerate(self.services, 1)
        }

    @staticmethod
    def _label(service: AIServiceBase) -> str:
        config = service.config
        return (
            f"{config.id} "
            f"(provider={config.provider}, model={config.model}, api={config.api_type})"
        )

    @staticmethod
    def _format_error(name: str, reason: str, code: int | None) -> str:
        return f"{name}: {reason}" + (f" (HTTP {code})" if code else "")
