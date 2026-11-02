#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Q-PAGE A3 원페이지 일괄 생성기 (tools/build_sheets.py)
   조판 로직은 build_sheet.py(단일 진실원천) 하나만 쓰고,
   이 파일은 652종 루프·A3 1페이지 PDF·검산만 맡는다.
   사용:  python tools/build_sheets.py <외부HTML> <출력폴더> [--codes 6335,1530] [--check-list 목록파일]"""
import io, re, json, sys, os, time, argparse

HERE = os.path.dirname(os.path.abspath(__file__))

def load_core():
    src = io.open(os.path.join(HERE, 'build_sheet.py'), encoding='utf-8').read()
    # 입력 3줄(경로 인자·파일 읽기·JSON 파싱)을 주입 변수로 치환 → 652회 재파싱 제거
    src = re.sub(r"SRC = sys\.argv.*?\n", "SRC = None\n", src, count=1)
    src = re.sub(r"CODE = sys\.argv.*?\n", "CODE = __CODE__\n", src, count=1)
    src = re.sub(r"H = io\.open\(SRC.*?\n", "H = None\n", src, count=1)
    src = re.sub(r"D = json\.loads\(.*?\n", "D = __D__\n", src, count=1)
    src = src[:src.index("out=f'sheet_")]          # 꼬리(파일 저장부) 절단 — html 변수까지만
    assert "sheet_{" not in src
    assert '__CODE__' in src and '__D__' in src, '치환 실패'
    return compile(src, 'build_sheet.py', 'exec')

def render(core, D, code):
    g = {'__CODE__': code, '__D__': D}
    exec(core, g)
    return g['html']

def fname(x, year):
    tag = '_과정평가형' if x['etype'] == '과정형' else ''
    return f"{x['code']}_{x['name']}{tag}_{year}년 분석자료.pdf"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('html'); ap.add_argument('out', nargs='?', default='pdf_out')
    ap.add_argument('--codes'); ap.add_argument('--check-list'); ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    H = io.open(a.html, encoding='utf-8').read()
    D = json.loads(re.search(r'<script id="qdata" type="application/json">(.*?)</script>', H, re.S).group(1))
    items = D['items']; year = D['meta']['base_year']
    core = load_core()
    sel = [i for i in items if (not a.codes) or i['code'] in a.codes.split(',')]

    # ── 파일명 전수 대조(선택) ──
    if a.check_list:
        want = {os.path.basename(l.strip()) for l in io.open(a.check_list, encoding='utf-8') if l.strip()}
        mine = {fname(x, year) for x in items}
        only_w, only_m = sorted(want - mine), sorted(mine - want)
        print(f"[파일명 대조] 기존 {len(want)} vs 생성규칙 {len(mine)} | 기존에만: {len(only_w)} {only_w[:3]} | 규칙에만: {len(only_m)} {only_m[:3]}")

    # ── 건식(렌더만) 전수 검사 ──
    t0 = time.time(); fails = []
    pages_html = {}
    for x in sel:
        try: pages_html[x['code']] = render(core, D, x['code'])
        except Exception as e: fails.append((x['code'], repr(e)[:80]))
    print(f"[건식 렌더] {len(sel)-len(fails)}/{len(sel)} 성공 · {time.time()-t0:.1f}s" + (f" | 실패 {fails[:5]}" if fails else ""))
    if fails: sys.exit(1)
    if a.dry: return

    # ── A3 1페이지 PDF (make_pdf.py 검증 공식 이식 · 브라우저 1회 기동) ──
    import subprocess
    from playwright.sync_api import sync_playwright
    os.makedirs(a.out, exist_ok=True)
    PAPER = 420/25.4*96                      # A3 세로 높이의 px (≈1587)
    def pages(f):
        r = subprocess.run(['pdfinfo', f], capture_output=True, text=True).stdout
        return int([l for l in r.splitlines() if l.startswith('Pages')][0].split()[-1])
    bad1p = []; t0 = time.time()
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        for k, x in enumerate(sel, 1):
            pg.set_content(pages_html[x['code']], wait_until='load'); pg.wait_for_timeout(60)
            h = pg.evaluate("document.querySelector('.sheet').scrollHeight")
            s = min(1.0, round(PAPER/h*0.99, 3))
            out = os.path.join(a.out, fname(x, year))
            for _ in range(6):
                if s < 1.0:
                    pg.add_style_tag(content=f'.sheet{{width:{297/s:.2f}mm !important;min-height:0 !important;height:auto !important}}')
                    pg.wait_for_timeout(100)
                pg.pdf(path=out, width='297mm', height='420mm', print_background=True, scale=s,
                       margin={'top':'0','bottom':'0','left':'0','right':'0'})
                if pages(out) == 1: break
                s = round(s - 0.008, 3)
            else: bad1p.append(x['code'])
            if k % 50 == 0: print(f"  …{k}/{len(sel)} ({time.time()-t0:.0f}s)")
        b.close()
    made = len([f for f in os.listdir(a.out) if f.endswith('.pdf')])
    dt = time.time() - t0
    print(f"[변환 결과] PDF {made}/{len(sel)}장 · {dt:.0f}s ({dt/max(len(sel),1):.2f}s/장)" + (f" | 1페이지 실패: {bad1p}" if bad1p else " | 전수 1페이지 ✓"))
    if bad1p or made != len(sel): sys.exit(1)

if __name__ == '__main__': main()
