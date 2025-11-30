# CodeContext

<div align="center">

[![Python](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)](https://github.com/junyeong-ai/codecontext/releases)

🌐 [English](README.en.md) | **한국어**

</div>

> **"이 기능 어디있지?" "수정하면 어디 영향가지?"** — 대규모 코드베이스에서 즉시 답을 얻으세요.

**하이브리드 검색** (70% 의미론 + 30% 키워드) | **AST 파싱** | **관계 그래프**

---

## 시작하기

```bash
# 1. Qdrant 시작
docker compose -f docker-compose.qdrant.yml up -d

# 2. 설치
./scripts/install.sh

# 3. 인덱싱 & 검색
cd your-project
codecontext index
codecontext search "user authentication"
```

---

## 왜 CodeContext인가?

| 문제 | CodeContext 해결책 |
|------|-------------------|
| grep은 의미를 모른다 | 의미론적 검색 + 키워드 매칭 |
| IDE 검색은 관계를 못 본다 | 12가지 코드 관계 추적 (호출, 상속, 참조 등) |
| 대규모 코드베이스에서 길을 잃는다 | Architecture-first 검색 (구현 > 인터페이스) |

**성능**: 검색 <500ms | 6000+ 파일 프로젝트 검증 | 증분 인덱싱

---

## 핵심 기능

### 하이브리드 검색
```bash
codecontext search "payment processing"
```
- **70% 의미론**: "결제 처리" → PaymentService, checkout, billing 모두 찾음
- **30% 키워드**: 정확한 함수명, 클래스명 매칭

### 관계 탐색
```bash
codecontext search "authenticate" --expand relationships --format json
```
```json
{
  "callers": [{"name": "login", "type": "method", "file": "src/auth.py", "line": 42}],
  "callees": [{"name": "validate_token", "type": "function", "file": "src/token.py", "line": 15}]
}
```

### 지원 언어
Python, Java, Kotlin, TypeScript, JavaScript, Markdown

---

## 설정

`.codecontext.toml` (선택사항):

```toml
[storage.qdrant]
url = "http://localhost:6333"

[embeddings.huggingface]
device = "cpu"  # cuda, mps
```

---

## 요구사항

- Python 3.13+
- Docker (Qdrant)

---

## 링크

- [아키텍처](docs/architecture.md)
- [개발 가이드](CLAUDE.md)
- [라이선스](LICENSE) (MIT)

---

**Made with ❤️ by CodeContext Team**
