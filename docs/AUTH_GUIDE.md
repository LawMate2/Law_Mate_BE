# 인증 가이드

## 개요

이 프로젝트는 Google OAuth와 개발용 로그인을 지원합니다.

## 로그인 방법

### 1. 개발용 로그인 (권장: 개발 환경)

프론트엔드 없이 빠르게 테스트할 수 있는 로그인 방식입니다.

**엔드포인트:** `POST /auth/dev/login`

**요청:**
```json
{
  "email": "test@example.com",
  "name": "테스터"
}
```

**응답:**
```json
{
  "user": {
    "id": 1,
    "email": "test@example.com",
    "name": "테스터",
    "verified_email": true,
    "last_login_at": "2024-01-01T00:00:00Z"
  },
  "access_token": "dev-token-test@example.com",
  "is_new_user": true,
  "message": "개발 환경 로그인 (프로덕션에서는 비활성화됨)"
}
```

**cURL 예시:**
```bash
curl -X POST http://localhost:8000/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "name": "테스터"}'
```

**특징:**
- 이메일만으로 로그인 가능
- 사용자가 없으면 자동 생성
- 개발/테스트 환경에서만 사용 가능 (프로덕션에서는 403 에러)
- 토큰 형식: `dev-token-{email}`

### 2. Google OAuth 로그인 (프로덕션)

**엔드포인트:** `POST /auth/google`

**요청:**
```json
{
  "access_token": "google_oauth_access_token"
}
```

**응답:**
```json
{
  "user": { /* 사용자 정보 */ },
  "access_token": "google_oauth_access_token",
  "is_new_user": false
}
```

## 인증이 필요한 API 사용하기

### 1. 토큰 발급
먼저 로그인하여 `access_token`을 받습니다.

### 2. API 호출 시 헤더에 토큰 포함

**Authorization 헤더 형식:**
```
Authorization: Bearer {access_token}
```
또는
```
Authorization: {access_token}
```

**cURL 예시:**
```bash
# 채팅 API 호출 (인증 필요)
curl -X POST http://localhost:8000/chat/sessions/1/messages \
  -H "Authorization: Bearer dev-token-test@example.com" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
```

**JavaScript/React 예시:**
```javascript
const token = "dev-token-test@example.com";

const response = await fetch('http://localhost:8000/chat/sessions/1/messages', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ message: '안녕하세요' })
});
```

## 공개 엔드포인트 (인증 불필요)

다음 엔드포인트들은 인증 없이 접근 가능합니다:

- `GET /` - 루트
- `GET /health` - 헬스 체크
- `GET /architecture` - 아키텍처 정보
- `GET /docs` - API 문서
- `GET /openapi.json` - OpenAPI 스펙
- `GET /redoc` - ReDoc 문서
- `POST /auth/google` - Google 로그인
- `POST /auth/dev/login` - 개발용 로그인

## 컨트롤러에서 인증 사용하기

### 필수 인증

```python
from fastapi import Depends
from app.auth.infrastructure.middleware.auth_middleware import get_current_user
from app.auth.domain.entities.user import User

@router.post("/protected")
async def protected_endpoint(
    current_user: User = Depends(get_current_user)
):
    """인증이 필요한 엔드포인트"""
    return {
        "message": f"안녕하세요, {current_user.name}님!",
        "user_id": current_user.id
    }
```

### 선택적 인증

```python
from typing import Optional
from fastapi import Depends
from app.auth.infrastructure.middleware.auth_middleware import get_current_user_optional
from app.auth.domain.entities.user import User

@router.get("/optional")
async def optional_auth_endpoint(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """인증이 선택적인 엔드포인트"""
    if current_user:
        return {"message": f"환영합니다, {current_user.name}님!"}
    return {"message": "비회원으로 접속하셨습니다."}
```

## 환경 설정

`.env` 파일에서 환경을 설정할 수 있습니다:

```bash
# 개발 환경 (개발용 로그인 활성화)
ENVIRONMENT=development

# 프로덕션 환경 (개발용 로그인 비활성화)
ENVIRONMENT=production
```

가능한 값: `development`, `dev`, `local`, `production`, `prod`

## 보안 고려사항

### 개발 환경
- 개발용 로그인은 편의를 위한 것이므로 프로덕션에서는 절대 사용하지 마세요
- `ENVIRONMENT=production`으로 설정하면 자동으로 비활성화됩니다

### 프로덕션 환경
- Google OAuth만 사용
- HTTPS 필수
- CORS origins를 특정 도메인으로 제한
- 토큰 만료 시간 설정 (향후 구현)

## 테스트 시나리오

### 1. 개발용 로그인으로 전체 플로우 테스트

```bash
# 1. 로그인
TOKEN=$(curl -X POST http://localhost:8000/auth/dev/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com"}' \
  | jq -r '.access_token')

# 2. 채팅 세션 생성 (인증 필요)
SESSION_ID=$(curl -X POST http://localhost:8000/chat/sessions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"metadata": {}}' \
  | jq -r '.id')

# 3. 메시지 전송 (인증 필요)
curl -X POST "http://localhost:8000/chat/sessions/$SESSION_ID/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "안녕하세요"}'
```

## 향후 개선 사항

- [ ] JWT 토큰 도입
- [ ] 토큰 만료 시간 설정
- [ ] Refresh token 구현
- [ ] Role-based access control (RBAC)
- [ ] API rate limiting