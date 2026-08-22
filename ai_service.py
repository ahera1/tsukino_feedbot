from ai_manager import AIServiceManager
from ai_settings import load_ai_configs


def create_ai_service_manager(
    config_file: str,
    system_prompt: str = "",
) -> AIServiceManager:
    """JSON設定ファイルからAIマネージャーを作成する。"""
    configs = load_ai_configs(
        config_file=config_file,
        system_prompt=system_prompt,
    )
    return AIServiceManager.from_configs(configs)
