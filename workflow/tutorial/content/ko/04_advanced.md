# 고급 기능

이 섹션에서는 고급 워크플로우 구성과 사용법을 다룹니다.

## 커스텀 검증기 (플러그인)

### 내장 플러그인

**FileExistsValidator**: 파일 존재 여부 확인
```yaml
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"

stages:
  P4:
    transitions:
      - target: P5
        conditions:
          - rule: fs
            args:
              path: "src/main.py"
              not_empty: true
```

**CommandValidator**: 쉘 명령어 실행
```yaml
plugins:
  shell: "workflow.plugins.shell.CommandValidator"

stages:
  P5:
    transitions:
      - target: P6
        conditions:
          - rule: shell
            args:
              cmd: "pytest tests/ -v"
              expect_code: 0
```

### 커스텀 플러그인 만들기

1. 플러그인 파일 생성:
```python
# workflow/plugins/my_validator.py
from ..core.validator import BaseValidator

class MyValidator(BaseValidator):
    def validate(self, args, context):
        # 검증 로직
        return True  # 또는 False
```

2. workflow.yaml에 등록:
```yaml
plugins:
  my_check: "workflow.plugins.my_validator.MyValidator"
```

## 룰셋

재사용을 위한 조건 그룹:

```yaml
rulesets:
  ready_for_deploy:
    - rule: all_checked
    - rule: shell
      args:
        cmd: "pytest"
    - rule: fs
      args:
        path: "CHANGELOG.md"

stages:
  P6:
    transitions:
      - target: P7
        conditions:
          - use_ruleset: ready_for_deploy
```

## 서브 에이전트 리뷰

AI 서브 에이전트 리뷰 기록:

```bash
flow review --agent "code-reviewer" --summary "모든 SOLID 원칙 준수, 이슈 없음"
```

나중에 확인할 수 있는 감사 기록이 생성됩니다.

### --agent 플래그로 간소화된 체크

`[AGENT:name]` 항목을 인라인 등록과 함께 체크:

```bash
# 두 명령어 대신:
flow review --agent plan-critic --summary "..."
flow check 1

# 하나의 명령어로:
flow check 1 --agent plan-critic
```

### AI CLI Hook 통합 (자동화)

CLI 훅을 사용하여 에이전트 리뷰 등록을 완전 자동화합니다.
**Claude Code**와 **Gemini CLI** 모두 지원됩니다.

**Claude Code 설정:**
```bash
mkdir -p .claude/hooks
cp examples/hooks/auto-review.sh .claude/hooks/
chmod +x .claude/hooks/auto-review.sh
```

`.claude/settings.json`:
```json
{
  "hooks": {
    "PostToolUse": [{ "matcher": "Task", "hooks": [{ "type": "command", "command": ".claude/hooks/auto-review.sh" }] }]
  }
}
```

**Gemini CLI 설정:**
```bash
mkdir -p .gemini/hooks
cp examples/hooks/auto-review.sh .gemini/hooks/
chmod +x .gemini/hooks/auto-review.sh
```

`settings.json`:
```json
{
  "hooks": {
    "AfterTool": [{ "matcher": "spawn_agent|delegate", "hooks": [{ "type": "command", "command": "$GEMINI_PROJECT_DIR/.gemini/hooks/auto-review.sh" }] }]
  }
}
```

**작동 원리:**
1. AI가 에이전트 위임 도구 호출
2. 훅이 완료를 감지 (PostToolUse/AfterTool)
3. 훅이 에이전트 이름을 추출하고 `flow review` 호출
4. `[AGENT:name]` 항목의 `flow check`가 이제 통과됨

### 세션 시작 훅 (워크플로우 상태 자동 로드)

AI가 세션을 시작할 때 워크플로우 상태를 자동으로 표시합니다.

**Claude Code** (`.claude/settings.json`):
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{ "type": "command", "command": "flow status 2>/dev/null || echo 'No workflow initialized'" }]
      },
      {
        "matcher": "resume",
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**Gemini CLI** (`settings.json`):
```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{ "type": "command", "command": "flow status 2>/dev/null || echo 'No workflow initialized'" }]
      },
      {
        "matcher": "resume",
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**매처:**
| Matcher | 트리거 시점 |
|---------|------------|
| `startup` | 새 세션 시작 |
| `resume` | 기존 세션 재개 |
| `clear` | `/clear` 명령 후 |
| `compact` | 컨텍스트 압축 후 (Claude Code만) |

**결과:** AI가 시작하면 자동으로 현재 워크플로우 상태를 컨텍스트에서 확인합니다.

### 사용자 프롬프트 훅 (매 입력마다 실시간 상태)

세션 시작 시뿐만 아니라 사용자가 프롬프트를 제출할 때마다 워크플로우 상태를 표시합니다.

**Claude Code** - `UserPromptSubmit` (`.claude/settings.json`):
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**Gemini CLI** - `BeforeModel` (`settings.json`):
```json
{
  "hooks": {
    "BeforeModel": [
      {
        "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }]
      }
    ]
  }
}
```

**비교:**
| 훅 | 트리거 시점 | 용도 |
|----|-----------|------|
| `SessionStart` | 세션 시작/재개 시 1회 | 초기 컨텍스트 로드 |
| `UserPromptSubmit` / `BeforeModel` | 사용자 프롬프트마다 | 실시간 상태 추적 |

**권장 조합 설정:**
```json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup", "hooks": [{ "type": "command", "command": "flow status 2>/dev/null || true" }] }
    ],
    "UserPromptSubmit": [
      { "hooks": [{ "type": "command", "command": "flow status --oneline 2>/dev/null || true" }] }
    ]
  }
}
```

- 세션 시작: 전체 상태 표시
- 각 프롬프트: 한 줄 상태 (최소 오버헤드)

## 쉘 래퍼를 통한 자동 체크

태그와 쉘 래퍼를 사용하여 특정 CLI 명령 성공 시 체크리스트를 자동 업데이트합니다.

### 1단계: 체크리스트 항목에 태그 추가

```yaml
# workflow.yaml
stages:
  P3:
    checklist:
      - "[CMD:pytest] 테스트 실행"
      - "[CMD:memory-write] memory tool로 문서 저장"
      - "[CMD:lint] 린터 실행"
