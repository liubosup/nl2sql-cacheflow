from dataclasses import dataclass, field


@dataclass(slots=True)
class CacheSettings:
    top_k: int = 5
    similarity_threshold: float = 0.77
    enable_equivalence_check: bool = False


@dataclass(slots=True)
class RetrievalSettings:
    top_k: int = 6


@dataclass(slots=True)
class AppSettings:
    cache: CacheSettings = field(default_factory=CacheSettings)
    retrieval: RetrievalSettings = field(default_factory=RetrievalSettings)
    default_dialect: str = "sqlite"
