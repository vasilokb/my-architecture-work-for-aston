from abc import ABC, abstractmethod

class IGradingProvider(ABC):
    @abstractmethod
    def grade(self, user_content: str) -> str:
        pass
