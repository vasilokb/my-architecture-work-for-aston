from ports.grading_provider import IGradingProvider
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL

def create_provider(name: str | None = None) -> IGradingProvider:
    provider = name or LLM_PROVIDER
    if provider == "perplexity":
        from adapters.perplexity_provider import PerplexityProvider
        return PerplexityProvider(api_key=LLM_API_KEY, model=LLM_MODEL)
    elif provider == "qwen":
        from adapters.qwen_provider import QwenProvider
        return QwenProvider(api_key=LLM_API_KEY)
    else:
        raise ValueError(f"Unknown provider: {provider}")
