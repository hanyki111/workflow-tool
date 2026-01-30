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
