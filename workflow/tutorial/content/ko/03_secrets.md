# 보안 및 비밀

일부 워크플로우 작업은 사용자 승인이 필요합니다. 이 섹션에서는 보안 시스템을 설명합니다.

## USER-APPROVE 항목

특정 체크리스트 항목은 `[USER-APPROVE]`로 표시됩니다:

```yaml
checklist:
  - "설계 문서 검토"
  - "[USER-APPROVE] 프로덕션 배포 승인"
  - "문서 업데이트"
```

이러한 항목은 체크하려면 비밀 토큰이 필요하며, 사람이 명시적으로 해당 작업을 승인했음을 보장합니다.

## 비밀 설정

### 비밀 생성

```bash
flow secret-generate
```

대화형 프롬프트:
```
비밀 문구를 입력하세요: ********
비밀 문구 확인: ********

비밀 해시가 .workflow/secret에 저장됨
USER-APPROVE 항목에 --token 플래그와 함께 이 비밀을 사용하세요
```

### 보안 참고사항

1. **비밀은 해시됨**: 평문이 아닌 SHA-256 해시만 저장됩니다
2. **비공개 유지**: `.workflow/secret`을 git에 커밋하지 마세요
3. **문구 기억**: 복구 메커니즘이 없습니다

## 토큰 사용

USER-APPROVE 항목 체크 시:

```bash
# 토큰 없이는 실패
flow check 2
# 오류: 항목 2는 USER-APPROVE 토큰 필요

# 토큰 제공
flow check 2 --token "your-secret-phrase"
# 성공: 체크된 항목: 2
```

## 감사 추적

모든 USER-APPROVE 작업은 기록됩니다:

```bash
cat .workflow/audit.log
```

로그 예시:
```
2024-01-15T10:30:00 USER-APPROVE 항목 2 체크 (프로덕션 배포)
2024-01-15T10:30:00 증거: 보안팀 검토 완료
```

## 모범 사례

1. **강력한 비밀 사용**: 길고 무작위한 문구
2. **공유 금지**: 각 팀원은 자신만의 비밀을 가져야 함
3. **주기적 교체**: 장기 프로젝트의 경우 새 비밀 생성
4. **증거 추가**: 승인 이유 문서화

```bash
flow check 2 --token "secret" --evidence "@alice의 보안 검토 후 승인"
```

## Gitignore 설정

`.gitignore`에 추가:
```
.workflow/secret
.workflow/audit.log
```

다음: 고급 기능을 배워봅시다!
