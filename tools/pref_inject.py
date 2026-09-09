#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pref_inject.py — 순정본 Q-Page HTML에 우대법령(pref_law) 오버레이 주입  [v1.1]
사용: python pref_inject.py <순정본.html> <pref_export.json> <출력.html> [--max-age-days 35]

계약(규격 v1.3.1 §3 + 부속서 A):
  · 명찰(qpage-master)만 읽어 연도·수록 종목을 판정 (화면 파싱 금지)
  · 검산 실패 시 exit 1 — 호출측은 순정본을 그대로 배포(폴백)
  · 주입 범위 = 종목별 "pref_law" 키 하나. 역제거 시 원본과 완전 동일(불변식 자체검증)
  · 과정평가형(코드 문자 시작)은 **명찰 안에서** 동일 종목명의 검정형 코드를 찾아
    그 코드의 데이터를 공유 주입하고, 딥링크용으로 그 검정형 코드를 src 로 함께 기록
    (v1.1: 외부 JSON 의 종목명에 의존하던 매칭을 명찰 내부 매칭으로 전환)"""
import json, re, sys, datetime

CATS = {'의무고용','직무권한','인사우대','시험면제'}

def die(msg): print('[주입 생략]', msg); sys.exit(1)

def main(html_path, json_path, out_path, max_age=35):
    html = open(html_path, encoding='utf-8').read()

    # 1) 명찰
    m = re.search(r'<script type="application/json" id="qpage-master">\s*(.*?)\s*</script>', html, re.S)
    if not m: die('명찰(qpage-master) 없음 — Z33 v1.5 이상 산출물인지 확인')
    plate = json.loads(m.group(1).replace('<\\/', '</'))
    if plate.get('version') != '1.0': die('명찰 version 비호환: %r' % plate.get('version'))
    pitems = plate['items']
    if plate.get('count') != len(pitems): die('명찰 count 불일치')
    year = plate.get('year')
    print(f'[명찰] year={year} · 수록 {len(pitems)}종목')

    # 2) 우대 데이터
    pref = json.loads(open(json_path, encoding='utf-8').read())
    if pref.get('version') != '1.0': die('pref version 비호환')
    asof = pref.get('asof', '')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', asof): die('asof 형식 위반: %r' % asof)
    age = (datetime.date.today() - datetime.date.fromisoformat(asof)).days
    if age > max_age:
        print(f'[경고] asof {asof} — {age}일 경과 (Q-Radar 게시 파이프라인 점검 필요)')
    for cd, it in pref['items'].items():
        n, c = it['n'], it['cat']
        if n != c['duty']+c['auth']+c['hr']+c['exempt'] or n <= 0: die(f'{cd} 건수 등식 위반')
        if len(it.get('top', [])) > 3: die(f'{cd} 대표 3건 초과')
        for t in it.get('top', []):
            if t['cat'] not in CATS: die(f'{cd} 성격 표기 위반: {t["cat"]}')

    # 3) 주입 계획 — 명찰 내부에서 판정(외부 종목명에 의존하지 않음)
    exam_byname = {}
    for cd, nm in pitems.items():
        if cd[:1].isdigit(): exam_byname.setdefault(nm, []).append(cd)
    plan, srcmap, shared, direct = {}, {}, 0, 0
    for cd, nm in pitems.items():
        if cd in pref['items']:
            plan[cd] = pref['items'][cd]; direct += 1
        elif not cd[:1].isdigit():
            sib = [x for x in exam_byname.get(nm, []) if x in pref['items']]
            if len(sib) == 1:
                plan[cd] = pref['items'][sib[0]]; srcmap[cd] = sib[0]; shared += 1
            elif len(sib) > 1:
                print(f'[정보] {cd}({nm}) 동명 검정형 {len(sib)}건 — 모호하여 제외')
    unmatched = sorted(set(pref['items']) - set(pitems))

    # 4) 문자 수술 주입
    out, inserted = html, []
    for cd, it in plan.items():
        anchor = '{"code":"%s",' % cd
        if out.count(anchor) != 1: die(f'주입 앵커 유일성 위반: {cd} ({out.count(anchor)}회)')
        payload = {'n': it['n'], 'cat': it['cat'], 'top': it.get('top', []), 'asof': asof}
        if cd in srcmap: payload['src'] = srcmap[cd]   # 과정평가형 딥링크용 검정형 코드
        frag = '"pref_law":' + json.dumps(payload, ensure_ascii=False, separators=(',',':')).replace('</','<\\/') + ','
        out = out.replace(anchor, anchor + frag, 1)
        inserted.append((cd, anchor, frag))

    # 5) 불변식: 역제거 == 원본 (위치 기반 정밀 제거)
    stripped = out
    for cd, anchor, frag in inserted:
        i = stripped.find(anchor)
        j = i + len(anchor)
        if stripped[j:j+len(frag)] != frag: die(f'불변식 검증 실패: {cd}')
        stripped = stripped[:j] + stripped[j+len(frag):]
    if stripped != html: die('불변식 위반 — 주입 외 변경 발생')

    # 6) 산출 JSON 유효성
    q = re.search(r'<script id="qdata" type="application/json">(.*?)</script>', out, re.S)
    data = json.loads(q.group(1))
    got = sum(1 for x in data['items'] if 'pref_law' in x)
    if got != len(plan): die(f'주입 수 불일치 {got}/{len(plan)}')

    open(out_path, 'w', encoding='utf-8').write(out)
    print(f'[성공] 주입 {len(plan)}종목 (직접 {direct} + 과정형 공유 {shared}) · asof {asof}')
    print(f'[정보] JSON에만 있고 화면({year}) 명찰에 없는 코드 {len(unmatched)}건: {unmatched[:10]}{"…" if len(unmatched)>10 else ""}')

if __name__ == '__main__':
    if len(sys.argv) < 4: die('사용: pref_inject.py <순정본.html> <pref.json> <출력.html> [--max-age-days N]')
    ma = 35
    if '--max-age-days' in sys.argv: ma = int(sys.argv[sys.argv.index('--max-age-days')+1])
    main(sys.argv[1], sys.argv[2], sys.argv[3], ma)
