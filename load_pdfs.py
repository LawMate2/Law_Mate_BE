"""PDF 파일을 FAISS 벡터 스토어에 로드하는 스크립트"""
import os
import sys
import asyncio

from app.core.config import settings
from app.documents.application.services.document_processor import LangChainDocumentProcessor
from app.search.infrastructure.repositories.faiss_vector_store_repository import FAISSVectorStoreRepository


async def load_pdfs():
    """PDF 파일들을 벡터 스토어에 로드"""
    processor = LangChainDocumentProcessor()

    # OpenAI API 키가 없으면 에러 메시지 출력
    if not settings.openai_api_key:
        print("❌ OPENAI_API_KEY가 .env 파일에 설정되지 않았습니다.")
        print("   .env 파일에 OPENAI_API_KEY=your_key_here 를 추가해주세요.")
        return

    vector_store = FAISSVectorStoreRepository(
        faiss_db_path=settings.faiss_db_path,
        openai_api_key=settings.openai_api_key,
        embedding_model="text-embedding-3-small",
        dimension=1536
    )

    pdf_dir = settings.upload_dir
    pdf_files = []

    # PDF 파일 찾기
    for root, dirs, files in os.walk(pdf_dir):
        for file in files:
            if file.endswith('.pdf'):
                pdf_files.append(os.path.join(root, file))

    if not pdf_files:
        print(f"❌ {pdf_dir} 디렉토리에 PDF 파일이 없습니다.")
        return

    print(f"📚 찾은 PDF 파일: {len(pdf_files)}개\n")

    total_chunks = 0
    success_count = 0
    fail_count = 0

    # 각 PDF 파일 처리
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] 처리 중: {os.path.basename(pdf_path)}")

        try:
            # PDF를 청크로 분할
            chunks = await processor.process_document(pdf_path)
            print(f"   ✓ 청크 수: {len(chunks)}개")

            # 벡터 스토어에 추가
            success = await vector_store.add_documents(chunks)

            if success:
                print(f"   ✓ 임베딩 추가 성공\n")
                total_chunks += len(chunks)
                success_count += 1
            else:
                print(f"   ✗ 임베딩 추가 실패\n")
                fail_count += 1

        except Exception as e:
            print(f"   ✗ 오류 발생: {e}\n")
            fail_count += 1

    # 최종 결과
    count = await vector_store.get_document_count()

    print("=" * 60)
    print(f"✅ 완료!")
    print(f"   - 성공: {success_count}개")
    print(f"   - 실패: {fail_count}개")
    print(f"   - 총 저장된 청크 수: {count}개")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(load_pdfs())