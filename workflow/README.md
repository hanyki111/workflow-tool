# AI-Native Workflow Engine (v2.0)

> **상태 머신 기반의 AI 협업 및 프로젝트 관리 자동화 도구**

이 도구는 AI 에이전트와 인간 개발자가 협력하여 프로젝트를 진행할 때, 명확한 절차를 강제하고 감사 로그(Audit Log)를 남기며 보안을 유지하기 위해 설계되었습니다.

## 주요 기능

1.  **YAML 기반 워크플로우 정의**: 복잡한 상태 전이 및 검증 규칙을 YAML로 관리.
2.  **보안 인증 (SHA-256)**: 중요한 단계(`[USER-APPROVE]`)에서 AI가 독단적으로 진행하는 것을 방지하는 해시 토큰 시스템.
3.  **에이전트 검증 (Sub-Agent Verification)**: 특정 단계(`[AGENT:name]`)에서 전문 에이전트의 검토 여부를 로그 기반으로 확인.
4.  **자동 검증 플러그인**: 파일 존재 여부, 쉘 명령 성공 여부 등을 자동으로 체크.
5.  **Audit Trail**: 모든 상태 전이와 체크 항목에 대한 증거(Evidence) 및 기록 보존.

## 설치 및 설정

### 1. 요구 사항
- Python 3.10+
- PyYAML

### 2. 별칭(Alias) 설정
도구를 편리하게 사용하기 위해 다음 명령으로 `flow` 별칭을 설치할 수 있습니다.
```bash
python tools/workflow/cli.py install-alias --name flow
source ~/.zshrc (또는 ~/.bashrc)
```

## 사용법 (Tutorial)

### 1. 초기화 및 상태 확인
```bash
flow status
```
현재 마일스톤, 페이즈, 활성 모듈 및 체크리스트를 표시합니다.

### 2. 시크릿 생성 (최초 1회)
AI가 `[USER-APPROVE]` 항목을 마음대로 체크하지 못하게 하려면 시크릿 해시를 생성해야 합니다.
```bash
flow secret-generate
```
입력한 평문은 저장되지 않으며, 오직 SHA-256 해시값만 `.workflow/secret`에 저장됩니다.

### 3. 체크리스트 완료
```bash
# 일반 항목 체크
flow check 1 2 3

# 사용자 승인 항목 체크 (토큰 필요)
flow check 1 --token "your-secret-token"

# 증거와 함께 체크
flow check 4 --evidence "Logic verified in module X"
```

### 4. 에이전트 리뷰 기록
서브 에이전트(예: spec-validator)가 작업을 마친 후 기록을 남깁니다.
```bash
flow review --agent spec-validator --summary "Spec is compliant with architecture."
```

### 5. 다음 단계로 이동
모든 체크리스트가 완료되고 YAML에 정의된 `conditions`를 만족하면 다음 단계로 이동할 수 있습니다.
```bash
flow next
```

## 프로젝트 구조
- `core/`: 상태 머신 엔진, 파서, 인증, 감사 로그 등 핵심 로직.
- `plugins/`: 자동화 검증 규칙 (File, Shell 등).
- `templates/`: 기본 워크플로우 설정 템플릿.