```

### 2단계: 쉘 래퍼 생성

```bash
# .bashrc 또는 프로젝트/.envrc

# pytest 래퍼
pytest() {
    command pytest "$@"
    [ $? -eq 0 ] && flow check --tag "CMD:pytest" 2>/dev/null
}

# memory_tool 래퍼 (서브커맨드 인식)
memory_tool() {
    command memory_tool "$@"
    [ $? -eq 0 ] && case "$1" in
        write|save) flow check --tag "CMD:memory-write" ;;
    esac
}

# lint 래퍼
lint() {
    command ruff check . "$@"
    [ $? -eq 0 ] && flow check --tag "CMD:lint" 2>/dev/null
}
```

### 3단계: 평소처럼 사용

```bash
# pytest 실행 - 성공 시 체크리스트 자동 업데이트
pytest tests/
# ✅ 자동 체크: [CMD:pytest] 테스트 실행

# memory tool - 'write' 서브커맨드만 체크 트리거
memory_tool write docs/spec.md
# ✅ 자동 체크: [CMD:memory-write] memory tool로 문서 저장

memory_tool read docs/spec.md
# (체크리스트 업데이트 없음 - read는 매핑되지 않음)
```

### 태그 매칭

`--tag` 옵션은 해당 태그를 포함하는 **모든 미체크 항목**을 찾아 체크합니다:

```bash
flow check --tag "CMD:pytest"
# "[CMD:pytest]"를 포함하는 항목을 찾아 체크
```

**장점:**
- AI와 사용자 실행 모두 동작
- 서브커맨드 인식 (특정 액션만 체크 트리거)
- 항목 인덱스 번호를 알 필요 없음
- 명시적 태그로 실수 방지

## 변수

프로젝트 전체 변수 정의:

```yaml
variables:
  project_name: "my-app"
  version: "2.0.0"
  test_command: "pytest -v"
```

조건에서 사용:
```yaml
conditions:
  - rule: shell
    args:
      cmd: "${test_command}"
```

## 조건부 규칙 (when 절)

`when` 절을 사용하여 컨텍스트에 따라 조건을 건너뜁니다:

```yaml
stages:
  P3:
    transitions:
      - target: P4
        conditions:
          # 코드 모듈에서만 구현 디렉토리 검사
          - rule: fs
            when: '${active_module} not in ["roadmap", "docs", "planning"]'
            args:
              path: "src/${active_module}/"
            fail_message: "구현 디렉토리가 없습니다"

          # 코드 모듈에서만 테스트 실행
          - rule: shell
            when: '${active_module} not in ["roadmap", "docs"]'
            args:
              cmd: "pytest tests/${active_module}/"
```

### 지원하는 연산자

| 연산자 | 예시 | 설명 |
|--------|------|------|
| `==` | `${var} == "value"` | 동등 비교 |
| `!=` | `${var} != "value"` | 불일치 비교 |
| `in` | `${var} in ["a", "b"]` | 리스트 포함 |
| `not in` | `${var} not in ["a", "b"]` | 리스트 미포함 |

### 사용 사례

**메타 모듈 (roadmap, docs):** 코드 관련 검증 건너뛰기
```yaml
- rule: shell
  when: '${active_module} != "roadmap"'
  args:
    cmd: "pytest"
```

**스테이지별 조건:**
```yaml
- rule: fs
  when: '${current_stage} == "P6"'
  args:
    path: "CHANGELOG.md"
```

`when` 조건이 false로 평가되면, 해당 규칙은 감사 로그에 `SKIPPED`로 기록됩니다.

## 스테이지 훅 (on_enter)

스테이지 진입 시 작업 실행:

```yaml
stages:
  P4:
    on_enter:
      - action: "notify"
        args:
          message: "구현 시작"
      - action: "shell"
        args:
          cmd: "git status"
```

## 조건부 전이

조건에 따른 다중 대상:

```yaml
stages:
  P7:
    transitions:
      # 모든 페이즈 완료 시 M4로
      - target: "M4"
        conditions:
          - rule: all_phases_complete
      # 그렇지 않으면 다음 페이즈로
      - target: "P1"
        conditions:
          - use_ruleset: all_checked
```

다음: 모범 사례와 팁!
