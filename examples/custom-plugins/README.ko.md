# 커스텀 플러그인 예시

워크플로우 전이를 위한 커스텀 검증기 생성 및 사용 방법을 시연합니다.

## 개요

이 예시는 세 가지 커스텀 검증기를 보여줍니다:

1. **GitBranchValidator** - 올바른 Git 브랜치 확인
2. **CoverageValidator** - 테스트 커버리지 임계값 확인
3. **DependencyValidator** - 보안 취약점 없음 확인

## 파일 구조

```
custom-plugins/
├── workflow.yaml           # 커스텀 플러그인 사용하는 워크플로우
├── .workflow/
│   └── state.json
├── validators/
│   ├── __init__.py
│   └── custom.py           # 커스텀 검증기 구현
└── README.ko.md
```

## 커스텀 검증기

### 1. GitBranchValidator

전이 전 올바른 Git 브랜치에 있는지 확인:

```python
class GitBranchValidator(BaseValidator):
    def validate(self, args, context):
        expected = args.get('branch', 'main')
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            capture_output=True, text=True
        )
        current = result.stdout.strip()
        return current == expected
```

**workflow.yaml에서 사용:**
```yaml
conditions:
  - rule: git_branch
    args:
      branch: "feature/my-feature"
    fail_message: "기능 브랜치에 있어야 합니다"
```

### 2. CoverageValidator

테스트 커버리지가 최소 임계값을 충족하는지 확인:

```python
class CoverageValidator(BaseValidator):
    def validate(self, args, context):
        minimum = args.get('minimum', 80)
        # pytest를 커버리지와 함께 실행
        result = subprocess.run(
            ['pytest', '--cov=src', '--cov-report=term', '--cov-fail-under=' + str(minimum)],
            capture_output=True
        )
        return result.returncode == 0
```

**workflow.yaml에서 사용:**
```yaml
conditions:
  - rule: coverage
    args:
      minimum: 80
    fail_message: "테스트 커버리지가 최소 80%여야 합니다"
```

### 3. DependencyValidator

의존성의 보안 취약점 확인:

```python
class DependencyValidator(BaseValidator):
    def validate(self, args, context):
        # safety 검사 실행 (pip install safety)
        result = subprocess.run(
            ['safety', 'check', '--json'],
            capture_output=True
        )
        return result.returncode == 0
```

**workflow.yaml에서 사용:**
```yaml
conditions:
  - rule: deps_secure
    fail_message: "의존성에서 보안 취약점 발견됨"
```

## 설정

### 1. 의존성 설치

```bash
# 커버리지 검증용
pip install pytest-cov

# 의존성 검사용
pip install safety
```

### 2. Python 경로 설정

```bash
cd examples/custom-plugins
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 3. 워크플로우 테스트

```bash
flow status
flow check 1 2 3
flow next  # 커스텀 검증기 확인
```

## 직접 검증기 만들기

### 단계 1: 검증기 클래스 생성

```python
# my_validators.py
from workflow.core.validator import BaseValidator

class MyValidator(BaseValidator):
    """
    커스텀 검증기 설명.

    Args (workflow.yaml에서):
        arg1: arg1 설명
        arg2: arg2 설명

    Context:
        project_root: 기본 디렉토리 경로
    """

    def validate(self, args: dict, context: dict) -> bool:
        # 인자 가져오기
        arg1 = args.get('arg1', 'default')
        project_root = context.get('project_root', '.')

        # 검증 로직
        try:
            # ... 검사 수행 ...
            return True  # 통과
        except Exception:
            return False  # 실패
```

### 단계 2: workflow.yaml에 등록

```yaml
plugins:
  my_check: "my_validators.MyValidator"
```

### 단계 3: 조건에서 사용

```yaml
stages:
  STAGE_NAME:
    transitions:
      - target: "NEXT_STAGE"
        conditions:
          - rule: my_check
            args:
              arg1: "value1"
              arg2: "value2"
            fail_message: "검증 실패"
```

## 검증기 아이디어

만들 수 있는 유용한 검증기들:

| 검증기 | 목적 |
|--------|------|
| `DockerRunning` | Docker 데몬이 실행 중인지 확인 |
| `PortAvailable` | 포트가 사용 가능한지 확인 |
| `EnvVarsSet` | 필수 환경 변수 존재 확인 |
| `APIHealthy` | 외부 API 헬스 체크 |
| `DBMigrated` | 데이터베이스 마이그레이션 완료 확인 |
| `LintClean` | 린팅 오류 없음 확인 |
| `TypeCheckPass` | mypy/pyright 통과 확인 |
| `NoTODOs` | 코드에 TODO 주석 없음 확인 |
| `ChangelogUpdated` | CHANGELOG.md 수정됨 확인 |
| `VersionBumped` | 버전 번호 증가 확인 |

## 검증기 디버깅

### 검증기 직접 테스트

```python
# test_validator.py
from validators.custom import GitBranchValidator

validator = GitBranchValidator()
result = validator.validate(
    args={'branch': 'main'},
    context={'project_root': '.'}
)
print(f"검증 결과: {result}")
```

### 디버그 출력 추가

```python
class MyValidator(BaseValidator):
    def validate(self, args, context):
        print(f"DEBUG: args={args}")
        print(f"DEBUG: context={context}")
        # ... 나머지 검증
```

### 플러그인 로딩 확인

```bash
python -c "from validators.custom import GitBranchValidator; print('OK')"
```

## 모범 사례

1. **검증기를 집중적으로**: 검증기당 하나의 검사
2. **예외 처리**: 검증기가 크래시되지 않도록
3. **명확한 fail_message 제공**: 사용자가 실패 원인을 이해하도록
4. **검증기를 빠르게**: 오래 걸리는 작업 피하기
5. **context 현명하게 사용**: `project_root`는 항상 사용 가능
6. **args 문서화**: workflow.yaml 사용자를 위한 명확한 문서

## 문제 해결

### "플러그인 로드 실패"

```bash
# 모듈 경로 확인
python -c "from validators.custom import MyValidator"

# PYTHONPATH 확인
echo $PYTHONPATH
```

### 검증기가 항상 실패

```bash
# 기본 명령어 수동 테스트
pytest --cov=src --cov-fail-under=80

# 검증기 로직 확인
python -c "
from validators.custom import CoverageValidator
v = CoverageValidator()
print(v.validate({'minimum': 80}, {}))
"
```

### 검증기가 항상 통과

실패 케이스에서 `False`를 반환하는지 확인:
```python
def validate(self, args, context):
    if something_wrong:
        return False  # 명시적으로 False 반환 필요
    return True
```
