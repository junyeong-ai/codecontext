# CodeContext - 지능형 코드 검색 엔진

<div align="center">

![Python](https://img.shields.io/badge/python-3.13-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-0.5.0-orange.svg)
![CI](https://github.com/junyeong-ai/codecontext/actions/workflows/ci.yml/badge.svg)
[![Coverage](https://codecov.io/gh/junyeong-ai/codecontext/graph/badge.svg)](https://codecov.io/gh/junyeong-ai/codecontext)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

[English](README.en.md) | **한국어**

</div>

> **AST 구문 분석, 벡터 임베딩, 하이브리드 검색으로 구동되는 차세대 코드 검색**

CodeContext는 여러분의 코드베이스를 검색 가능한 지식 그래프로 변환합니다. Tree-sitter AST 파싱과 벡터 임베딩을 활용하여 코드 구조, 관계, 컨텍스트를 이해하는 자연어 검색을 제공합니다.

---

## 왜 CodeContext인가?

**기존 grep/regex:** 텍스트 패턴 매칭
**CodeContext:** 코드 의미 이해

| 기능 | 설명 |
|------|------|
| 🔍 **하이브리드 검색** | BM25 키워드 매칭 + 벡터 의미론적 검색 |
| 🎯 **정확한 순위** | 8단계 파이프라인 (Translation → Expansion → BM25 → Vector → Fusion → GraphRAG → MMR → Diversity) |
| 🧠 **의미 이해** | "인증 흐름" 같은 자연어 쿼리 지원 |
| 🌍 **다국어 지원** | 200개 언어 자동 번역 (한국어 → 영어 검색 지원) |
| 🔗 **양방향 관계** | 26개 관계 타입으로 코드 구조 완벽 추적 |
| 📚 **문서-코드 링크** | Markdown 문서와 코드 자동 연결 |
| ⚡ **빠른 속도** | Git 기반 증분 색인 |
| 🌐 **다중 언어** | Python, Java, Kotlin, TypeScript, JS 지원 |
| 🤖 **AI 최적화** | JSON 출력 (관계 + 메타데이터 포함) |

---

## 빠른 시작

### 설치

```bash
# Python 3.13, ChromaDB 필요
pip install -e .
chroma run --host localhost --port 8000
```

### 색인

```bash
codecontext index                    # 최초 전체 색인
codecontext index --incremental      # 증분 업데이트
```

### 검색

```bash
codecontext search "드라이버 활성화 로직"
codecontext search "인증 흐름" --language python --format json
codecontext status --verbose
```

---

## 핵심 기능

### 🎯 하이브리드 검색 시스템

**8단계 파이프라인:** 자연어 쿼리 → Translation (200개 언어) → Query Expansion → BM25 Search (5x over-retrieval) → Vector Search (5x) → Adaptive Fusion (40% keyword + 60% semantic) → Graph Expansion (1-hop PPR) → MMR Reranking (75% relevance + 25% diversity) → File Diversity (최대 2 chunks/file) → 최종 결과

**핵심 3가지 설정:**
- `bm25_weight: 0.4` - 키워드/의미론적 균형
- `mmr_lambda: 0.75` - 관련성/다양성 균형
- `max_chunks_per_file: 2` - 파일당 최대 chunk

### 🔗 양방향 관계 그래프

**26개 관계 타입 (13 bidirectional pairs):**

**Code-to-Code (16개 - 8 pairs):**
CALLS ↔ CALLED_BY, REFERENCES ↔ REFERENCED_BY, EXTENDS ↔ EXTENDED_BY, IMPLEMENTS ↔ IMPLEMENTED_BY, CONTAINS ↔ CONTAINED_BY, IMPORTS ↔ IMPORTED_BY, DEPENDS_ON ↔ DEPENDED_BY, ANNOTATES ↔ ANNOTATED_BY

**Document-to-Code (10개 - 5 pairs):**
DOCUMENTS ↔ DOCUMENTED_BY, MENTIONS ↔ MENTIONED_IN, IMPLEMENTS_SPEC ↔ IMPLEMENTED_IN

**자동 생성:** 색인 중 모든 관계 자동 추출 및 양방향 생성

### 📚 문서-코드 자동 링크

Markdown 문서에서 코드 참조를 자동 추출하여 링크 생성:

**지원 패턴:** Backtick 참조 (\`ClassName.method\`), 파일 경로 (path/to/file.py), 클래스/함수 이름

**매칭 신뢰도:** 정확한 이름 1.0, 파일 경로 0.9, Class.method 0.95, 부분 매칭 0.7

### 🌐 다중 언어 지원

**코드 언어:** Python, Kotlin, Java, JavaScript, TypeScript (Tree-sitter AST 파싱)
**설정 파일:** YAML, JSON, Properties
**문서:** Markdown (자동 코드 참조 추출)
**언어별 최적화:** python_optimizer.py, java_optimizer.py, kotlin_optimizer.py, typescript_optimizer.py

### 📊 AI 최적화 JSON 출력

**검색 결과 정보:**
- 코드 위치 및 스니펫
- AST 메타데이터 (복잡도, 라인 수)
- 양방향 관계 (callers, callees, references, referenced_by 등)
- 문서-코드 링크 (documents, documented_by)
- 유사 코드 추천, 영향도 분석

---

## 사용 사례

**CodeContext가 유용한 경우:**
- 대규모 코드베이스에서 특정 기능 구현 위치 찾기
- 자연어로 코드 의미 검색 ("인증 로직", "데이터베이스 연결")
- 함수/클래스 간 관계 추적 (호출, 참조, 상속)
- 다국어 팀 환경 (한국어로 검색, 영어 코드 찾기)
- AI 에이전트에 코드 컨텍스트 제공 (JSON 출력)

**대안과 비교:**
- **grep/ag/rg:** 텍스트 패턴 매칭만 지원, CodeContext는 의미 이해
- **GitHub Code Search:** 웹 기반, CodeContext는 로컬 + 관계 그래프
- **Language Servers (LSP):** IDE 내 단일 파일 분석, CodeContext는 전체 코드베이스 검색

**알려진 제한사항:**
- Python 3.13 필수 (하위 버전 미지원)
- ChromaDB 서버 별도 실행 필요
- 최초 색인 시간: 10,000 파일 8-15분 (GPU 권장)
- 메모리 사용량: 50,000 파일에 4-6GB

---

## 설치

### 필수 요구사항

- Python 3.13
- ChromaDB 서버 (localhost:8000)
- Git 저장소 (증분 색인용, 선택사항)
- 2GB+ 여유 메모리

### 빠른 설치 (10단계)

```bash
# 1. Python 3.13 설치 (asdf 권장)
asdf plugin add python
asdf install python 3.13.2
cd codecontext
echo "python 3.13.2" > .tool-versions

# 2. 가상 환경 생성
~/.asdf/installs/python/3.13.2/bin/python3.13 -m venv venv
source venv/bin/activate

# 3. CodeContext 설치
pip install -e .

# 4. ChromaDB 시작
./scripts/chroma-cli.sh start

# 5. 설치 확인
codecontext version
```

자세한 내용은 [설치 가이드](docs/INSTALLATION.md) 참조.

---

## 사용법

### 색인 명령어

```bash
codecontext index                    # 현재 디렉토리 색인
codecontext index /path/to/project   # 특정 디렉토리
codecontext index --incremental      # 증분 업데이트
codecontext index --force            # 강제 전체 재색인
```

### 검색 명령어

```bash
codecontext search "드라이버 활성화 로직"
codecontext search "인증 흐름" --language python
codecontext search "사용자 등록" --format json  # AI 에이전트용
codecontext search "API 핸들러" --limit 5
```

### 상태 명령어

```bash
codecontext status
codecontext status --verbose
```

---

## 설정

### 계층적 설정 시스템

1. 환경 변수 (`CODECONTEXT_*`)
2. 프로젝트 설정 (`.codecontext.yaml`)
3. 사용자 설정 (`~/.codecontext/config.yaml`)
4. 기본값 (내장)

### 핵심 설정 예시

`.codecontext.yaml`:

```yaml
# 임베딩 설정
embeddings:
  provider: huggingface
  huggingface:
    model_name: "jinaai/jina-code-embeddings-0.5b"
    device: auto
    batch_size: null      # null = auto (cpu:16, mps:64, cuda:128)
    max_length: 32768

# 검색 설정
search:
  bm25_weight: 0.4        # 40% keyword + 60% semantic
  mmr_lambda: 0.75        # 75% relevance + 25% diversity
  max_chunks_per_file: 2
```

전체 설정은 [.codecontext.yaml.example](.codecontext.yaml.example) 참조.

---

## 검색 결과 예시

### 자연어 쿼리: "사용자 인증 로직"

```json
{
  "results": [
    {
      "file": "src/auth/authenticator.py",
      "name": "authenticate_user",
      "type": "function",
      "score": 0.92,
      "snippet": "def authenticate_user(username, password):\n    # JWT 토큰 생성...",
      "relationships": {
        "called_by": ["login_handler", "api_middleware"],
        "calls": ["validate_credentials", "generate_jwt"]
      }
    }
  ]
}
```

---

## 문서

### 사용자용
- [README.md](README.md) - 이 파일 (한글)
- [README.en.md](README.en.md) - English version

### 개발자용
- [CLAUDE.md](CLAUDE.md) - AI agent 개발 참조 (기술 스택, 아키텍처, 개발 가이드)

### 설정
- [.codecontext.yaml.example](.codecontext.yaml.example) - 전체 설정 예시

---

## 문제 해결

### ChromaDB 연결 오류

```bash
./scripts/chroma-cli.sh start
./scripts/chroma-cli.sh status
```

### Python 버전 오류

```bash
python --version  # 3.13.x여야 함
```

### 메모리 문제

```yaml
indexing:
  batch_size: 50
  parallel_workers: 2
```

---

## 지원

- **GitHub:** [https://github.com/junyeong-ai/codecontext](https://github.com/junyeong-ai/codecontext)
- **이슈:** [GitHub Issues](https://github.com/junyeong-ai/codecontext/issues)
- **토론:** [GitHub Discussions](https://github.com/junyeong-ai/codecontext/discussions)

---

## 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 참조

---

**Built with** 🌳 Tree-sitter • 🧠 Jina Code Embeddings • 🗄️ ChromaDB • 🐍 Python 3.13
