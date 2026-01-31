# 기본 명령어

워크플로우 관리를 위한 필수 명령어를 배웁니다.

## Status 명령어

워크플로우에서 현재 위치 확인:

```bash
flow status
```

출력 예시:
```
=== 현재 스테이지: M0 (기술 부채 검토) ===
활성 모듈: core-engine

체크리스트:
[ ] 1. 사용자와 함께 발견된 부채 검토
[x] 2. 기술 부채 검색 실행
[ ] 3. 이번 마일스톤에서 해결할 부채 결정

진행률: 1/3 항목 완료
```

### 한 줄 상태

```bash
flow status --oneline
# 출력: M0 (기술 부채 검토) - 1/3
```

## Check 명령어

체크리스트 항목을 완료로 표시:

```bash
# 단일 항목 체크 (1부터 시작하는 인덱스)
flow check 1

# 여러 항목 체크
flow check 1 2 3

# 증거/근거 추가
flow check 1 --evidence "모든 모듈 검토 완료, 심각한 부채 없음"

# 액션 명령어에 인자 전달
flow check 5 --args "feat: 사용자 인증 추가"
```

### Active Workflow (액션 자동 실행)

workflow.yaml에 `action`이 정의된 체크리스트 항목은 자동으로 실행됩니다:

```bash
$ flow check 1
✅ Action executed: pytest -v
   Output: 15 passed in 2.34s
Checked: 테스트 실행
```

액션이 실패하면 항목이 체크되지 않습니다:

```bash
$ flow check 1
❌ Action failed for item 1: 종료 코드 1로 명령 실패
```

**내장 변수:** 현재 Python 인터프리터에는 `${python}` (venv 인식), 작업 디렉토리에는 `${cwd}`를 사용하세요. 액션은 전체 쉘 환경을 상속받습니다.

## Next 명령어

다음 스테이지로 전이:

```bash
# 다음 스테이지 자동 감지
flow next

# 대상 스테이지 지정
flow next M1

# 플러그인 조건(shell, fs) 건너뛰기 (체크리스트는 필요)
flow next --skip-conditions

# 강제 전이 (모든 규칙 건너뜀, 토큰 필요)
flow next --force --token "secret" --reason "긴급 핫픽스 필요"
```

### 전이 옵션

| 옵션 | 체크리스트 | 조건 | 토큰 |
|------|-----------|------|------|
| (없음) | 필요 | 필요 | 아니오 |
| `--skip-conditions` | 필요 | 건너뜀 | 아니오 |
| `--force` | 건너뜀 | 건너뜀 | 예 |

### 전이 오류

조건이 충족되지 않은 경우:
```
Cannot proceed. Unchecked items:
- 사용자와 함께 발견된 부채 검토
- 이번 마일스톤에서 해결할 부채 결정
```

## Set 명령어

스테이지 또는 모듈 수동 설정:

```bash
# 스테이지 설정
flow set M2

# 스테이지와 모듈 설정
flow set P3 --module inventory-system
```

## Module 명령어

스테이지 변경 없이 모듈 변경 (`--force` 불필요):

```bash
# 활성 모듈 전환
flow module set inventory-system

# 새 페이즈 시작 시 다른 모듈로 작업할 때 유용
```

## 명령어 조합

일반적인 워크플로우:
```bash
# 1. 상태 확인
flow status

# 2. 작업 완료 후 항목 체크
flow check 1
flow check 2 3

# 3. 다음 스테이지로 이동
flow next
```

## 팁

- 작업 시작 전 항상 `flow status` 실행
- 한꺼번에 말고 완료하는 대로 항목 체크
- 중요한 결정에는 `--evidence` 사용
- 꼭 필요한 경우가 아니면 `--force` 사용 금지

다음: 보안과 비밀에 대해 배워봅시다!
