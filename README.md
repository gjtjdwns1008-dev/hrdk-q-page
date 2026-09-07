# 국가기술자격 Q-Page 자격정보집

국가기술자격 652종목(검정형 545 · 과정평가형 107)의 응시·취득·취업·임금 통계를
종목당 한 화면으로 제공하는 대국민 채널.
다이렉트 링크 : <https://gjtjdwns1008-dev.github.io/hrdk-q-page/>

## 구조

```
q-page-outside_YYYY-MM-DD.html      외부공개 화면(단일 파일, 자료 내장).
                                    날짜가 가장 최신인 파일이 자동으로 홈(index)에 배포된다.
pdf/                                종목별 화면 PDF. 파일명 = 종목코드.pdf (외부용 시트 출력물만)
tools/
  pdf_to_png.py                     pdf/ → PNG 변환기 (pdftoppm+pngquant, 없으면 PyMuPDF 폴백)
robots.txt                          검색엔진 수집 차단(시범 기간). 공식 전환 때 삭제.
.github/workflows/
  build-qpage.yml                   배포 지시서: 최신 외부공개본을 홈으로 배포
  keepalive.yml                     월 1회 심장박동(저장소 활동 유지용 커밋)
```

## 배포가 도는 시점 (v2)

- `q-page-outside_*.html` 이 올라올 때 **한 번** 돈다. ← 유일한 자동 방아쇠
- **pdf/ 업로드는 배포를 일으키지 않는다.** 깃허브 웹은 한 번에 100개까지만
  올라가므로 PDF를 여러 번 나눠 올려도 조용하다. 다 올린 뒤 HTML을 올리면
  그때 한 번만 돌고, HTML 변경 없이 PDF만 갱신했다면 Actions 탭에서
  수동 실행(Run workflow) 한 번.
- 삭제 커밋: 깃허브 감시는 삭제에도 이벤트를 띄우지만, 문지기(gate)가
  "삭제만 있는 커밋"이면 10초 만에 본작업을 생략한다(변환·배포 없음).
  최신본을 지워 이전 날짜본으로 되돌리려면 수동 실행(Run workflow) 1회.

## 규약·안전장치

- `dist/` 와 PNG는 커밋하지 않는다(Actions 빌드 산출물).
  변환된 PNG 주소: `https://<계정>.github.io/<저장소>/sheets/종목코드.png`
- 과거 날짜의 `q-page-outside_*.html` 은 지우지 않아도 된다(연도별 보관함).
- **안전장치**: `q-page-inside*` 또는 `*내부용*.html` 이 발견되면 배포가
  강제 중단된다. 실수로 올렸다면 삭제 커밋 후 Actions 에서 Re-run.
- **keepalive**: 갱신이 연 1회라 저장소가 오래 조용하면 깃허브가 예약
  워크플로를 끈다(60일 규정). 월 1회 날짜 파일 커밋으로 활동을 유지한다.

## 연간 갱신 순서

1. 엑셀: 새 연도 파일 만들기 → 입력파일 내보내기 → 불러오기 → 순위·평균 다시 계산
2. One-page(외부용) 시트에서 종목별 PDF 일괄 생성 → `pdf/` 에 **먼저** 업로드
   (100개씩 나눠 올려도 됨 — 이 단계에서는 배포가 돌지 않는다)
3. 리본 **[외부공개 HTML]** → `out\q-page-outside_날짜.html` 생성
4. 그 파일을 저장소 루트에 **마지막으로** 업로드 → 배포가 한 번 돌며 전부 반영
5. Actions 요약에서 "홈(index)으로 배포된 파일"과 PNG 변환 실패 0건 확인

## 사전 1회 설정

깃허브 웹에서 Settings → Pages → Source = **GitHub Actions** 로 지정.
그 외 설정·비밀키 없음.
