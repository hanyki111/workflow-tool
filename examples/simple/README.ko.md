# 간단한 워크플로우 예시

소규모 프로젝트나 학습 목적을 위한 최소한의 3단계 워크플로우입니다.

## 개요

```
START → DEVELOP → DONE
```

이 워크플로우는 의도적으로 단순합니다:
- **START**: 프로젝트 초기화
- **DEVELOP**: 구현 작업
- **DONE**: 완료 및 마무리

## 파일 구성

- `workflow.yaml` - 워크플로우 구성
- `.workflow/state.json` - 현재 상태

## 사용법

```bash
# 이 디렉토리로 이동
cd examples/simple

# 현재 상태 확인
flow status

# 출력:
# Current Stage: START (Project Start)
# ========================================
# 1. [ ] Define project scope
# 2. [ ] Set up development environment
# 3. [ ] Create initial file structure

# 항목 완료
flow check 1 2 3

# 다음 스테이지로 이동
flow next

# DEVELOP 스테이지 진행
flow status
flow check 1 2 3
flow next

# 워크플로우 완료
flow status
flow check 1 2
flow next
```

## 커스터마이징 아이디어

### 리뷰 스테이지 추가

```yaml
stages:
  # ... 기존 스테이지 ...

  REVIEW:
    id: "REVIEW"
    label: "Code Review"
    checklist:
      - "셀프 리뷰 완료"
      - "피어 리뷰 요청"
      - "[USER-APPROVE] 리뷰어 승인"
    transitions:
      - target: "DONE"
```

### 자동화 테스트 추가

```yaml
plugins:
  shell: "workflow.plugins.shell.CommandValidator"

stages:
  DEVELOP:
    transitions:
      - target: "DONE"
        conditions:
          - rule: all_checked
          - rule: shell
            args:
              cmd: "pytest tests/"
            fail_message: "테스트가 통과해야 합니다"
```

### 파일 검사 추가

```yaml
plugins:
  fs: "workflow.plugins.fs.FileExistsValidator"

stages:
  DONE:
    checklist:
      - "README 업데이트"
      - "변경 로그 추가"
    transitions:
      - target: "START"  # 다음 반복을 위해 돌아감
        conditions:
          - rule: fs
            args:
              path: "README.md"
              not_empty: true
```

## 이 예시를 사용할 때

- 워크플로우 도구 학습
- 작은 스크립트나 유틸리티
- 빠른 프로토타입
- 1인 개발 프로젝트

더 큰 프로젝트는 `examples/full-project/`를 참조하세요.
