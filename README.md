# CodeContext - AI 기반 코드 검색 엔진

<div align="center">

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)
[![CI](https://github.com/junyeong-ai/codecontext/actions/workflows/ci.yml/badge.svg)](https://github.com/junyeong-ai/codecontext/actions)
[![Coverage](https://codecov.io/gh/junyeong-ai/codecontext/graph/badge.svg)](https://codecov.io/gh/junyeong-ai/codecontext)

[English](README.en.md) | **한국어**

</div>

> **하이브리드 검색 (75% 의미론 + 25% 키워드) + Tree-sitter AST 파싱 + 벡터 임베딩**

대규모 코드베이스에서 **"이 기능 어디있지?"**, **"이거 수정하면 어디 영향가지?"** 같은 질문에 즉시 답을 얻으세요.

---

## 빠른 시작 (3단계)

### 1. 설치

```bash
# Qdrant 서버 시작
docker compose -f docker-compose.qdrant.yml up -d

# CodeContext 설치
./scripts/install.sh
```

### 2. 인덱싱

```bash
cd your-project
codecontext index
```

### 3. 검색

```bash
codecontext search "user authentication logic"
```

**결과**:
```
1. AuthService.authenticate (score: 0.94)
   Type: method | Language: python | Lines: 45-89
   File: src/services/auth_service.py

2. login_required decorator (score: 0.87)
   Type: function | Language: python | Lines: 12-23
   File: src/middleware/auth.py
```

---

## 핵심 기능

### 🎯 Architecture-First 검색

- **Class 우선 표시**: 아키텍처 이해를 위해 구현(Class)이 인터페이스보다 우선
- **LOC 기반 복잡도**: 대규모 컴포넌트가 소규모 헬퍼보다 높은 순위
- **Graph Expansion**: 관련 심볼 자동 확장 (호출 관계, 상속 등)

### ⚡ 하이브리드 검색

- **70% 의미론적 매칭**: Instruction-based embeddings (Jina Code Embeddings)
- **30% 키워드 매칭**: BM25F sparse vector (camelCase/snake_case 분리)
- **RRF Fusion**: Reciprocal Rank Fusion으로 결과 통합

### 🧬 LoRA 파인튜닝 지원

- **도메인 특화 임베딩**: LoRA adapter로 특정 도메인 코드에 최적화
- **간편한 통합**: adapter 경로만 설정하면 자동 적용
- **안정적 동작**: PEFT 라이브러리 없어도 base model로 동작

### 🌐 다중 언어 지원

Python, Kotlin, Java, JavaScript, TypeScript, Markdown 지원

### 🔍 관계 기반 검색

12가지 관계 타입 (6쌍의 양방향):
- CALLS/CALLED_BY, EXTENDS/EXTENDED_BY, IMPLEMENTS/IMPLEMENTED_BY
- REFERENCES/REFERENCED_BY, CONTAINS/CONTAINED_BY, IMPORTS/IMPORTED_BY

---

## 왜 CodeContext인가?

**높은 정확도**: 키워드 노이즈 감소 + 의미론적 이해 + 관계 기반 확장으로 false positive 최소화

**대규모 확장성**: 6000+ 파일 프로젝트에서 검증, 증분 인덱싱으로 10-100배 빠른 업데이트

**완전한 커스터마이징**: 타입/필드 가중치, 검색 알고리즘, LoRA 파인튜닝까지 프로젝트에 맞게 조정

**성능**: 검색 <500ms | 인덱싱 ~1000 파일/분 | 메모리 <2GB

---

## 설치 요구사항

- Python 3.13+
- Docker (Qdrant)
- UV (자동 설치됨)

---

## 설정

프로젝트 루트에 `.codecontext.toml` 생성 (선택사항, 기본값으로 동작):

```toml
[storage.qdrant]
url = "http://localhost:6333"  # Docker Qdrant

[embeddings.huggingface]
device = "cpu"  # or "cuda", "mps"
# lora_adapter_path = "~/.codecontext/adapters/my-domain"  # Optional
```

고급 설정 (타입 가중치, 필드 가중치, 검색 알고리즘): [scripts/README.md](scripts/README.md)

---

## 사용 예시

### 자연어 검색
```bash
codecontext search "payment gateway integration"
```

### 코드 검색
```bash
codecontext search "class UserService"
```

### 확장 정보 보기
```bash
codecontext search "order processing" --expand relationships
```

### LoRA 파인튜닝 사용
```bash
# 1. LoRA adapter 준비 (adapter_config.json + adapter_model.safetensors)
# 2. 설정 파일에 경로 추가
codecontext index  # 파인튜닝된 임베딩 사용
codecontext search "domain-specific query"
```

자세한 내용은 [scripts/README.md](scripts/README.md#lora-fine-tuning-support) 참조.

---

## 아키텍처

**모듈 구조**: CLI + Core + Pluggable Providers (Storage, Embeddings)

**검색 파이프라인 (5단계)**: Query Embedding → Hybrid Search (70%:30%) → Graph Expansion → Boosting+Weight → Diversity

자세한 설계: [docs/architecture.md](docs/architecture.md) | [docs/hybrid-search.md](docs/hybrid-search.md)

---

## 개발

```bash
./scripts/dev-install.sh  # 개발 환경 설정
pytest                     # 테스트
```

개발 가이드: [CLAUDE.md](CLAUDE.md) (AI Agent) | [docs/](docs/) (Architecture)

---

## 라이선스

MIT License - [LICENSE](LICENSE) 참조

---

## 기여

기여는 언제나 환영합니다! Issue나 Pull Request를 남겨주세요.

---

**Made with ❤️ by CodeContext Team**
