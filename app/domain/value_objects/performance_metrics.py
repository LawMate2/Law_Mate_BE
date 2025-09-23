from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class PerformanceMetrics:
    """성능 메트릭 값 객체"""
    retrieve_time: float
    generate_time: float
    total_time: float
    context_length: int
    response_length: int
    similarity_scores: List[float]
    retrieved_chunks: int

    @property
    def retrieval_efficiency(self) -> float:
        """검색 효율성 (청크당 검색 시간)"""
        if self.retrieved_chunks == 0:
            return 0.0
        return self.retrieve_time / self.retrieved_chunks

    @property
    def generation_efficiency(self) -> float:
        """생성 효율성 (글자당 생성 시간)"""
        if self.response_length == 0:
            return 0.0
        return self.generate_time / self.response_length

    @property
    def max_similarity_score(self) -> float:
        """최고 유사도 점수"""
        return max(self.similarity_scores) if self.similarity_scores else 0.0

    @property
    def avg_similarity_score(self) -> float:
        """평균 유사도 점수"""
        return sum(self.similarity_scores) / len(self.similarity_scores) if self.similarity_scores else 0.0

    @property
    def context_utilization_ratio(self) -> float:
        """컨텍스트 활용 비율"""
        if self.context_length == 0:
            return 0.0
        return min(1.0, self.response_length / self.context_length)

    @classmethod
    def create_empty(cls) -> "PerformanceMetrics":
        """빈 성능 메트릭 생성"""
        return cls(
            retrieve_time=0.0,
            generate_time=0.0,
            total_time=0.0,
            context_length=0,
            response_length=0,
            similarity_scores=[],
            retrieved_chunks=0
        )