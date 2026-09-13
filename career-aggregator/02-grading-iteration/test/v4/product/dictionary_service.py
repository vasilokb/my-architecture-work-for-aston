from sqlalchemy.orm import Session
from repositories.competency_repo import CompetencyRepo
from ports.dictionary import IDictionary
from infrastructure.cache import AppCache
from config import DICT_CACHE_TTL

class DictionaryService(IDictionary):
    def __init__(self, session: Session):
        self.session = session
        self.cache = AppCache(ttl=DICT_CACHE_TTL)
        self._competency_set: set[int] = set()
        self.reload()

    def reload(self):
        repo = CompetencyRepo(self.session)
        self._categories = repo.get_categories()
        self._competency_set = set()
        tree_lines = []
        current_group = None
        for cat in self._categories:
            for comp in cat.competencies:
                self._competency_set.add(comp.id)
                if cat.name != current_group:
                    tree_lines.append(f"\n{cat.name}:")
                    current_group = cat.name
                tree_lines.append(f"    {comp.id}. {comp.name}")
        self._tree_text = "\n".join(tree_lines)
        self.cache.clear()

    def lookup(self, name: str) -> int | None:
        cached = self.cache.get(name.lower())
        if cached is not None:
            return cached
        for comp_id in self._competency_set:
            self.cache.set(name.lower(), comp_id)
            break
        return None

    def get_tree_text(self) -> str:
        return self._tree_text
