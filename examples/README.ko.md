# 워크플로우 예시

이 디렉토리는 다양한 사용 사례와 복잡도 수준을 보여주는 워크플로우 구성 예시를 포함합니다.

---

## 디렉토리 구조

```
examples/
├── README.md                    # 영문 문서
├── README.ko.md                 # 이 파일 (한국어)
├── simple/                      # 최소 3단계 워크플로우
│   ├── workflow.yaml
│   ├── .workflow/
│   │   └── state.json
│   └── README.md / README.ko.md
├── full-project/                # 완전한 M0-M4, P1-P7 워크플로우
│   ├── workflow.yaml
│   ├── .workflow/
│   │   └── state.json
│   └── README.md / README.ko.md
└── custom-plugins/              # 커스텀 검증기 예시
    ├── workflow.yaml
    ├── .workflow/
    │   └── state.json
    ├── validators/
    │   └── custom.py
    └── README.md / README.ko.md
```

---

## 예시 설명

### 1. 간단한 워크플로우 (`simple/`)

**적합한 경우:** 소규모 프로젝트, 학습용, 빠른 작업

3단계만 있는 최소 워크플로우:
- `START` → `DEVELOP` → `DONE`

시연되는 기능:
- 기본 스테이지 정의
- 간단한 체크리스트
- 자동 전이

**사용해보기:**
```bash
cd examples/simple
flow status
flow check 1 2
flow next
```

---

### 2. 전체 프로젝트 워크플로우 (`full-project/`)

**적합한 경우:** 실제 소프트웨어 프로젝트, 팀 워크플로우

듀얼 트랙 워크플로우의 완전한 구현:

**마일스톤 스테이지:**
- M0: 기술 부채 검토
- M1: 마일스톤 계획
- M2: 마일스톤 논의
- M3: 브랜치 생성
- M4: 마일스톤 종료

**페이즈 스테이지 (각 페이즈마다 반복):**
- P1: 페이즈 계획
- P2: 페이즈 논의
- P3: 스펙
- P4: 구현
- P5: 테스팅
- P6: 셀프 리뷰
- P7: 페이즈 종료

시연되는 기능:
- 다단계 워크플로우 (마일스톤 + 페이즈)
- USER-APPROVE 항목
- 조건 재사용을 위한 룰셋
- 파일 및 명령어 검증기
- 서브 에이전트 리뷰 통합

**사용해보기:**
```bash
cd examples/full-project
flow status
flow tutorial --list
```

---

### 3. 커스텀 플러그인 (`custom-plugins/`)

**적합한 경우:** 고급 사용자, 특수 요구사항

커스텀 검증기 생성 및 사용 방법 시연:
- Git 브랜치 검증기
- 코드 커버리지 검증기
- API 헬스 체커

시연되는 기능:
- 커스텀 BaseValidator 서브클래스 생성
- workflow.yaml에 플러그인 등록
- 전이에서 플러그인 조건 사용
- 여러 검증기 조합

**사용해보기:**
```bash
cd examples/custom-plugins
flow status
# 구현 세부사항은 validators/custom.py 참조
```

---

## 예시 사용 방법

### 방법 1: 프로젝트에 복사

```bash
# 원하는 예시 복사
cp -r examples/simple/* /path/to/your/project/

# 이동 후 사용
cd /path/to/your/project
flow status
```

### 방법 2: 제자리에서 실행

```bash
# 예시 디렉토리로 이동
cd examples/full-project

# workflow.yaml이 자동 감지됨
flow status
```

### 방법 3: 학습용 참조

workflow.yaml 파일을 읽어 패턴 이해:
```bash
cat examples/simple/workflow.yaml
cat examples/full-project/workflow.yaml
```

---

## 커스터마이징 가이드

### simple부터 시작하기

1. `simple/`을 프로젝트에 복사
2. 프로세스에 맞게 스테이지 이름 수정
3. 필요에 맞게 체크리스트 조정
4. 필요에 따라 스테이지 추가

### full-project부터 시작하기

1. `full-project/`를 프로젝트에 복사
2. 마일스톤 관련 항목 이름 변경
3. 페이즈 체크리스트 조정
4. 필요에 따라 플러그인 활성화/비활성화

### 커스텀 워크플로우 만들기

1. 필요에 맞는 구조로 시작
2. 논리적 순서로 스테이지 추가
3. 의미 있는 체크리스트 정의 (스테이지당 3-7개 항목)
4. 적절한 조건으로 전이 설정
5. 자동화 검증을 위한 플러그인 추가

---

## 효과적인 워크플로우를 위한 팁

### 체크리스트 설계

**좋은 체크리스트:**
```yaml
checklist:
  - "새 함수에 대한 유닛 테스트 작성"
  - "린터 실행 및 모든 오류 수정"
  - "API 문서 업데이트"
```

**모호한 항목 피하기:**
```yaml
# 나쁨 - 너무 모호함
checklist:
  - "테스팅 하기"
  - "수정하기"
  - "작동하게 만들기"
```

### 전이 조건

**자동화를 위한 검증기 사용:**
```yaml
transitions:
  - target: "DEPLOY"
    conditions:
      - rule: shell
        args:
          cmd: "pytest"
        fail_message: "배포 전 테스트가 통과해야 합니다"
```

### USER-APPROVE의 전략적 배치

중요한 결정 포인트에 USER-APPROVE 배치:
```yaml
checklist:
  - "보안 영향 검토"
  - "성능 영향 확인"
  - "[USER-APPROVE] 프로덕션 배포 승인"
```

---

## 예시 문제 해결

### "workflow.yaml을 찾을 수 없음"

예시 디렉토리에 있는지 확인:
```bash
pwd  # examples/simple 또는 유사한 경로가 표시되어야 함
ls   # workflow.yaml이 보여야 함
```

### "상태 파일을 찾을 수 없음"

첫 명령어로 초기화:
```bash
flow status  # .workflow/state.json 생성됨
```

### 플러그인 임포트 오류

custom-plugins 예시의 경우 Python 경로 확인:
```bash
cd examples/custom-plugins
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
flow status
```

---

## 예시 기여하기

유용한 워크플로우 패턴이 있으신가요? 기여해주세요!

1. `examples/` 아래에 새 디렉토리 생성
2. 다음 파일 포함:
   - `workflow.yaml` - 워크플로우 구성
   - `.workflow/state.json` - 초기 상태
   - `README.md` - 설명 및 사용법
3. 어떤 문제를 해결하는지 문서화
4. Pull Request 제출

---

## 참고 자료

- 전체 문서는 메인 [README.md](../README.md) 참조
- 학습 자료는 [Tutorial](../workflow/tutorial/) 참조
- 전체 방법론은 [PROJECT_MANAGEMENT_GUIDE.md](../.memory/docs/PROJECT_MANAGEMENT_GUIDE.md) 참조
