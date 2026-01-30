# 설치 및 설정

이 섹션에서는 워크플로우 도구를 설치하고 구성하는 방법을 다룹니다.

## 설치

### pip 사용 (권장)

```bash
# 개발용 편집 가능 모드로 설치
pip install -e .

# 또는 패키지에서 설치
pip install ai-workflow-engine
```

### 설치 확인

```bash
# 도움말 메시지가 표시되어야 함
flow --help

# 대체 호출 방법
python -m workflow --help
```

## 초기 구성

### 1. workflow.yaml 생성

워크플로우 구성은 프로젝트 루트의 `workflow.yaml`에 있습니다:

```yaml
version: "2.0"

variables:
  project_name: "my-project"

stages:
  M0:
    id: "M0"
    label: "초기 스테이지"
    checklist:
      - "완료할 첫 번째 항목"
      - "완료할 두 번째 항목"
    transitions:
      - target: "M1"
```

### 2. 상태 초기화

`.workflow/state.json` 생성:

```json
{
  "current_stage": "M0",
  "checklist": []
}
```

### 3. 쉘 별칭 설정 (선택사항)

```bash
# .bashrc 또는 .zshrc에 추가
alias flow='python -m workflow'

# 또는 내장 설치 프로그램 사용
flow install-alias --name flow
```

## 언어 구성

선호하는 언어 설정:

```bash
# 환경 변수로
export FLOW_LANG=ko

# 명령줄로
flow --lang ko status

# workflow.yaml에서
# language: "ko" 추가
```

## 디렉토리 구조

설정 후 프로젝트 구조:

```
my-project/
├── workflow.yaml        # 워크플로우 정의
├── .workflow/
│   ├── state.json       # 현재 상태
│   ├── docs/            # 워크플로우 문서
│   │   └── PROJECT_MANAGEMENT_GUIDE.md
│   ├── audit/           # 감사 로그 (자동 생성)
│   └── ACTIVE_STATUS.md # AI 상태 훅 (자동 생성)
└── CLAUDE.md            # AI 지침 (선택)
```

## 경로 설정 (선택)

workflow.yaml에서 경로를 커스터마이즈할 수 있습니다:

```yaml
# 기본 경로 (모두 .workflow/ 내부)
docs_dir: ".workflow/docs"
audit_dir: ".workflow/audit"
status_file: ".workflow/ACTIVE_STATUS.md"
guide_file: ".workflow/docs/PROJECT_MANAGEMENT_GUIDE.md"
```

다음: 기본 명령어를 배워봅시다!
