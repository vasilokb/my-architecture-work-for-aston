from abc import ABC, abstractmethod

class IDictionary(ABC):
    @abstractmethod
    def lookup(self, name: str) -> int | None:
        pass

    @abstractmethod
    def get_tree_text(self) -> str:
        pass

    @abstractmethod
    def reload(self):
        pass
