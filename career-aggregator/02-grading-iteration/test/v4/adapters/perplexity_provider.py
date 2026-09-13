import time
from ports.grading_provider import IGradingProvider
from exceptions import LLMProviderError
from config import RETRY_ATTEMPTS, RETRY_BASE_DELAY
from perplexity import Perplexity

class PerplexityProvider(IGradingProvider):
    def __init__(self, api_key: str, model: str = "sonar-pro"):
        self.client = Perplexity(api_key=api_key)
        self.model = model

    def grade(self, user_content: str) -> str:
        for attempt in range(RETRY_ATTEMPTS):
            try:
                completion = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": user_content}]
                )
                return completion.choices[0].message.content
            except Exception as e:
                if "429" in str(e) or "rate" in str(e).lower():
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    time.sleep(delay)
                    continue
                raise LLMProviderError(str(e))
        raise LLMProviderError("Max retries exceeded")
