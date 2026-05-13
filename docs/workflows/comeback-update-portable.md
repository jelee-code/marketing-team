# 컴백 일정 자동 업데이트 워크플로우 (포터블 버전)

namu.wiki의 연도별 가요계 페이지를 모니터링해서 사내 아티스트 DB와 매칭되는 컴백/발매/데뷔/콘서트 일정을 Notion 캘린더에 자동 기록하는 워크플로우. 다른 팀/조직에서도 동일하게 적용 가능하도록 작성됨.

## 사전 요구사항

### MCP 커넥터
- **Notion MCP**: 캘린더 DB 읽기/쓰기. https://claude.ai/customize/connectors 에서 설치
  - 필요 도구: `notion-fetch`, `notion-search`, `notion-create-pages`, `notion-update-page`, `notion-update-data-source`
- **WebFetch**: namu.wiki 페이지 가져오기 (기본 제공)

### 자원
1. **소스 페이지**: 원하는 namu.wiki 페이지 URL (예: `https://namu.wiki/w/2026%EB%85%84%20%EA%B0%80%EC%9A%94%EA%B3%84`)
2. **아티스트 DB 파일**: 매칭 대상 그룹/멤버 목록 → **사용자에게 요청 필요** (아래 설명)
3. **Notion 캘린더 데이터베이스**: 일정을 기록할 Notion DB

## 초기 셋업 (1회만 실행)

### Step 1. 아티스트 DB 확보

사용자에게 아티스트/그룹 목록 파일을 요청한다. 다음 중 어느 형태든 가능:
- xlsx/csv: 그룹명, 영문명, 검색어 컬럼이 있는 스프레드시트
- JSON: 이미 정리된 형식
- 텍스트 목록: "그룹명 (영문명) - 검색어1, 검색어2..." 같은 형식

요청 예시:
> "매칭할 아티스트 목록 파일을 알려주세요. 그룹명/영문명/별칭(검색어)이 포함된 형식이면 됩니다."

받은 파일을 다음 JSON 스키마로 정규화해서 repo의 `data/artist-db.json`에 저장:

```json
{
  "meta": {
    "source": "원본 파일명",
    "group_count": 175,
    "member_count": 1017
  },
  "groups": [
    {
      "id": 1,
      "nameKR": "에스파",
      "nameEN": "aespa",
      "nameShort": "aespa",
      "searchTerms": "에스파 aespa"
    }
  ],
  "members": [
    {
      "id": 1,
      "nameKR": "카리나",
      "nameEN": "KARINA",
      "group": "에스파",
      "searchTerms": "카리나 KARINA"
    }
  ]
}
```

### Step 2. Notion 캘린더 DB 확인/생성

사용자가 캘린더로 쓸 Notion 페이지 또는 DB URL을 받는다. `notion-fetch`로 조회해서:

**DB가 이미 있으면**: 스키마 확인 후 부족한 필드 추가
**DB가 없으면**: `notion-update-data-source` 또는 페이지에 새 inline DB 생성

표준 스키마:
| 컬럼 | 타입 | 용도 |
|------|------|------|
| `Name` | title | 그룹명 (앨범/멤버 정보는 페이지 본문에) |
| `Date` | date | 활동 일자 (ISO 형식) |
| `Tags` | multi_select | 컴백 · 발매 · 데뷔 · 콘서트 · 팬미팅 · OST · 예능 · 기타 |

Tags 옵션이 없으면 추가:
```
notion-update-data-source(
  data_source_id: "<DB_ID>",
  statements: "ALTER COLUMN \"Tags\" SET MULTI_SELECT('컴백':red, '발매':orange, '데뷔':yellow, '콘서트':green, '팬미팅':blue, 'OST':purple, '예능':pink, '기타':gray)"
)
```

### Step 3. 환경 변수 기록

이후 실행 시 참조할 ID를 워크플로우 문서나 메모리에 기록:
- `NAMU_URL`: namu.wiki 페이지 URL
- `NOTION_DATA_SOURCE_ID`: 캘린더 DB의 `collection://...` ID
- `ARTIST_DB_PATH`: `data/artist-db.json`

## 정기 실행 절차

### 1. 페이지 fetch

```
WebFetch(
  url: "<NAMU_URL>",
  prompt: "Extract all dated future events from this page. For each: artist/group name (as written), date (YYYY-MM-DD), event type (컴백/발매/데뷔/콘서트/팬미팅/OST/예능/기타), brief description. Skip TBD/미정 entries. JSON array."
)
```

### 2. 미래 이벤트 필터링

오늘 날짜 이후 일정만 남긴다. 활동 종료/해체 같은 비-컴백 항목은 제외.

