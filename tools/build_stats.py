#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""자격정보 서비스(Q-PAGE·Q-RADAR) 통합 방문 통계 생성기 — RADAR 레포 상주(tools/build_stats.py)
   매일 아침 GoatCounter 장부의 '일별 사본'을 stats-ledger/에 적층(전 기간 이력 자체 보존)하고,
   원장 + 당일 실시간분으로 관제판 stats-site/index.html을 조판한다. (열쇠·원장·생성은 모두 이 레포,
   Q-PAGE 배포는 산출물을 읽기만 해 /stats로 서빙 — 시크릿·쓰기권한 불요)
   사용: python tools/build_stats.py <Q-PAGE외부HTML> <출력dir> [--ledger stats-ledger] [--demo]
   env : GOATCOUNTER_TOKEN(필수) · GOATCOUNTER_TOKEN_RADAR(선택) · STATS_SINCE(기본 2026-11-04)"""
import io, re, json, os, sys, time, urllib.request, urllib.error, urllib.parse, datetime

SINCE = os.environ.get("STATS_SINCE", "2026-11-04")
SITES = [
    dict(label="Q-PAGE",  desc="자격정보집(상세·원페이지)", site="hrdk-q-page",  tok=["GOATCOUNTER_TOKEN"]),
    dict(label="Q-RADAR", desc="우대법령 네비게이터",       site="hrdk-q-radar", tok=["GOATCOUNTER_TOKEN_RADAR", "GOATCOUNTER_TOKEN"]),
]

def api(sitecfg, path):
    tok = next((os.environ[k] for k in sitecfg["tok"] if os.environ.get(k)), None)
    if not tok: raise RuntimeError("토큰 미설정")
    req = urllib.request.Request("https://%s.goatcounter.com/api/v0%s" % (sitecfg["site"], path),
        headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())

def pick(d, *keys, default=0):
    for k in keys:
        if isinstance(d, dict) and d.get(k) is not None: return d[k]
    return default

def fetch_day(sitecfg, day):
    """한국시간 하루치(00:00~23:59 KST) 경로별 집계.
    공식 규격: start/end는 '시간 단위로 끊은 시각', 집계는 양끝 포함(hour >= start AND hour <= end)
    → 00:00 KST ~ 23:00 KST(마지막 1시간 칸 포함)로 명시. 경로가 많으면 more/exclude_paths로 넘김.
    반환: (rows, 완결여부) — 미완결이면 원장에 확정하지 않는다."""
    span = "start=%s&end=%s&limit=100" % (urllib.parse.quote(day + "T00:00:00+09:00"),
                                         urllib.parse.quote(day + "T23:00:00+09:00"))
    rows, seen = [], []
    for _ in range(30):                                   # 안전 상한(100경로×30쪽)
        q = span + ("&exclude_paths=" + ",".join(seen) if seen else "")
        res = api(sitecfg, "/stats/hits?" + q)
        for h in pick(res, "hits", "paths", default=[]) or []:
            rows.append({"path": pick(h, "path", default=""),
                         "title": pick(h, "title", default=""),
                         "n": pick(h, "count", "count_unique", "visits", "total")})
            if h.get("path_id") is not None: seen.append(str(h["path_id"]))
        time.sleep(0.3)                                   # 초당 4회 제한 여유
        if not pick(res, "more", default=False):
            return rows, True
    return rows, False

def daterange(a, b):
    d = datetime.date.fromisoformat(a)
    while d <= b:
        yield d.isoformat(); d += datetime.timedelta(days=1)

def collect(sitecfg, now, ledger):
    """확정일은 원장(없으면 받아서 적층), 미확정일(오늘·자정 직후엔 어제까지)은 매번 실시간 수신.
    확정 기준: 한국시간 자정 후 1시간 유예(늦게 처리되는 집계 대비)가 지난 날만 원장에 굳힌다."""
    today = now.date()
    settle = (now - datetime.timedelta(hours=1)).date()   # 이 날짜 '이전'만 확정
    acc = {}; days = []
    def add(rows, day):
        q = {}
        for r in rows:
            m = re.fullmatch(r"/q/([0-9A-Z]{4})", r["path"])
            if m: q[m.group(1)] = q.get(m.group(1), 0) + r["n"]
        days.append({"d": day, "n": sum(r["n"] for r in rows), "q": q})
        for r in rows:
            k = r["path"]
            e = acc.setdefault(k, {"path": k, "title": r["title"], "n": 0})
            e["n"] += r["n"]
            if r["title"]: e["title"] = r["title"]
    ldir = None
    if ledger:
        ldir = os.path.join(ledger, sitecfg["site"]); os.makedirs(ldir, exist_ok=True)
    new = 0
    for day in daterange(SINCE, settle - datetime.timedelta(days=1)):
        fp = os.path.join(ldir, day + ".json") if ldir else None
        if fp and os.path.exists(fp):
            add(json.load(io.open(fp, encoding="utf-8")), day); continue
        rows, ok = fetch_day(sitecfg, day)
        if fp and ok:
            io.open(fp, "w", encoding="utf-8").write(json.dumps(rows, ensure_ascii=False)); new += 1
        add(rows, day)
    for day in daterange(settle.isoformat(), today):      # 미확정(실시간)
        add(fetch_day(sitecfg, day)[0], day)
    if new: print("  (%s: 일별 원장 %d일치 확정 적층)" % (sitecfg["label"], new))
    return sorted(acc.values(), key=lambda r: -r["n"]), days

def demo(sitecfg):
    import random; random.seed(42 if sitecfg["site"]=="hrdk-q-page" else 7)
    pool = ["6335","1530","2177","9542","1750","7785","7916","0752","3643","7301","0021","1320"]
    scale = 1.0 if sitecfg["site"]=="hrdk-q-page" else 0.4
    days=[]; acc={}
    for d,base in [(4,9),(5,21),(6,34),(7,18),(8,26),(9,41),(10,75)]:
        tot=int(base*scale)+1; q={}
        for _ in range(max(1,int(tot*0.75))):
            c=random.choice(pool); q[c]=q.get(c,0)+1
        days.append({"d":"2026-11-%02d"%d,"n":tot,"q":q})
        for c,n in q.items(): acc[c]=acc.get(c,0)+n
        acc["/"]=acc.get("/",0)+tot-sum(q.values())
    rows=[{"path":("/" if c=="/" else "/q/"+c),"title":"","n":max(n,0)} for c,n in acc.items()]
    return sorted(rows,key=lambda r:-r["n"]), days

def _load_page():
    """관제판 화면 템플릿 — 같은 폴더의 stats_template.html (디자인 수정은 그 파일에서)."""
    fp = os.path.join(HERE, "stats_template.html")
    tpl = io.open(fp, encoding="utf-8").read()
    assert "__DATA__" in tpl, "stats_template.html 에 __DATA__ 토큰이 없습니다"
    return tpl

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = None   # main()에서 로드

def main():
    src, out = sys.argv[1], sys.argv[2]
    ledger = sys.argv[sys.argv.index("--ledger") + 1] if "--ledger" in sys.argv else None
    H = io.open(src, encoding="utf-8").read()
    D = json.loads(re.search(r'<script id="qdata" type="application/json">(.*?)</script>', H, re.S).group(1))
    name = {i["code"]: i["name"] for i in D["items"]}
    etyp = {i["code"]: i["etype"] for i in D["items"]}
    KST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(KST); today = now.strftime("%Y-%m-%d")
    sites = []
    for sc in SITES:
        try:
            rows, days = demo(sc) if "--demo" in sys.argv else collect(sc, now, ledger)
            qs = []
            for r in rows:
                m = re.fullmatch(r"/q/([0-9A-Z]{4})", r["path"])
                if not m: continue
                c = m.group(1)
                nm = name.get(c) or (r["title"].split(" · ")[0] if r["title"] else c)
                qs.append(dict(c=c, nm=nm, et=etyp.get(c, ""), n=r["n"]))
            sites.append(dict(label=sc["label"], desc=sc["desc"], status="on",
                              total=sum(r["n"] for r in rows),
                              home=sum(r["n"] for r in rows if r["path"] == "/"),
                              qsum=sum(x["n"] for x in qs), qcnt=len(qs),
                              top=qs[:10], days=days))
        except Exception as e:
            print("  (%s: 집계 미수신 → 대기 표시 · %s)" % (sc["label"], type(e).__name__))
            sites.append(dict(label=sc["label"], desc=sc["desc"], status="wait"))
    nmap = {c: {"nm": name[c], "et": etyp.get(c, "")} for c in name}
    data = dict(since=SINCE, gen=now.strftime("%Y-%m-%d %H:%M"), sites=sites, nmap=nmap)
    html = _load_page().replace("__DATA__", json.dumps(data, ensure_ascii=False))
    os.makedirs(out, exist_ok=True)
    io.open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)
    print("[방문 통계] %d개 사이트 섹션 → %s/index.html" % (len(data["sites"]), out))

if __name__ == "__main__": main()
