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
```

## Next 명령어

다음 스테이지로 전이:

```bash
# 다음 스테이지 자동 감지
flow next

# 대상 스테이지 지정
flow next M1

# 강제 전이 (규칙 건너뜀)
flow next --force --reason "긴급 핫픽스 필요"
```

### 전이 오류

조건이 충족되지 않은 경우:
```
전이 불가: 모든 체크리스트 항목을 완료해야 합니다
남은 항목: 2, 3
```

## Set 명령어

스테이지 또는 모듈 수동 설정:

```bash
# 스테이지 설정
flow set M2

# 스테이지와 모듈 설정
flow set P3 --module inventory-system
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
