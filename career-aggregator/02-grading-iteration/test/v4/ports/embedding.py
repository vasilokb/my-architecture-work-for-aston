from abc import ABC, abstractmethod

class IEmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        pass