### 3. 아티스트 DB 매칭

`data/artist-db.json`을 읽고, 각 이벤트의 본문에 언급된 아티스트가 우리 DB의 `groups[]` 또는 `members[]`에 있는지 확인.

**중요**: 자동 substring 매칭은 노이즈가 많다 (짧은 한글 이름이 무관한 문맥에서 매칭됨). Claude가 직접 본문을 읽고 판단하는 방식을 권장.

매칭 결과를 사용자에게 미리보기로 보여주고 확인받기.

### 4. Notion 중복 제거

```
notion-search(
  data_source_url: "collection://<NOTION_DATA_SOURCE_ID>"
)
```

기존 항목과 비교해서 **Name + Date 동일**시 스킵.

### 5. 새 일정 추가

```
notion-create-pages(
  parent: {"type": "data_source_id", "data_source_id": "<NOTION_DATA_SOURCE_ID>"},
  pages: [
    {
      properties: {
        "Name": "에스파",
        "date:Date:start": "2026-05-29",
        "Tags": "[\"컴백\"]"
      },
      content: "aespa가 정규 2집 《LEMONADE》를 발매할 예정.\n\n출처: [namu.wiki](<NAMU_URL>)"
    }
  ]
)
```

**기록 규칙**:
- `Name`은 **그룹명만** (앨범명, 멤버명 X)
- 멤버 솔로 활동도 소속 그룹명으로 (예: NCT 태용 솔로 → `Name="NCT"`)
- 활동 상세는 페이지 본문에
- 본문 끝에 namu.wiki 출처 링크 필수

### 6. 보고

사용자에게:
- 추가한 항목 수 + 목록
- 중복으로 스킵한 수
- 매칭됐지만 날짜 불분명으로 제외한 항목

## 자동화 (선택)

### 옵션 A: 매시간 원격 자동 실행

`/schedule` (RemoteTrigger)로 cron 루틴 생성:

```json
{
  "name": "컴백 캘린더 자동 업데이트",
  "cron_expression": "0 * * * *",
  "enabled": true,
  "job_config": {
    "ccr": {
      "environment_id": "<ENV_ID>",
      "session_context": {
        "model": "claude-sonnet-4-6",
        "sources": [{"git_repository": {"url": "<REPO_URL>"}}],
        "allowed_tools": ["Bash", "Read", "WebFetch"]
      },
      "events": [
        {
          "data": {
            "uuid": "<new-uuid>",
            "session_id": "",
            "type": "user",
            "parent_tool_use_id": null,
            "message": {
              "content": "이 워크플로우 문서(docs/workflows/comeback-update-portable.md)를 읽고 그대로 실행. 보고는 생략하고 Notion에만 기록.",
              "role": "user"
            }
          }
        }
      ]
    }
  },
  "mcp_connections": [
    {"connector_uuid": "<NOTION_CONNECTOR_UUID>", "name": "notion", "url": "https://mcp.notion.com/..."}
  ]
}
```

매시간 정각(UTC)에 자동 실행. PC가 꺼져 있어도 작동.

### 옵션 B: 수동 트리거 (슬래시 커맨드)

`.claude/commands/update-comebacks.md` 파일 생성:

```markdown
---
description: namu.wiki → 아티스트 DB 매칭 → Notion 캘린더 자동 기록
---

docs/workflows/comeback-update-portable.md 워크플로우를 실행한다.
```

이후 Claude Code에서 `/update-comebacks` 입력으로 실행.

### 옵션 C: 키워드 트리거

메모리에 다음 feedback 저장:
- 사용자가 "업데이트", "컴백 업데이트", "캘린더 업데이트" 등을 말하면 워크플로우 자동 실행

## 주의사항

- **추측 금지**: 페이지에 명시되지 않은 날짜는 추가하지 않음
- **TBD/미정 제외**: 날짜가 없는 항목은 건너뜀
- **활동 종료/해체는 컴백 아님**: 그룹 해산, 멤버 탈퇴 같은 사항은 캘린더에 추가하지 않음
- **다국어 매칭**: namu.wiki는 한글/영문 표기가 혼재하므로 DB의 `searchTerms`에 모든 변형 포함시킬 것
- **첫 실행 시 검토 필수**: 매칭 결과를 사용자에게 보여주고 확인받은 후 Notion에 기록

## 확장 아이디어

- 다른 연도 페이지 (예: 2027년 가요계)도 동시 모니터링
- 콘서트/페스티벌 전용 페이지 추가 매칭
- Notion에 기록 후 Slack/Discord 웹훅으로 팀 알림
- 이미 지난 일정 자동 아카이브
