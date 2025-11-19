from app.search.domain.entities.search_result import SearchResult
from app.search.domain.repositories.vector_store_repository import VectorStoreRepository
from app.shared.services.mlflow_tracker import MLflowTracker


class SearchUseCases:
    """검색 관련 유스케이스"""

    def __init__(
        self,
        vector_store_repository: VectorStoreRepository,
        mlflow_tracker: MLflowTracker
    ):
        self.vector_store_repository = vector_store_repository
        self.mlflow_tracker = mlflow_tracker

    async def search_documents(
        self,
        query: str,
        k: int = 3
    ) -> SearchResult:
        """문서 검색"""
        with self.mlflow_tracker.start_run("document_search"):
            # 파라미터 로깅
            await self.mlflow_tracker.log_params({
                "query": query,
                "k": k
            })

            try:
                # 벡터 저장소에서 검색
                search_result = await self.vector_store_repository.search_similar(query, k)

                # 메트릭 로깅
                await self.mlflow_tracker.log_metrics({
                    "search_time": search_result.search_time,
                    "embedding_time": search_result.embedding_time,
                    "total_search_time": search_result.total_search_time,
                    "retrieved_chunks": search_result.retrieved_chunks,
                    "max_similarity_score": search_result.max_similarity_score,
                    "avg_similarity_score": search_result.avg_similarity_score,
                    "context_length": len(search_result.combined_context),
                    "success": 1 if search_result.has_results else 0
                })

                # 검색 결과 아티팩트 저장
                await self.mlflow_tracker.log_text(
                    search_result.combined_context,
                    "search_context.txt"
                )

                return search_result

            except Exception as e:
                await self.mlflow_tracker.log_metric("success", 0)
                await self.mlflow_tracker.log_text(str(e), "search_error.txt")

                # 빈 결과 반환
                return SearchResult.empty_result()

    async def get_search_statistics(self) -> dict:
        """검색 통계"""
        document_count = await self.vector_store_repository.get_document_count()
        document_list = await self.vector_store_repository.list_documents()

        return {
            "total_chunks": document_count,
            "unique_documents": len(set(document_list)),
            "avg_chunks_per_document": document_count / len(set(document_list)) if document_list else 0
        }

    async def health_check(self) -> bool:
        """벡터 저장소 헬스 체크"""
        return await self.vector_store_repository.health_check()
