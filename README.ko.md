# AI 워크플로우 엔진

> **AI 네이티브 워크플로우 관리 시스템** - AI 지원 소프트웨어 개발을 위해 설계된 구조화된 개발 워크플로우 엔진

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 목차

- [개요](#개요)
- [핵심 기능](#핵심-기능)
- [빠른 시작](#빠른-시작)
- [설치](#설치)
- [구성](#구성)
- [명령어 레퍼런스](#명령어-레퍼런스)
- [워크플로우 개념](#워크플로우-개념)
- [AI 어시스턴트와 함께 사용하기](#ai-어시스턴트와-함께-사용하기)
- [튜토리얼](#튜토리얼)
- [예시](#예시)
- [고급 사용법](#고급-사용법)
- [다국어 지원](#다국어-지원)
- [문제 해결](#문제-해결)

---

## 개요

AI 워크플로우 엔진은 구조화된 개발 워크플로우를 강제하는 커맨드라인 도구입니다. Claude, GPT 등의 AI 어시스턴트와 함께 작업할 때 소프트웨어 개발 생명주기 전반에 걸쳐 규율과 일관성을 유지하도록 특별히 설계되었습니다.

### 왜 이 도구를 사용해야 하나요?

복잡한 프로젝트에서 AI 어시스턴트와 작업할 때 여러 문제가 발생합니다:

1. **컨텍스트 손실**: AI 어시스턴트가 세션 간에 프로젝트 상태를 잊어버림
2. **프로세스 건너뛰기**: 리뷰, 테스팅 같은 중요한 단계가 간과됨
3. **문서 표류**: 스펙과 문서가 구현과 맞지 않게 됨
4. **기술 부채 누적**: 체계적인 추적 없이 이슈가 쌓임

AI 워크플로우 엔진은 다음을 통해 이를 해결합니다:

- **스테이지 기반 워크플로우 강제**: 각 스테이지에 필수 체크리스트
- **상태 인식 제공**: AI가 현재 워크플로우 상태를 읽을 수 있음
- **명시적 전이 요구**: 요구사항 완료 없이 스테이지 건너뛰기 불가
- **모든 작업 로깅**: 개발 과정의 완전한 감사 추적

### 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│                        사용자 / AI 에이전트                          │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            CLI 계층                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  workflow/cli.py                                             │   │
│  │  - 인자 파싱 (argparse)                                      │   │
│  │  - 명령어 라우팅 (status, next, check, set 등)               │   │
│  │  - i18n 통합                                                 │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          코어 엔진                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐                  │
│  │  controller.py       │  │  state.py           │                  │
│  │  - 워크플로우 로직   │  │  - 상태 관리        │                  │
│  │  - 스테이지 전이     │  │  - JSON 영속화      │                  │
│  │  - 체크리스트 작업   │  │  - 체크리스트 상태  │                  │
│  └─────────────────────┘  └─────────────────────┘                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         플러그인 계층                                │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │ FileExistsValidator  │  │  CommandValidator    │  [커스텀...]   │
│  └──────────────────────┘  └──────────────────────┘                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 핵심 기능

### 코어 기능

| 기능 | 설명 |
|------|------|
| **스테이지 기반 워크플로우** | 체크리스트와 전이 규칙이 있는 스테이지(M0-M4, P1-P7) 정의 |
| **강제 전이** | 모든 체크리스트 항목 완료 없이 진행 불가 |
| **플러그인 시스템** | 커스텀 조건을 위한 확장 가능한 검증기 |
| **상태 영속화** | 세션 간 JSON 기반 상태 추적 |
| **감사 로깅** | 책임 추적을 위한 모든 작업 로깅 |

### AI 통합 기능

| 기능 | 설명 |
|------|------|
| **Status 명령어** | AI가 세션 시작 시 현재 상태 조회 가능 |
| **USER-APPROVE** | 특정 작업에 사람의 검증 필요 |
| **서브 에이전트 리뷰** | AI 서브 에이전트 리뷰 기록 및 추적 |
| **증거 추적** | 완료 항목에 근거 첨부 |

### 개발자 경험

| 기능 | 설명 |
|------|------|
| **이중 언어 지원** | 완전한 한국어/영어 i18n |
| **대화형 튜토리얼** | 내장 학습 시스템 |
| **쉘 별칭** | 간편한 `flow` 명령어 설정 |
| **YAML 구성** | 사람이 읽기 쉬운 워크플로우 정의 |

---

## 빠른 시작

### 30초 설정

```bash
# 1. 클론 및 설치
git clone https://github.com/your-org/workflow-tool.git
cd workflow-tool
pip install -e .

# 2. 작동 확인
flow --help

# 3. 현재 상태 보기
flow status

# 4. 튜토리얼 시작
flow tutorial
```

### 최소 워크플로우 예시

`workflow.yaml` 생성:

```yaml
version: "2.0"

stages:
  START:
    id: "START"
    label: "프로젝트 시작"
    checklist:
      - "프로젝트 목표 정의"
      - "개발 환경 설정"
    transitions:
      - target: "DEVELOP"

  DEVELOP:
    id: "DEVELOP"
    label: "개발"
    checklist:
      - "코드 작성"
      - "테스트 작성"
      - "테스트 실행"
    transitions:
      - target: "REVIEW"

  REVIEW:
    id: "REVIEW"
    label: "리뷰"
    checklist:
      - "코드 리뷰 완료"
      - "[USER-APPROVE] 머지 승인"
    transitions:
      - target: "DONE"

  DONE:
    id: "DONE"
    label: "완료"
    checklist:
      - "main에 머지"
      - "문서 업데이트"
```

`.workflow/state.json` 생성:

```json
{
  "current_stage": "START",
  "checklist": []
}
```

사용하기:

```bash
flow status           # 현재 스테이지 보기
flow check 1 2        # 항목 완료 표시
flow next             # 다음 스테이지로 이동
```

---

## 설치

### 요구사항

- Python 3.10 이상
- pip (Python 패키지 매니저)

### 방법 1: 소스에서 설치 (개발용 권장)

```bash
# 저장소 클론
git clone https://github.com/your-org/workflow-tool.git
cd workflow-tool

# 가상환경 생성 (권장)
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 편집 가능 모드로 설치
pip install -e .

# 설치 확인
flow --help
```

### 방법 2: 패키지에서 설치

```bash
pip install ai-workflow-engine
```

### 방법 3: 설치 없이 실행

```bash
# 직접 실행
python -m workflow --help

# 또는 별칭 설정
alias flow='python -m workflow'
```

### 쉘 별칭 설정

편리한 접근을 위해 쉘 별칭 설치:

```bash
# 자동 설치
flow install-alias --name flow

# 또는 ~/.bashrc 또는 ~/.zshrc에 수동 추가:
alias flow='python -m workflow'

# 쉘 설정 리로드
source ~/.bashrc  # 또는 ~/.zshrc
```

---

## 구성

### 파일 구조

workflow-tool을 사용하는 일반적인 프로젝트:

```
my-project/
├── workflow.yaml           # 워크플로우 정의 (필수)
├── .workflow/
│   ├── state.json          # 현재 상태 (자동 생성)
│   ├── secret              # USER-APPROVE용 비밀 해시 (gitignore)
│   └── audit.log           # 작업 감사 로그 (gitignore)
├── .memory/                # 프로젝트 지식 (선택)
│   ├── docs/
│   │   └── PROJECT_MANAGEMENT_GUIDE.md
│   └── modules/
│       └── [feature-name]/
│           ├── spec.md
│           └── current.md
└── ... (프로젝트 파일들)
```

### workflow.yaml 레퍼런스

완전한 구성 레퍼런스:

```yaml
# 버전 (필수)
version: "2.0"

# 전역 변수 (선택)
variables:
  project_name: "my-project"
  test_command: "pytest -v"

# 플러그인 등록 (선택)
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"
  shell: "workflow.plugins.shell.CommandValidator"

# 재사용 가능한 조건 세트 (선택)
rulesets:
  all_checked:
    - rule: all_checked
      fail_message: "모든 체크리스트 항목을 먼저 완료하세요"

  tests_pass:
    - rule: shell
      args:
        cmd: "pytest"
        expect_code: 0
      fail_message: "테스트가 통과해야 합니다"

# 스테이지 정의 (필수)
stages:
  M0:
    id: "M0"                          # 고유 식별자
    label: "기술 부채 검토"            # 사람이 읽을 수 있는 이름
    checklist:                        # 완료할 항목들
      - "기존 기술 부채 검토"
      - "부채 항목 우선순위 결정"
      - "[USER-APPROVE] 부채 계획 승인"  # 토큰 필요
    transitions:                      # 여기서 어디로 갈 수 있나?
      - target: "M1"
        conditions:
          - use_ruleset: all_checked  # 룰셋 참조
          - rule: fs                  # 또는 플러그인 직접 사용
            args:
              path: "docs/debt-plan.md"
    on_enter:                         # 스테이지 진입 시 작업 (선택)
      - action: "log"
        args:
          message: "기술 부채 검토 시작"

  M1:
    id: "M1"
    label: "계획"
    # ... 더 많은 스테이지
```

### 환경 변수

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `FLOW_LANG` | 표시 언어 (`en`, `ko`) | 시스템 로케일 |

---

## 명령어 레퍼런스

### `flow status`

현재 워크플로우 상태 표시.

```bash
# 전체 상태 표시
flow status

# 출력:
# Current Stage: M0 (기술 부채 검토)
# ========================================
# Active Module: core-engine
# ----------------------------------------
# 1. [x] 기존 기술 부채 검토
# 2. [x] 부채 항목 우선순위 결정
# 3. [ ] [USER-APPROVE] 부채 계획 승인

# 한 줄 형식
flow status --oneline
# 출력: M0 (기술 부채 검토) - 2/3
```

### `flow check`

체크리스트 항목을 완료로 표시.

```bash
# 단일 항목 체크 (1부터 시작하는 인덱스)
flow check 1

# 여러 항목 체크
flow check 1 2 3

# 증거/근거 추가
flow check 1 --evidence "2024-01-15 팀과 검토함"

# USER-APPROVE 항목을 토큰과 함께 체크
flow check 3 --token "your-secret-phrase"

# 둘 다 함께
flow check 3 --token "secret" --evidence "@alice의 보안 검토 후 승인"
```

### `flow next`

다음 스테이지로 전이.

```bash
# 다음 스테이지 자동 감지 (첫 번째 유효한 전이 사용)
flow next

# 대상 스테이지 명시적 지정
flow next M1

# 강제 전이 (모든 조건 우회)
flow next --force --reason "긴급 핫픽스 필요"

# 가능한 출력:
# 성공: "✅ Transitioned to M1: 계획"
# 차단: "Cannot proceed. Unchecked items: ..."
```

### `flow set`

현재 스테이지 또는 모듈 수동 설정.

```bash
# 스테이지만 설정
flow set M2

# 스테이지와 활성 모듈 설정
flow set P3 --module inventory-system

# 용도:
# - 상태 손상 후 복구
# - 특정 지점으로 점프
# - 특정 스테이지 테스트
```

### `flow review`

서브 에이전트 리뷰 결과 기록.

```bash
flow review --agent "code-reviewer" --summary "모든 SOLID 원칙 준수, 차단 이슈 없음"

# 나중에 확인할 수 있는 감사 로그 항목 생성
```

### `flow secret-generate`

USER-APPROVE 항목용 비밀 생성.

```bash
flow secret-generate

# 대화형 프롬프트:
# 비밀 문구를 입력하세요: ********
# 비밀 문구 확인: ********
# Secret hash saved to .workflow/secret
```

### `flow tutorial`

내장 튜토리얼 시스템 접근.

```bash
# 모든 섹션 목록
flow tutorial --list

# 특정 섹션 보기
flow tutorial --section 0

# 대화형 튜토리얼 시작
flow tutorial

# 별칭 사용
flow guide --section 2
```

### 전역 옵션

```bash
# 표시 언어 설정
flow --lang ko status
flow --lang en --help

# 도움말
flow --help
flow status --help
```

---

## 워크플로우 개념

### 스테이지 유형

워크플로우 엔진은 두 가지 수준의 스테이지를 지원합니다:

#### 마일스톤 스테이지 (M0-M4)

며칠에서 몇 주에 걸친 고수준 프로젝트 단계:

| 스테이지 | 이름 | 목적 |
|---------|------|------|
| M0 | 기술 부채 검토 | 기술 부채 평가 및 계획 |
| M1 | 마일스톤 계획 | PRD 생성, 범위 정의 |
| M2 | 마일스톤 논의 | 아키텍처 검토, 사용자 승인 |
| M3 | 브랜치 생성 | 마일스톤용 Git 설정 |
| M4 | 마일스톤 종료 | 머지, 문서화, 축하 |

#### 페이즈 스테이지 (P1-P7)

각 마일스톤 내의 상세 구현 단계:

| 스테이지 | 이름 | 목적 |
|---------|------|------|
| P1 | 페이즈 계획 | 구체적 산출물 정의 |
| P2 | 페이즈 논의 | 기술적 접근 방식, 사용자 승인 |
| P3 | 스펙 | 기술 사양서 작성 |
| P4 | 구현 | 코드 작성 |
| P5 | 테스팅 | 유닛 및 통합 테스트 |
| P6 | 셀프 리뷰 | 코드 품질 검사 |
| P7 | 페이즈 종료 | 문서 동기화, 커밋 |

### 워크플로우 흐름

```
┌─────────────────────────────────────────────────────────────────┐
│                    마일스톤 생명주기                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ [마일스톤 시작] ──────────────────────────────────────────┐ │
│  │  M0: 기술 부채 검토                                        │ │
│  │  M1: 마일스톤 계획                                         │ │
│  │  M2: 마일스톤 논의                                         │ │
│  │  M3: 브랜치 생성                                           │ │
│  └────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│  ┌─ [페이즈 루프] ────────────────────────────────────────────┐ │
│  │                                                             │ │
│  │   페이즈 1 ──► 페이즈 2 ──► 페이즈 3 ──► ...               │ │
│  │      │           │           │                              │ │
│  │      └───────────┴───────────┴──────────┐                  │ │
│  │                                          │                  │ │
│  │   각 페이즈마다:                          │                  │ │
│  │   P1 → P2 → P3 → P4 → P5 → P6 → P7 ─────┘                  │ │
│  │                                                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                            │                                     │
│                            ▼                                     │
│  ┌─ [마일스톤 종료] ──────────────────────────────────────────┐ │
│  │  M4: 마일스톤 종료                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 체크리스트

각 스테이지에는 완료해야 하는 체크리스트 항목이 있습니다:

```yaml
checklist:
  - "일반 항목 - 완료되면 체크"
  - "[USER-APPROVE] 토큰으로 사람 검증 필요"
  - "[AGENT:spec-validator] 서브 에이전트 리뷰 필요"
```

**체크리스트 항목 유형:**

| 유형 | 문법 | 설명 |
|------|------|------|
| 일반 | `"항목 텍스트"` | AI가 자유롭게 체크 가능 |
| 사용자 승인 | `"[USER-APPROVE] 텍스트"` | 비밀 토큰 필요 |
| 에이전트 리뷰 | `"[AGENT:name] 텍스트"` | 서브 에이전트 검증 필요 |

---

## AI 어시스턴트와 함께 사용하기

이 섹션은 **AI 어시스턴트(Claude, GPT 등)가 워크플로우 도구를 사용하여 프로젝트를 개발하도록 설정하는 방법**을 설명합니다.

### 기본 설정

#### 1. 프로젝트 지침 파일 (CLAUDE.md 또는 .cursorrules)

프로젝트 루트에 AI 지침 파일을 생성합니다:

```markdown
# AI 에이전트 지침

## 워크플로우 프로토콜 (필수)

이 프로젝트는 `workflow-tool`을 사용한 구조화된 개발 워크플로우를 따릅니다.

### 매 작업 시작 시
1. **반드시** `flow status`를 실행하여 현재 스테이지와 체크리스트 확인
2. 현재 스테이지의 체크리스트 항목을 순서대로 수행
3. 각 항목 완료 시 `flow check N`으로 체크
4. 모든 항목 완료 후 `flow next`로 다음 스테이지 진행

### 응답 형식
매 응답 시작에 현재 스테이지 명시:
\`\`\`
**[Stage M2]** 마일스톤 논의
**[Stage P4]** 구현 (Phase 24.2)
\`\`\`

### 금지 사항
- 체크리스트 항목 건너뛰기 금지
- `--force` 옵션 임의 사용 금지
- USER-APPROVE 항목 무시 금지
```

#### 2. 워크플로우 상태 자동 표시

`.memory/ACTIVE_STATUS.md` 파일이 자동으로 업데이트됩니다. CLAUDE.md에서 이를 임포트합니다:

```markdown
# CLAUDE.md

@import .memory/ACTIVE_STATUS.md

## 작업 지침
...
```

이렇게 하면 AI가 대화 시작 시 자동으로 현재 워크플로우 상태를 인식합니다.

### 상세 설정 예시

#### 완전한 CLAUDE.md 예시

```markdown
# For AI Agent 🤖

@import .memory/ACTIVE_STATUS.md

---

## ⚠️ 필수: 워크플로우 준수

이 프로젝트는 엄격한 개발 워크플로우를 따릅니다.

### 매 턴마다 수행할 작업

1. **상태 확인**: 응답 시작 시 `flow status` 실행
2. **스테이지 명시**: `**[Stage XX]** 스테이지명` 형식으로 현재 위치 표시
3. **체크리스트 수행**: 현재 스테이지의 항목들을 순서대로 수행
4. **완료 기록**: 각 항목 완료 시 `flow check N --evidence "설명"` 실행
5. **전이**: 모든 항목 완료 후 `flow next` 실행

### 스테이지별 행동 가이드

#### M0-M3 (마일스톤 준비)
- 계획 문서 작성에 집중
- 코드 작성하지 않음
- 사용자 승인 필요 시 요청

#### P1-P3 (페이즈 준비)
- 스펙 문서 작성
- 아직 코드 작성하지 않음
- 설계 검토 요청

#### P4 (구현)
- 스펙에 따라 코드 작성
- 구현 중 스펙과 다르면 기록

#### P5-P6 (검증)
- 테스트 작성 및 실행
- 코드 리뷰 수행
- 품질 체크리스트 확인

#### P7 (종료)
- 문서 업데이트
- 스펙 동기화
- 커밋 생성

### 예시 대화 흐름

```
AI: `flow status` 실행 결과를 확인했습니다.

**[Stage P4]** 구현 (Phase 24.1)

현재 체크리스트:
1. [x] 스펙에 따라 파일/폴더 생성
2. [ ] 로직 구현
3. [ ] 의존성 확인
4. [ ] 구조 검증

항목 2 "로직 구현"을 수행하겠습니다.
[코드 작성...]

완료되었습니다. 체크하겠습니다.
`flow check 2 --evidence "UserService 클래스 구현 완료"`
```

---

## 명령어 요약

| 명령어 | 용도 | 예시 |
|--------|------|------|
| `flow status` | 현재 상태 확인 | 매 턴 시작 |
| `flow check N` | 항목 완료 | `flow check 1 2` |
| `flow check N --evidence "..."` | 증거와 함께 완료 | 중요 결정 |
| `flow check N --token "..."` | USER-APPROVE 항목 | 사용자에게 요청 |
| `flow next` | 다음 스테이지 | 모든 항목 완료 후 |
| `flow set XX` | 스테이지 이동 | 복구/테스트 시 |
```

### AI 세션 시작 템플릿

AI와 새 세션을 시작할 때 사용할 프롬프트:

```markdown
새 개발 세션을 시작합니다.

1. `flow status`로 현재 워크플로우 상태를 확인해주세요.
2. 현재 스테이지의 체크리스트를 검토해주세요.
3. 다음으로 수행할 작업을 알려주세요.

워크플로우를 따라 진행해주세요.
```

### USER-APPROVE 처리 방법

사용자 승인이 필요한 항목을 만났을 때:

```markdown
# AI 응답 예시

현재 체크리스트에 USER-APPROVE 항목이 있습니다:
- `[USER-APPROVE] 프로덕션 배포 승인`

이 항목을 완료하려면 다음 명령어를 실행해주세요:
\`\`\`bash
flow check 3 --token "your-secret"
\`\`\`

아직 비밀을 생성하지 않았다면:
\`\`\`bash
flow secret-generate
\`\`\`

승인하시면 알려주세요.
```

### 서브 에이전트 리뷰 통합

AI가 다른 AI 에이전트(spec-validator, code-reviewer 등)의 리뷰를 기록:

```bash
# 코드 리뷰 완료 후
flow review --agent "code-reviewer" --summary "SOLID 원칙 준수, 타입 힌트 완비, 이슈 없음"

# 스펙 검증 후
flow review --agent "spec-validator" --summary "모든 필수 필드 정의됨, 메서드 시그니처 완전"
```

### 실제 작업 흐름 예시

```bash
# 1. 세션 시작 - 상태 확인
$ flow status
Current Stage: P4 (구현)
========================================
Active Module: user-auth
----------------------------------------
1. [x] 스펙에 따라 파일/폴더 생성
2. [ ] 로직 구현
3. [ ] 의존성 확인
4. [ ] 구조 검증

# 2. AI가 코드 구현 후
$ flow check 2 --evidence "UserService, AuthMiddleware 구현 완료"
Checked: 로직 구현

# 3. 의존성 확인 후
$ flow check 3 --evidence "순환 의존성 없음 확인"
Checked: 의존성 확인

# 4. 구조 검증
$ flow check 4 --evidence "mcontext --structure 통과"
Checked: 구조 검증

# 5. 다음 스테이지로 이동
$ flow next
✅ Transitioned to P5
Current Stage: P5 (테스팅)
...
```

### 멀티 에이전트 설정

여러 AI 에이전트가 협업하는 경우:

```yaml
# workflow.yaml에 에이전트 리뷰 요구 설정
stages:
  P6:
    label: "셀프 리뷰"
    checklist:
      - "스펙 정합성 확인"
      - "[AGENT:code-reviewer] 코드 리뷰어 에이전트 리뷰"
      - "[USER-APPROVE] 사용자 승인"
```

각 에이전트는 `flow review`로 자신의 리뷰를 기록:

```bash
# code-reviewer 에이전트가 실행
flow review --agent "code-reviewer" --summary "리뷰 완료: 이슈 없음"

# 메인 에이전트가 항목 체크
flow check 2  # AGENT 리뷰가 기록되어 있어야 통과
```

### 팁: 효과적인 AI 협업

1. **명확한 지침**: CLAUDE.md에 워크플로우 규칙 명시
2. **상태 자동 노출**: ACTIVE_STATUS.md 임포트
3. **증거 기록**: 모든 결정에 `--evidence` 사용
4. **단계적 진행**: 한 번에 하나의 체크리스트 항목 처리
5. **전이 전 확인**: `flow next` 전에 모든 항목 완료 확인

---

## 튜토리얼

### 내장 대화형 튜토리얼

워크플로우 도구에는 포괄적인 내장 튜토리얼이 포함되어 있습니다:

```bash
# 모든 튜토리얼 섹션 목록
flow tutorial --list

# 출력:
# 0. 소개
# 1. 설치 및 설정
# 2. 기본 명령어
# 3. 보안 및 비밀
# 4. 고급 기능
# 5. 모범 사례

# 특정 섹션 보기
flow tutorial --section 0

# 대화형 모드 시작
flow tutorial
```

### 튜토리얼 내용

| 섹션 | 다루는 주제 |
|------|------------|
| 0. 소개 | workflow-tool이란, 핵심 개념, 빠른 시작 |
| 1. 설치 | pip 설치, 쉘 별칭, 초기 구성 |
| 2. 기본 명령어 | status, check, next, set - 예시와 함께 |
| 3. 보안 | USER-APPROVE, 비밀 생성, 감사 추적 |
| 4. 고급 | 커스텀 플러그인, 룰셋, 변수, 훅 |
| 5. 모범 사례 | 설계 팁, 일상 워크플로우, AI 협업 |

---

## 예시

`examples/` 디렉토리에 바로 사용할 수 있는 워크플로우 구성이 있습니다:

### 간단한 워크플로우

위치: `examples/simple/`

소규모 프로젝트를 위한 최소 3단계 워크플로우:

```bash
cd examples/simple
flow status
```

### 전체 프로젝트 워크플로우

위치: `examples/full-project/`

PROJECT_MANAGEMENT_GUIDE.md와 일치하는 완전한 M0-M4, P1-P7 워크플로우:

```bash
cd examples/full-project
flow status
```

### 커스텀 플러그인 예시

위치: `examples/custom-plugins/`

커스텀 검증기 생성 및 사용 방법 시연:

```bash
cd examples/custom-plugins
flow status
```

각 예시의 상세 문서는 `examples/README.ko.md`를 참조하세요.

---

## 고급 사용법

### 커스텀 플러그인 만들기

1. 검증기 클래스 생성:

```python
# my_project/validators/api_validator.py
from workflow.core.validator import BaseValidator
import requests

class APIHealthValidator(BaseValidator):
    """API 엔드포인트가 정상인지 확인."""

    def validate(self, args, context):
        url = args.get('url')
        timeout = args.get('timeout', 5)

        try:
            response = requests.get(url, timeout=timeout)
            return response.status_code == 200
        except:
            return False
```

2. workflow.yaml에 등록:

```yaml
plugins:
  api_health: "my_project.validators.api_validator.APIHealthValidator"
```

3. 조건에서 사용:

```yaml
stages:
  DEPLOY:
    transitions:
      - target: "DONE"
        conditions:
          - rule: api_health
            args:
              url: "https://api.example.com/health"
              timeout: 10
            fail_message: "API 헬스 체크 실패"
```

### 재사용을 위한 룰셋

공통 조건 세트를 한 번 정의:

```yaml
rulesets:
  production_ready:
    - rule: all_checked
    - rule: shell
      args:
        cmd: "pytest"
    - rule: shell
      args:
        cmd: "mypy src/"
    - rule: fs
      args:
        path: "CHANGELOG.md"
        not_empty: true

stages:
  PRE_DEPLOY:
    transitions:
      - target: "DEPLOY"
        conditions:
          - use_ruleset: production_ready
```

### 변수와 치환

일관성을 위한 변수 사용:

```yaml
variables:
  project_name: "my-app"
  test_cmd: "pytest tests/ -v"
  main_branch: "main"

stages:
  TEST:
    checklist:
      - "${test_cmd} 실행"
    transitions:
      - target: "MERGE"
        conditions:
          - rule: shell
            args:
              cmd: "${test_cmd}"
```

---

## 다국어 지원

### 지원 언어

| 코드 | 언어 | 상태 |
|------|------|------|
| `en` | English | 완전 지원 |
| `ko` | 한국어 | 완전 지원 |

### 언어 설정

```bash
# 커맨드라인 플래그로
flow --lang ko status

# 환경 변수로
export FLOW_LANG=ko
flow status

# 언어 감지 우선순위:
# 1. --lang 플래그
# 2. FLOW_LANG 환경 변수
# 3. 시스템 로케일
# 4. 기본값 (영어)
```

---

## 문제 해결

### 일반적인 문제

#### "구성 파일을 찾을 수 없음"

```bash
# 오류: Configuration file not found: workflow.yaml

# 해결: 프로젝트 루트에 workflow.yaml 생성
# 또는 경로 지정: flow --config path/to/workflow.yaml status
```

#### "전이할 수 없음" 오류

```bash
# 오류: Cannot proceed. Unchecked items: ...

# 해결: 남은 항목 확인
flow status

# 누락된 항목 완료
flow check 3 4

# 다시 시도
flow next
```

#### "USER-APPROVE 토큰 잘못됨"

```bash
# 오류: Invalid token for USER-APPROVE

# 해결 1: 비밀이 생성되었는지 확인
ls .workflow/secret

# 해결 2: 비밀 재생성
flow secret-generate

# 해결 3: 올바른 문구 사용
flow check 2 --token "실제-비밀-문구"
```

#### 플러그인 로드 오류

```bash
# 오류: Failed to load plugin: my_plugin

# 해결: workflow.yaml의 플러그인 경로 확인
# 모듈이 임포트 가능한지 확인:
python -c "from my_project.validators import MyValidator"
```

#### 상태 손상

```bash
# state.json이 손상된 경우:

# 옵션 1: 알려진 스테이지로 리셋
flow set M0

# 옵션 2: 삭제 후 재초기화
rm .workflow/state.json
flow status  # 새 상태 생성
```

### 도움 받기

1. **튜토리얼**: `flow tutorial`
2. **명령어 도움말**: `flow <command> --help`
3. **문서**: `.memory/docs/`
4. **이슈**: https://github.com/your-org/workflow-tool/issues

---

## 기여하기

### 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/your-org/workflow-tool.git
cd workflow-tool

# 가상환경 생성
python -m venv .venv
source .venv/bin/activate

# 개발 모드로 설치
pip install -e ".[dev]"

# 테스트 실행
pytest tests/ -v
```

### 코딩 표준

- Python 3.10+ 타입 힌트
- PEP 8 스타일 가이드
- 공개 API에 독스트링
- 새 기능에 테스트

---

## 라이선스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 참조.

---

**즐거운 워크플로우 관리 되세요!** 🚀
