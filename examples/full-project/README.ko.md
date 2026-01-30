# 전체 프로젝트 워크플로우 예시

PROJECT_MANAGEMENT_GUIDE 방법론을 완전히 구현한 듀얼 트랙 워크플로우입니다.

## 개요

이 워크플로우는 두 가지 트랙 시스템을 구현합니다:

### 마일스톤 트랙 (M0-M4)
전체 마일스톤에 걸친 고수준 프로젝트 단계:

```
M0 (기술 부채) → M1 (계획) → M2 (논의) → M3 (브랜치)
                                                ↓
                    ┌───────────────────────────┘
                    ↓
              [페이즈 루프]
                    ↓
              M4 (종료)
```

### 페이즈 트랙 (P1-P7)
각 페이즈마다 반복되는 상세 구현 단계:

```
P1 (계획) → P2 (논의) → P3 (스펙) → P4 (구현)
                                        ↓
P7 (종료) ← P6 (리뷰) ← P5 (테스팅) ←───┘
```

## 스테이지 상세

### 마일스톤 스테이지

| 스테이지 | 목적 | 주요 활동 |
|---------|------|----------|
| M0 | 기술 부채 검토 | 기존 부채 평가, 수정 우선순위 결정 |
| M1 | 마일스톤 계획 | PRD 작성, 범위 정의, 작업 추정 |
| M2 | 마일스톤 논의 | 아키텍처 검토, 사용자 승인 획득 |
| M3 | 브랜치 생성 | Git 설정, 기능 브랜치 생성 |
| M4 | 마일스톤 종료 | 머지, 문서화, 배포 |

### 페이즈 스테이지

| 스테이지 | 목적 | 주요 활동 |
|---------|------|----------|
| P1 | 페이즈 계획 | PRD 검토, 산출물 정의 |
| P2 | 페이즈 논의 | 기술 설계, 사용자 승인 |
| P3 | 스펙 | 기술 사양서 작성 |
| P4 | 구현 | 코드 구현 |
| P5 | 테스팅 | 유닛 테스트, 통합 테스트 |
| P6 | 셀프 리뷰 | 코드 품질 검사 |
| P7 | 페이즈 종료 | 문서 동기화, 커밋 |

## 시연되는 기능

### 1. USER-APPROVE 항목

중요한 결정은 사람의 검증이 필요:

```yaml
checklist:
  - "[USER-APPROVE] 마일스톤 계획 승인"
```

사용법:
```bash
flow secret-generate              # 최초 설정
flow check 3 --token "secret"     # 검증과 함께 체크
```

### 2. 룰셋

재사용 가능한 조건 그룹:

```yaml
rulesets:
  ready_for_next:
    - rule: all_checked
    - rule: user_approved
```

### 3. 파일 검증기

필수 파일 존재 확인:

```yaml
conditions:
  - rule: fs
    args:
      path: "docs/spec.md"
      not_empty: true
```

### 4. 명령어 검증기

테스트 검증 자동화:

```yaml
conditions:
  - rule: shell
    args:
      cmd: "pytest tests/"
      expect_code: 0
```

## 사용법

```bash
# 이 디렉토리로 이동
cd examples/full-project

# 현재 상태 확인 (M0에서 시작)
flow status

# 기술 부채 검토 진행
flow check 1
flow check 2
flow check 3 --token "your-secret"  # USER-APPROVE
flow next

# 마일스톤 스테이지 계속 진행
flow status  # 이제 M1
# ... 체크리스트 따라가기
```

## 일반적인 워크플로우 세션

### 세션 1: 새 마일스톤 시작

```bash
# 상태 확인
flow status
# 출력: M0 (Tech Debt Review)

# 기술 부채 검토 완료
flow check 1 --evidence "모든 모듈 검토, 3개 부채 항목 발견"
flow check 2 --evidence "우선순위: 인증 버그 수정, DB 레이어 리팩토링"
flow check 3 --token "secret" --evidence "부채 계획 승인됨"
flow next

# 마일스톤 계획 생성
flow status  # M1 (Milestone Planning)
flow check 1 --evidence "m24-user-auth.md 생성됨"
flow check 2
flow check 3
flow next
```

### 세션 2: 아키텍처 검토

```bash
flow status  # M2 (Milestone Discussion)
flow check 1 --evidence "OAuth2 플로우 다이어그램 발표"
flow check 2 --evidence "Pre-mortem과 Devil's Advocate 적용"
flow check 3
flow check 4 --token "secret" --evidence "사용자가 아키텍처 승인"
flow next
```

### 세션 3: 구현 페이즈

```bash
flow status  # P1 (Phase Planning)
# ... 각 페이즈에 대해 P1-P7 진행
```

## 커스터마이징

### 팀에 맞게 조정

1. 팀 용어에 맞게 스테이지 레이블 수정
2. 필요에 따라 체크리스트 항목 추가/제거
3. 도구에 맞게 플러그인 활성화/비활성화

### 소규모 프로젝트용 간소화

일부 페이즈 스테이지가 과도하면 제거:
- 유지: P1, P4, P5, P7
- 선택: P2, P3, P6

### 프로젝트별 검증기 추가

```yaml
plugins:
  coverage: "myproject.validators.CoverageValidator"

stages:
  P5:
    transitions:
      - target: "P6"
        conditions:
          - rule: coverage
            args:
              minimum: 80
```

## 파일 구성

- `workflow.yaml` - 완전한 워크플로우 구성
- `.workflow/state.json` - 현재 상태
- `.workflow/secret` - USER-APPROVE용 비밀 해시 (`flow secret-generate`로 생성)

## 팁

1. **M0 건너뛰지 않기**: 기술 부채 검토가 부채 누적 방지
2. **증거 사용하기**: `--evidence`가 감사 추적 생성
3. **USER-APPROVE 전략적 배치**: 중요한 결정에만 사용
4. **페이즈 완전히 완료하기**: P6(리뷰)와 P7(종료) 서두르지 않기

## 관련 문서

- [PROJECT_MANAGEMENT_GUIDE.md](../../.memory/docs/PROJECT_MANAGEMENT_GUIDE.md)
- [ARCHITECTURE.md](../../.memory/docs/ARCHITECTURE.md)
