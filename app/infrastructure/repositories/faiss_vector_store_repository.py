import os
import json
import time
from typing import List
import faiss
import numpy as np
from openai import OpenAI

from ...domain.entities.search_result import SearchResult
from ...domain.value_objects.document_chunk import DocumentChunk
from ...domain.value_objects.embedding_result import EmbeddingResult
from ...domain.repositories.vector_store_repository import VectorStoreRepository


class FAISSVectorStoreRepository(VectorStoreRepository):
    """FAISS를 사용한 벡터 저장소 구현"""

    def __init__(self, faiss_db_path: str, openai_api_key: str, dimension: int = 1536):
        self.faiss_db_path = faiss_db_path
        self.openai_client = OpenAI(api_key=openai_api_key)
        self.dimension = dimension

        self.index_path = os.path.join(faiss_db_path, "faiss_index.bin")
        self.metadata_path = os.path.join(faiss_db_path, "metadata.json")

        # 디렉토리 생성
        os.makedirs(faiss_db_path, exist_ok=True)

        # FAISS 인덱스 로드 또는 생성
        self._load_or_create_index()

        # 메타데이터 로드 또는 생성
        self._load_or_create_metadata()

    def _load_or_create_index(self):
        """FAISS 인덱스를 로드하거나 새로 생성"""
        if os.path.exists(self.index_path):
            self.index = faiss.read_index(self.index_path)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)

    def _load_or_create_metadata(self):
        """메타데이터를 로드하거나 새로 생성"""
        if os.path.exists(self.metadata_path):
            with open(self.metadata_path, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                'documents': [],
                'sources': [],
                'chunk_ids': [],
                'pages': []
            }

    def _save_index(self):
        """FAISS 인덱스 저장"""
        faiss.write_index(self.index, self.index_path)

    def _save_metadata(self):
        """메타데이터 저장"""
        with open(self.metadata_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """텍스트 임베딩 생성"""
        start_time = time.time()

        response = self.openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )

        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        # 코사인 유사도를 위해 벡터 정규화
        embedding = embedding / np.linalg.norm(embedding)

        generation_time = time.time() - start_time

        return EmbeddingResult(
            embedding=embedding.tolist(),
            text=text,
            generation_time=generation_time
        )

    async def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """문서 청크들을 벡터 저장소에 추가"""
        try:
            embeddings = []

            for chunk in chunks:
                embedding_result = await self.generate_embedding(chunk.content)
                embeddings.append(embedding_result.as_numpy_array())

                # 메타데이터 저장
                self.metadata['documents'].append(chunk.content)
                self.metadata['sources'].append(chunk.source)
                self.metadata['chunk_ids'].append(chunk.chunk_id)
                self.metadata['pages'].append(chunk.page)

            # FAISS 인덱스에 임베딩 추가
            if embeddings:
                embeddings_array = np.vstack(embeddings)
                self.index.add(embeddings_array)

                # 인덱스와 메타데이터 저장
                self._save_index()
                self._save_metadata()

            return True

        except Exception as e:
            print(f"문서 추가 중 오류: {e}")
            return False

    async def search_similar(self, query: str, k: int = 3) -> SearchResult:
        """유사한 문서 검색"""
        search_start_time = time.time()

        try:
            if self.index.ntotal == 0:
                return SearchResult.empty_result()

            # 쿼리 임베딩 생성
            embedding_result = await self.generate_embedding(query)
            query_embedding = embedding_result.as_numpy_array().reshape(1, -1)

            # 유사한 문서 검색
            actual_k = min(k, self.index.ntotal)
            scores, indices = self.index.search(query_embedding, actual_k)

            search_time = time.time() - search_start_time

            # 검색 결과를 컨텍스트로 결합
            contexts = []
            similarity_scores = []

            for i, idx in enumerate(indices[0]):
                if idx < len(self.metadata['documents']):
                    contexts.append(self.metadata['documents'][idx])
                    similarity_scores.append(float(scores[0][i]))

            return SearchResult(
                contexts=contexts,
                similarity_scores=similarity_scores,
                retrieved_chunks=len(contexts),
                search_time=search_time - embedding_result.generation_time,
                embedding_time=embedding_result.generation_time
            )

        except Exception as e:
            print(f"검색 중 오류: {e}")
            return SearchResult.empty_result()

    async def delete_documents(self, document_id: str) -> bool:
        """문서 삭제"""
        try:
            # 삭제할 대상 찾기
            indices_to_remove = []
            for i, source in enumerate(self.metadata['sources']):
                if document_id in source or document_id in self.metadata['chunk_ids'][i]:
                    indices_to_remove.append(i)

            if not indices_to_remove:
                return False

            # 메타데이터에서 삭제 (역순으로 삭제하여 인덱스 변화 방지)
            for idx in sorted(indices_to_remove, reverse=True):
                del self.metadata['documents'][idx]
                del self.metadata['sources'][idx]
                del self.metadata['chunk_ids'][idx]
                del self.metadata['pages'][idx]

            # FAISS 인덱스 재구성
            await self._rebuild_index()

            return True

        except Exception as e:
            print(f"문서 삭제 중 오류: {e}")
            return False

    async def _rebuild_index(self):
        """인덱스 재구성"""
        # 새 인덱스 생성
        self.index = faiss.IndexFlatIP(self.dimension)

        if self.metadata['documents']:
            # 모든 문서에 대해 임베딩 재생성
            embeddings = []
            for doc in self.metadata['documents']:
                embedding_result = await self.generate_embedding(doc)
                embeddings.append(embedding_result.as_numpy_array())

            if embeddings:
                embeddings_array = np.vstack(embeddings)
                self.index.add(embeddings_array)

        # 인덱스와 메타데이터 저장
        self._save_index()
        self._save_metadata()

    async def get_document_count(self) -> int:
        """저장된 문서 청크 수"""
        return len(self.metadata['documents'])

    async def list_documents(self) -> List[str]:
        """저장된 문서 목록"""
        return list(set(self.metadata['sources']))

    async def clear_all(self) -> bool:
        """모든 문서 삭제"""
        try:
            self.metadata = {
                'documents': [],
                'sources': [],
                'chunk_ids': [],
                'pages': []
            }

            self.index = faiss.IndexFlatIP(self.dimension)

            self._save_index()
            self._save_metadata()

            return True

        except Exception as e:
            print(f"전체 삭제 중 오류: {e}")
            return False

    async def health_check(self) -> bool:
        """헬스 체크"""
        try:
            # 인덱스가 정상적으로 로드되었는지 확인
            return self.index is not None and isinstance(self.index.ntotal, int)
        except Exception:
            return False