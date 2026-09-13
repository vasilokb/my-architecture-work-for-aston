from ports.grading_provider import IGradingProvider
from exceptions import LLMProviderError

class QwenProvider(IGradingProvider):
    def __init__(self, api_key: str, model: str = "qwen-plus"):
        self.api_key = api_key
        self.model = model

    def grade(self, user_content: str) -> str:
        raise LLMProviderError("Qwen SDK not configured yet")
