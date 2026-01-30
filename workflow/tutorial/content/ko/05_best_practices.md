# 모범 사례

효과적인 워크플로우 관리를 위한 팁과 패턴입니다.

## 워크플로우 설계

### 1. 스테이지를 집중적으로
각 스테이지는 명확한 단일 목적을 가져야 합니다:
- 좋음: "유닛 테스트 작성"
- 나쁨: "테스트 작성, 버그 수정, 문서 업데이트"

### 2. 체크리스트 세분화
- 스테이지당 3-7개 항목이 이상적
- 너무 적음 = 충분한 가이드가 없음
- 너무 많음 = 압도적

### 3. 의미 있는 조건
단순히 "all_checked"만 확인하지 말고 실제 검증 추가:
```yaml
conditions:
  - use_ruleset: all_checked
  - rule: shell
    args:
      cmd: "pytest"  # 실제로 테스트 실행
```

## 일상 워크플로우

### 작업 시작
```bash
# 항상 상태로 시작
flow status

# 체크리스트 읽기
# 무엇을 해야 하는지 이해
```

### 작업 중
```bash
# 완료하는 대로 항목 체크
flow check 1

# 마지막에 한꺼번에 하지 않기
# 이렇게 해야 정확한 진행 추적 유지
```

### 작업 종료
```bash
# 남은 항목 확인
flow status

# 미완료 시 진행 상황 문서화
flow check 2 --evidence "부분 완료, 테스트 작성했으나 리뷰 필요"
```

## AI 협업

### 컨텍스트 인식
AI 어시스턴트에게 다음을 지시:
1. 각 세션 시작 시 `flow status` 실행
2. 순서대로 체크리스트 항목 따르기
3. 각 작업 완료 후 항목 체크

### 예시 지시문
```
작업 시작 전에 `flow status`를 실행하고
체크리스트를 따르세요. 완료하는 대로
`flow check N`으로 항목을 체크하세요.
모든 항목이 확인될 때까지 다음 스테이지로
진행하지 마세요.
```

## 문제 해결

### "전이 불가" 오류
```bash
# 누락된 항목 확인
flow status

# 남은 항목 완료
flow check 3 4

# 다시 시도
flow next
```

### 상태 손상
```bash
# 알려진 상태로 리셋
flow set M0

# 또는 .workflow/state.json 직접 수정
```

### 플러그인 로드 오류
```bash
# workflow.yaml의 플러그인 경로 확인
# 모듈 임포트 가능 확인:
python -c "from workflow.plugins.fs import FileExistsValidator"
```

## 안티 패턴

### 하지 마세요:
- ❌ 정기적으로 `--force` 사용
- ❌ 작업 없이 모든 항목 체크
- ❌ USER-APPROVE 항목 건너뛰기
- ❌ `.workflow/secret`을 git에 커밋

### 하세요:
- ✅ 완료하는 대로 항목 체크
- ✅ 중요한 결정에 증거 추가
- ✅ 자주 `flow status` 실행
- ✅ 스테이지 순서 따르기

## 팀 사용

### 공유 구성
- `workflow.yaml`: git에 커밋
- `.workflow/state.json`: 개발자별 (gitignore)
- `.workflow/secret`: 개발자별 (gitignore)

### 일관된 프로세스
- 모든 팀원이 동일한 워크플로우 정의 사용
- 개별 상태로 병렬 작업 가능
- 리뷰 스테이지로 품질 게이트 보장

---

축하합니다! workflow-tool 튜토리얼을 완료했습니다.

추가 정보:
- 문서: `.memory/docs/`
- 구성: `workflow.yaml`
- 이슈: https://github.com/workflow-tool/workflow-tool/issues
