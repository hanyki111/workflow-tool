# 워크플로우 툴 독립화 가이드 (Standalone Guide)

이 문서는 `tools/workflow` 폴더에 있는 도구를 현재 프로젝트에서 완전히 분리하여 독립적인 라이브러리 또는 별도의 관리 프로젝트로 만드는 방법을 설명합니다.

## 1. 독립 프로젝트 구조 제안

도구를 독립시키려면 다음과 같은 구조를 권장합니다.

```
ai-workflow-engine/
├── workflow/               # tools/workflow 내부의 소스 코드
│   ├── core/
│   ├── plugins/
│   ├── templates/
│   └── __init__.py
├── tests/                  # 유닛 테스트
├── workflow.yaml.example   # 기본 설정 예시
├── setup.py                # 패키지 설치 설정
└── README.md
```

## 2. 분리 절차

### 단계 1: 코드 이동 및 구조화
1. 새로운 디렉토리를 생성하고 `tools/workflow/`의 모든 내용을 복사합니다.
2. `cli.py`를 `workflow/__main__.py`로 이름을 바꾸면 `python -m workflow`로 실행 가능해집니다.

### 단계 2: 의존성 관리
현재 도구는 `PyYAML` 외에 외부 의존성이 거의 없습니다. `requirements.txt`를 생성하세요.
```text
PyYAML>=6.0
```

### 단계 3: 절대 경로 임포트 수정
현재 `cli.py` 상단에는 다음과 같은 코드가 있습니다:
```python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
```
이를 제거하고, `core`, `plugins` 등의 내부 임포트를 **상대 임포트**(`.state`, `.auth` 등) 또는 **패키지 임포트**(`workflow.core.state`)로 수정해야 합니다.

### 단계 4: 설정 파일 분리
도구는 실행되는 위치의 `workflow.yaml`을 기본으로 읽도록 설계되어 있습니다. 이 설정을 유지하거나, 환경 변수(`WORKFLOW_CONFIG`)를 통해 설정 파일 위치를 지정할 수 있도록 `WorkflowController.__init__`을 수정하세요.

## 3. 다른 프로젝트에서 사용하는 방법

독립된 도구를 다른 프로젝트에서 사용하려면:

1. **패키지 설치**: `pip install -e /path/to/ai-workflow-engine`
2. **초기화 명령**: `flow init` 또는 `flow init --template full`
3. **생성되는 파일들**:
   - `workflow.yaml` - 워크플로우 정의
   - `.workflow/state.json` - 현재 상태
   - `.workflow/docs/PROJECT_MANAGEMENT_GUIDE.md` - 가이드 문서
   - `CLAUDE.md` - AI 에이전트 지침 (선택)

## 4. 향후 확장 제안

- **JSON Schema 지원**: `workflow.yaml`의 유효성을 편집기에서 즉시 확인할 수 있도록 스키마 제공.
- **REST API 서버**: 원격 에이전트가 HTTP를 통해 워크플로우 상태를 조회하고 리뷰를 남길 수 있는 서버 기능 추가.
- **UI 대시보드**: `status`를 텍스트가 아닌 웹 대시보드로 시각화.
