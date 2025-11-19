from dataclasses import dataclass
from typing import List
import numpy as np


@dataclass(frozen=True)
class EmbeddingResult:
    """임베딩 결과 값 객체"""
    embedding: List[float]
    text: str
    generation_time: float

    @property
    def dimension(self) -> int:
        return len(self.embedding)

    @property
    def text_length(self) -> int:
        return len(self.text)

    def as_numpy_array(self) -> np.ndarray:
        """numpy 배열로 변환"""
        return np.array(self.embedding, dtype=np.float32)

    def normalize(self) -> "EmbeddingResult":
        """정규화된 임베딩 반환"""
        embedding_array = self.as_numpy_array()
        normalized = embedding_array / np.linalg.norm(embedding_array)
        return EmbeddingResult(
            embedding=normalized.tolist(),
            text=self.text,
            generation_time=self.generation_time
        )

    @property
    def norm(self) -> float:
        """벡터의 노름 계산"""
        return float(np.linalg.norm(self.as_numpy_array()))