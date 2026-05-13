# 컴백 일정 업데이트 워크플로우

namu.wiki 2026 가요계 페이지를 확인해 사내 아티스트 DB와 매칭되는 컴백/발매/데뷔/콘서트 일정을 Notion 캘린더에 자동 기록한다.

## 트리거

다음 중 하나로 실행 (모두 동일 작업):
- `/update-comebacks` (슬래시 커맨드)
- "업데이트" / "컴백 업데이트" / "노션 캘린더 업데이트"
- "namu.wiki 체크해서 노션 업데이트"

## 자원

| 항목 | 위치 |
|------|------|
| 소스 페이지 | https://namu.wiki/w/2026%EB%85%84%20%EA%B0%80%EC%9A%94%EA%B3%84 |
| 아티스트 DB | [data/artist-db.json](../../data/artist-db.json) — 그룹 175 + 멤버 1,017 |
| 추출 스크립트 | [scripts/extract_events.py](../../scripts/extract_events.py) |
| Notion 캘린더 | https://www.notion.so/35fd14538861808ca05bd440aa25b5a4 |
| Notion DB (data source) | `collection://35fd1453-8861-809f-afa2-000b1e9ccb55` |

### Notion DB 스키마

| 컬럼 | 타입 | 값 |
|------|------|-----|
| `Name` | title | **그룹명만** (앨범/멤버 정보는 본문에) |
| `Date` | date | ISO 형식 (YYYY-MM-DD) |
| `Tags` | multi_select | 컴백 · 발매 · 데뷔 · 콘서트 · 팬미팅 · OST · 예능 · 기타 |

## 실행 단계

### 1. 페이지 fetch

namu.wiki는 `WebFetch`가 403을 반환하므로 **curl + User-Agent**를 써야 한다:

```powershell
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36" `
  "https://namu.wiki/w/2026%EB%85%84%20%EA%B0%80%EC%9A%94%EA%B3%84" `
  -o "$env:TEMP/namu.html"
```

HTML을 plaintext로 변환 (Python으로 태그 제거).

### 2. 미래 이벤트 추출

`scripts/extract_events.py`를 실행하거나 동일 로직을 적용:
- `X월 Y일,` 마커로 텍스트를 분할
- 오늘 날짜 이후 이벤트만 필터
- 각 이벤트의 본문(snippet)을 보존

### 3. 아티스트 DB 매칭

**중요**: 자동 substring 매칭은 노이즈가 많다. 짧은 한글 멤버명("이정", "위시" 등)이 무관한 문맥에서 매칭되기 때문.

권장 방식:
1. 스크립트로 모든 미래 이벤트의 깔끔한 본문 추출
2. **Claude(AI)가 직접 본문을 읽고** `data/artist-db.json`과 대조해서 어떤 그룹이 실제로 언급되었는지 판단
3. 단순 substring 매칭에 의존하지 않음

DB에 없는 아티스트(예: HYNN, 씨야, BIGBANG, NCT WISH, 아이오아이, 보이프렌드, tripleS, USPEER 등)는 제외.

### 4. Notion 기존 항목 조회 (중복 제거)

```
notion-search(
  data_source_url: "collection://35fd1453-8861-809f-afa2-000b1e9ccb55"
)
```

중복 판정: **Name(그룹명) + Date 동일**시 스킵. 같은 그룹의 같은 날 활동은 한 페이지에 모음(본문에 추가 활동 기록).

### 5. 새 일정 추가

`notion-create-pages`로 일괄 추가:

```json
{
  "parent": {"type": "data_source_id", "data_source_id": "35fd1453-8861-809f-afa2-000b1e9ccb55"},
  "pages": [
    {
      "properties": {
        "Name": "에스파",
        "date:Date:start": "2026-05-29",
        "Tags": "[\"컴백\"]"
      },
      "content": "aespa가 정규 2집 《LEMONADE》를 발매할 예정.\n\n출처: [namu.wiki](https://namu.wiki/w/2026%EB%85%84%20%EA%B0%80%EC%9A%94%EA%B3%84)"
    }
  ]
}
```

규칙:
- **Name은 그룹명만** (앨범명, 멤버명 X)
- 멤버 솔로 활동도 소속 그룹명으로 기록 (예: NCT 태용 솔로 → Name="NCT")
- 활동 상세는 페이지 본문에
- 본문 끝에 namu.wiki 출처 링크 필수

### 6. 보고

사용자에게 보고:
- 매칭된 아티스트 수 / 새로 추가한 일정 수 (목록 포함)
- 중복으로 스킵한 수
- 매칭은 됐지만 날짜 불분명해서 제외한 항목

## 주의사항

- **추측 금지**: 페이지에 명시되지 않은 날짜는 건너뛰고 보고에만 포함
- **TBD/미정 제외**: "미정" 섹션의 항목은 날짜가 없으므로 추가 안 함
- **활동 종료/해체는 컴백 아님**: 예) DKZ 활동 종료 → 추가 안 함
- **여러 활동, 한 날짜**: 같은 그룹이 같은 날 여러 활동(예: 컴백 + 콘서트)이면 페이지 1개에 Tags 여러 개
- **API 실패 보고**: 실패한 항목은 명확히 보고

## 사용 도구

- `WebFetch` — namu.wiki 차단됨, curl 사용
- `Bash` (curl + Python) — 페이지 fetch + 텍스트 추출
- `Read` (data/artist-db.json) — 아티스트 DB 로드
- `mcp__notion-fetch` — 캘린더 페이지/DB 조회
- `mcp__notion-search` — 기존 항목 조회 (중복 제거)
- `mcp__notion-create-pages` — 새 일정 추가
- `mcp__notion-update-page` — 기존 항목 수정 (필요 시)

## 변경 이력

- 2026-05-13: 초기 셋업. 26개 일정(5/13~8/14) 첫 동기화 완료.
