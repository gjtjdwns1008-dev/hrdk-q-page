#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pref_csv2json.py — 채널 A CSV(14열) → pref_export.json (규격 v1.3.1 §2.2)
사용: python pref_csv2json.py <입력.csv> <출력.json>
검산: 14열 헤더, 건수=4성격 합, 표시값 4종, 대표 짝·채움 패턴, 기준일 형식.
실패 시 비영(exit 1) 종료 — 자동화 관문으로 사용 가능."""
import csv, io, json, sys, re, datetime

EXPECT = ['종목코드','종목명','건수','의무고용','직무권한','인사우대','시험면제',
          '대표1_법령','대표1_성격','대표2_법령','대표2_성격','대표3_법령','대표3_성격','기준일']
CATS = {'의무고용','직무권한','인사우대','시험면제'}
KEY  = {'의무고용':'duty','직무권한':'auth','인사우대':'hr','시험면제':'exempt'}

def die(msg): print('[실패]', msg); sys.exit(1)

def main(src, dst):
    raw = open(src,'rb').read()
    rows = list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    if rows[0] != EXPECT: die('헤더 불일치: %r' % rows[0][:5])
    body = [r for r in rows[1:] if any(x.strip() for x in r)]
    items, asof = {}, None
    for ln, r in enumerate(body, 2):
        if len(r) != 14: die(f'{ln}행 열 수 {len(r)}')
        cd, nm = r[0].strip(), r[1].strip()
        try: n,d,a,h,e = (int(x) for x in r[2:7])
        except ValueError: die(f'{ln}행 수치 열 형식')
        if n != d+a+h+e or n <= 0: die(f'{ln}행 건수 등식/양수 위반({cd})')
        if cd in items: die(f'{ln}행 코드 중복 {cd}')
        top, empty = [], False
        for law, cat in ((r[7],r[8]),(r[9],r[10]),(r[11],r[12])):
            law, cat = law.strip(), cat.strip()
            if (law=='') != (cat==''): die(f'{ln}행 대표 짝 불일치({cd})')
            if not law: empty = True; continue
            if empty: die(f'{ln}행 대표 중간 빈칸({cd})')
            if cat not in CATS: die(f'{ln}행 성격 표기 위반({cd}:{cat})')
            top.append({'law': law, 'cat': cat})
        if n > 0 and not top: die(f'{ln}행 대표1 누락({cd})')
        day = r[13].strip()
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day): die(f'{ln}행 기준일 형식({day})')
        if asof is None: asof = day
        elif asof != day: die(f'{ln}행 기준일 불일치')
        items[cd] = {'name': nm, 'n': n,
                     'cat': {'duty': d, 'auth': a, 'hr': h, 'exempt': e}, 'top': top}
    out = {'version': '1.0', 'asof': asof,
           'generated': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
           'source': 'HRDK Q-Radar', 'items': items}
    open(dst,'w',encoding='utf-8').write(json.dumps(out, ensure_ascii=False, separators=(',',':')))
    print(f'[성공] {len(items)}종목 · asof={asof} → {dst}')

if __name__ == '__main__':
    if len(sys.argv) != 3: die('사용: pref_csv2json.py <입력.csv> <출력.json>')
    main(sys.argv[1], sys.argv[2])
