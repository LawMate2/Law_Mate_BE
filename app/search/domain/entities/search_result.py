from dataclasses import dataclass
from typing import List


@dataclass
class SearchResult:
    """검색 결과 도메인 엔티티"""
    contexts: List[str]
    similarity_scores: List[float]
    retrieved_chunks: int
    search_time: float
    embedding_time: float

    @property
    def combined_context(self) -> str:
        """검색된 컨텍스트들을 결합"""
        return "\n\n".join(self.contexts)

    @property
    def max_similarity_score(self) -> float:
        """최고 유사도 점수"""
        return max(self.similarity_scores) if self.similarity_scores else 0.0

    @property
    def avg_similarity_score(self) -> float:
        """평균 유사도 점수"""
        return sum(self.similarity_scores) / len(self.similarity_scores) if self.similarity_scores else 0.0

    @property
    def has_results(self) -> bool:
        """검색 결과가 있는지 확인"""
        return len(self.contexts) > 0

    @property
    def total_search_time(self) -> float:
        """전체 검색 시간"""
        return self.search_time + self.embedding_time

    @classmethod
    def empty_result(cls) -> "SearchResult":
        """빈 검색 결과 생성"""
        return cls(
            contexts=[],
            similarity_scores=[],
            retrieved_chunks=0,
            search_time=0.0,
            embedding_time=0.0
        )