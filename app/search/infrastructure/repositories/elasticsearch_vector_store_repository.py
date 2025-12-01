"""Elasticsearch 벡터 저장소 구현"""
import time
from typing import List, Optional

import numpy as np
from elasticsearch import AsyncElasticsearch
from openai import AsyncOpenAI

from app.documents.domain.value_objects.document_chunk import DocumentChunk
from app.search.domain.entities.search_result import SearchResult
from app.search.domain.repositories.vector_store_repository import VectorStoreRepository
from app.search.domain.value_objects.embedding_result import EmbeddingResult


class ElasticsearchVectorStoreRepository(VectorStoreRepository):
    """Elasticsearch를 사용한 벡터 저장소 구현 (FAISS 병행)"""

    def __init__(
        self,
        elasticsearch_host: str,
        elasticsearch_port: int,
        openai_api_key: str,
        embedding_model: str = "text-embedding-3-small",
        dimension: int = 1536,
        index_name: str = "lawmate_documents"
    ):
        self.es = AsyncElasticsearch([f"http://{elasticsearch_host}:{elasticsearch_port}"])
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)
        self.embedding_model = embedding_model
        self.dimension = dimension
        self.index_name = index_name

    async def initialize_index(self):
        """인덱스 생성 (매핑 설정)"""
        if await self.es.indices.exists(index=self.index_name):
            return

        index_mapping = {
            "mappings": {
                "properties": {
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.dimension,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "chunk_id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "page": {"type": "integer"},
                    "created_at": {"type": "date"},
                    "metadata": {"type": "object", "enabled": False}
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        }

        await self.es.indices.create(index=self.index_name, body=index_mapping)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """텍스트 임베딩 생성"""
        start_time = time.time()

        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            embedding_payload: Optional[list] = response.data[0].embedding
            if not embedding_payload:
                raise ValueError("임베딩 응답이 비어 있습니다.")

            embedding = np.array(embedding_payload, dtype=np.float32)
            embedding = embedding / np.linalg.norm(embedding)

            generation_time = time.time() - start_time

            return EmbeddingResult(
                embedding=embedding.tolist(),
                text=text,
                generation_time=generation_time
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI 임베딩 생성 중 오류가 발생했습니다: {exc}") from exc

    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """문서 청크들을 Elasticsearch에 추가"""
        try:
            await self.initialize_index()

            for chunk in chunks:
                # 임베딩 생성
                embedding_result = await self.generate_embedding(chunk.content)

                # Elasticsearch 문서 생성
                doc = {
                    "content": chunk.content,
                    "embedding": embedding_result.embedding,
                    "chunk_id": chunk.chunk_id,
                    "source": chunk.source,
                    "page": chunk.page,
                    "metadata": chunk.metadata
                }

                # 인덱싱
                await self.es.index(
                    index=self.index_name,
                    id=chunk.chunk_id,
                    document=doc
                )

            # 인덱스 리프레시 (즉시 검색 가능하도록)
            await self.es.indices.refresh(index=self.index_name)

            return True

        except Exception as e:
            print(f"Elasticsearch 문서 추가 중 오류: {e}")
            return False

    async def search_similar(self, query: str, k: int = 5) -> SearchResult:
        """쿼리로 유사한 문서 검색 (하이브리드: BM25 + 벡터 검색)"""
        search_start_time = time.time()

        try:
            await self.initialize_index()

            # 쿼리 임베딩 생성
            embedding_result = await self.generate_embedding(query)
            query_vector = embedding_result.embedding

            # 하이브리드 검색 쿼리
            search_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "match": {
                                    "content": {
                                        "query": query,
                                        "boost": 1.0
                                    }
                                }
                            },
                            {
                                "script_score": {
                                    "query": {"match_all": {}},
                                    "script": {
                                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                        "params": {"query_vector": query_vector}
                                    },
                                    "boost": 2.0
                                }
                            }
                        ]
                    }
                },
                "size": k
            }

            response = await self.es.search(index=self.index_name, body=search_query)
            hits = response.get("hits", {}).get("hits", [])

            elapsed = time.time() - search_start_time
            search_time = max(elapsed - embedding_result.generation_time, 0)

            if not hits:
                return SearchResult.empty_result()

            contexts: List[str] = []
            scores: List[float] = []

            for hit in hits:
                source = hit.get("_source", {})
                score = hit.get("_score", 0.0)
                # 기본 컨텍스트는 내용, 메타데이터는 접두로 붙임
                prefix = f"[source: {source.get('source', 'unknown')}, page: {source.get('page', '?')}] "
                contexts.append(prefix + source.get("content", ""))
                scores.append(float(score))

            return SearchResult(
                contexts=contexts,
                similarity_scores=scores,
                retrieved_chunks=len(contexts),
                search_time=search_time,
                embedding_time=embedding_result.generation_time
            )

        except Exception as e:
            print(f"Elasticsearch 검색 중 오류: {e}")
            return SearchResult.empty_result()

    async def delete_documents(self, document_id: str) -> bool:
        """문서 삭제 (source 또는 chunk_id 기준)"""
        try:
            await self.initialize_index()
            query = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"source": document_id}},
                            {"term": {"chunk_id": document_id}}
                        ]
                    }
                }
            }
            response = await self.es.delete_by_query(index=self.index_name, body=query, conflicts="proceed")
            return not response.get("failures")
        except Exception as e:
            print(f"Elasticsearch 문서 삭제 중 오류: {e}")
            return False

    async def get_document_count(self) -> int:
        """저장된 문서 청크 수"""
        try:
            await self.initialize_index()
            count = await self.es.count(index=self.index_name)
            return count.get("count", 0)
        except Exception as e:
            print(f"Elasticsearch 문서 개수 조회 중 오류: {e}")
            return 0

    async def list_documents(self) -> List[str]:
        """저장된 문서 목록 (source 기준 유니크)"""
        try:
            await self.initialize_index()
            body = {
                "size": 0,
                "aggs": {
                    "sources": {
                        "terms": {
                            "field": "source",
                            "size": 1000
                        }
                    }
                }
            }
            response = await self.es.search(index=self.index_name, body=body)
            buckets = response.get("aggregations", {}).get("sources", {}).get("buckets", [])
            return [bucket["key"] for bucket in buckets]
        except Exception as e:
            print(f"Elasticsearch 문서 목록 조회 중 오류: {e}")
            return []

    async def clear_all(self) -> bool:
        """모든 문서 삭제"""
        try:
            await self.initialize_index()
            await self.es.delete_by_query(
                index=self.index_name,
                body={"query": {"match_all": {}}},
                conflicts="proceed",
                refresh=True
            )
            return True
        except Exception as e:
            print(f"Elasticsearch 전체 삭제 중 오류: {e}")
            return False

    async def health_check(self) -> bool:
        """헬스 체크"""
        try:
            health = await self.es.cluster.health()
            return health.get("status") in {"green", "yellow"}
        except Exception:
            return False

    async def get_index_info(self) -> dict:
        """인덱스 정보 조회"""
        try:
            stats = await self.es.indices.stats(index=self.index_name)
            count = await self.es.count(index=self.index_name)

            return {
                "index_name": self.index_name,
                "total_documents": count['count'],
                "index_size": stats['indices'][self.index_name]['total']['store']['size_in_bytes'],
                "status": "healthy"
            }
        except Exception as e:
            return {
                "index_name": self.index_name,
                "error": str(e),
                "status": "error"
            }

    async def close(self):
        """연결 종료"""
        await self.es.close()
