# -*- coding: utf-8 -*-
"""A3 원페이지(외부용) 웹 재현 시안 — 종목 1건(6335 가스기능사).
데이터 원천: live.html 내장 jsonEx(원장→Z33 산출). 구멍 3건은 [보강] 표식."""
import io, re, json, math, sys

SRC = sys.argv[1] if len(sys.argv)>1 else '/mnt/user-data/uploads/q-page-outside_2026-11-02_1.html'
CODE = sys.argv[2] if len(sys.argv)>2 else '6335'
H = io.open(SRC, encoding='utf-8').read()
D = json.loads(re.search(r'<script id="qdata" type="application/json">(.*?)</script>', H, re.S).group(1))
X = next(i for i in D['items'] if i['code'] == CODE)
M = D['meta']

def n(v):  return '-' if v is None else f'{v:,.0f}' if isinstance(v,(int,float)) else str(v)
def p1(v): return '-' if v is None else f'{v*100:.1f}%'
def esc(s): return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

PAL = ['#4472C4','#ED7D31','#A5A5A5','#FFC000','#5B9BD5','#70AD47','#264478','#9E480E','#636363','#997300']
FIX = '<span class="fix">보강{}</span>'   # 회색 표식(캡션용)
FX2 = '<span class="fix fx2">보{}</span>'    # 표 안 축약형

# ───────── 공용 조각 ─────────
def stackbar(items, total, h=13):
    top=set(sorted(range(len(items)), key=lambda k:-items[k][1])[:2])   # 비중 상위 2개
    seg=''; left=0.0
    for i,(lab,v) in enumerate(items):
        w = 0 if not total else v/total*100
        if w<=0: continue
        txt = f'<b>{esc(lab)}</b>' if (i in top and w>=6) else ''
        seg += f'<i style="left:{left:.3f}%;width:{w:.3f}%;background:{PAL[i%len(PAL)]}">{txt}</i>'
        left += w
    return f'<div class="sb" style="height:{h}px">{seg}</div>'

def mrow(title, dist, extra_cols=None, bar=True):
    """설문 행렬 1블록: 제목셀 | (막대) | 라벨/인원/비율 표"""
    items=dist['i']; t=dist['t']
    labs=''.join(f'<th>{esc(l)}</th>' for l,_ in items)+'<th class="tt">총계</th>'
    nums=''.join(f'<td>{n(v)}</td>' for _,v in items)+f'<td class="tt">{n(t)}</td>'
    rats=''.join(f'<td>{p1(v/t) if t else "-"}</td>' for _,v in items)+'<td class="tt">-</td>'
    ex_h=ex_n='';
    if extra_cols:
        L=len(extra_cols)
        def xcls(i): return 'xc'+(' xf' if i==0 else '')+(' xl' if i==L-1 else '')
        ex_h=''.join(f'<th class="{xcls(i)}">{h}</th>' for i,(h,_) in enumerate(extra_cols))
        ex_n=''.join(f'<td class="{xcls(i)}" rowspan="2">{v}</td>' for i,(_,v) in enumerate(extra_cols))
    barhtml = stackbar(items,t) if bar else ''
    return f'''<div class="mx"><div class="mxt">{title}{barhtml}</div>
<table class="tb mt"><tr><th class="rh"></th>{labs}{ex_h}</tr>
<tr><th class="rh">인원</th>{nums}{ex_n}</tr><tr><th class="rh">비율</th>{rats}</tr></table></div>'''

def radar(sc):
    axes=[('응시 수요',sc['apply']),('취득 규모',sc['acq']),('취업률',sc['emp']),('채용 수요',sc['post']),('제시 임금',sc['wage'])]
    axes=[(nm, 0 if v is None else v) for nm,v in axes]  # 미시행 지표(빈 척도)는 중심(0점)
    cx,cy,R=118,102,66; pts=[]; grid=''
    for g in (2,4,6,8,10):
        ring=' '.join(f'{cx+R*g/10*math.sin(2*math.pi*k/5):.1f},{cy-R*g/10*math.cos(2*math.pi*k/5):.1f}' for k in range(5))
        grid+=f'<polygon points="{ring}" fill="none" stroke="#D9D9D9" stroke-width="0.7"/>'
    lab=''
    for k,(name,v) in enumerate(axes):
        ang=2*math.pi*k/5
        pts.append(f'{cx+R*v/10*math.sin(ang):.1f},{cy-R*v/10*math.cos(ang):.1f}')
        lx,ly=cx+(R+18)*math.sin(ang), cy-(R+14)*math.cos(ang)
        anc='middle' if abs(math.sin(ang))<.3 else ('start' if math.sin(ang)>0 else 'end')
        grid+=f'<line x1="{cx}" y1="{cy}" x2="{cx+R*math.sin(ang):.1f}" y2="{cy-R*math.cos(ang):.1f}" stroke="#D9D9D9" stroke-width="0.7"/>'
        lab+=f'<text x="{lx:.0f}" y="{ly:.0f}" text-anchor="{anc}" class="rl">{name} <tspan class="rv">{v}</tspan></text>'
    poly=' '.join(pts)
    return f'''<svg viewBox="0 0 236 204" class="radar"><text x="118" y="11" text-anchor="middle" class="rt">구성항목별 10점 척도 (5지표)</text>
{grid}<polygon points="{poly}" fill="#1F4E79" fill-opacity=".28" stroke="#1F4E79" stroke-width="1.6"/>
{''.join(f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="2.2" fill="#1F4E79"/>' for p in pts)}{lab}</svg>'''

AP='\u2019'   # 연도 라벨용 오른따옴표(3.11 호환: f-string 밖 상수)
def trend():
    ys=M['years']; A=X['apply']; Q=X['acquire']; P=X.get('p_apply_y') or []
    W,Hh,pad=300,44,16
    _vals=[v for v in list(A)+list(P)+list(Q) if v is not None]
    mx=(max(_vals) if _vals else 1)*1.15
    def xy(i,v): return (pad+ i*(W-pad-6)/(len(ys)-1), Hh-11-(v/mx)*(Hh-17))
    def line(vals,color):
        pts=' '.join(f'{xy(i,v)[0]:.1f},{xy(i,v)[1]:.1f}' for i,v in enumerate(vals) if v is not None)
        dots=''.join(f'<circle cx="{xy(i,v)[0]:.1f}" cy="{xy(i,v)[1]:.1f}" r="1.7" fill="{color}"/>' for i,v in enumerate(vals) if v is not None)
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.4"/>'+dots
    svg=f"""<svg viewBox="0 0 {W} {Hh}" class="tr">
{line(A,'#1F4E79')}{line(P,'#70AD47')}{line(Q,'#ED7D31')}
{''.join(f'<text x="{xy(i,0)[0]:.0f}" y="{Hh-2}" class="ax">{AP}{str(y)[2:]}</text>' for i,y in enumerate(ys))}</svg>"""
    return svg

# ───────── Ⅰ 기초정보 ─────────
def yn(b): return '해당' if b else '아님'
fl=set(X.get('flags') or [])
basic_rows=[
 [('종목코드',X['code']),('종목명',f'<b class="hl">{esc(X["name"])}</b>'),('평가유형',X['etype'].replace('과정형','과정평가형')),('과정형 운영',X.get('course_run') or '-'),('수탁기관','한국산업인력공단')],
 [('소관부처',X.get('ministry') or '-'),('직무분야',X.get('field')),('중직무분야',X.get('midfield') or '-'),('세부직무분야',X.get('subfield') or '-'),('실기시험방법',X.get('practical') or '-')],
 [('국가외검정금지',yn('국가외 검정 금지' in fl)),('기간산업직종',yn('기간산업 직종' in fl)),('전략산업직종',yn('전략산업 직종' in fl)),('서비스산업직종',yn('서비스산업 직종' in fl)),('국방부시행',yn('국방부 시행' in fl))],
 [('격년시행여부','해당' if X.get('biennial') else '아님')]+[(f'종목명_{y}', esc((X.get('names') or {}).get(str(y),'-'))) for y in (2025,2026,2027,2028)],
]
def kvrow(pairs):
    return '<tr>'+''.join(f'<th class="kl">{k}</th><td class="kv" colspan="3">{v}</td>' for k,v in pairs)+'</tr>'
sec1=f'''<table class="tb kvt">{''.join(kvrow(r) for r in basic_rows)}
</table>
<table class="tb kvt2"><tr><th class="kl">종목개요</th><td class="kv long">{esc(X.get('intro') or '')}</td></tr>
<tr><th class="kl">수행직무</th><td class="kv long">{esc(X.get('job') or '')}</td></tr></table>'''

# ───────── Ⅱ 척도 + 구간표 ─────────
sc=X['sc']
m2=[('응시수요(명)',"(3년평균('22~'24))",sc['apply'],n(X['apply_avg3'])),
    ('자격취득자 규모(명)',"(3년평균('22~'24))",sc['acq'],n(X['acq_avg3'])),
    ('취업률',f"({M['labor_short']})",sc['emp'],p1(X['emp_rateRef'])),
    ('채용공고 수요(건)',f"('{M['job24_year']%100}년)",sc['post'],n(X['post_cnt'])),
    ('제시임금(만원)',f"('{M['job24_year']%100}년)",sc['wage'],n(X['wage'])),
    ('비재직자 비율(%)',f"({M['labor_short']})",'-',p1(X['ins']['non']/X['ins']['t'] if X.get('ins') and X['ins'].get('t') and X['ins'].get('non') is not None else None)),
    ('재직자 비율(%)',f"({M['labor_short']})",'-',p1(X['ins']['stay_r'] if X.get('ins') else None))]
h1=''.join(f'<th>{a}</th>' for a,_,_,_ in m2); h2=''.join(f'<td class="sub">{b}</td>' for _,b,_,_ in m2)
h3=''.join(f'<td class="big">{c if c is not None else "-"}</td>' for _,_,c,_ in m2); h4=''.join(f'<td class="val">{d}</td>' for _,_,_,d in m2)
SCALE_FB=[  # 폴백(구버전 HTML용) — One-page(외부용) 시트 실측 사본
 ('응시수요(명)','1~16.7','17.3~50.7','51~104','109.3~201.7','202~436.7','445.7~898.3','904.3~1558','1559.7~3464','3475.3~8232.3','8404~209107.7','4341.5'),
 ('취득자규모(명)','0~4','4~10.3','10.7~22.7','23~47','47.7~102','102.3~251','255.7~501.7','503.3~987','992.3~2622.7','2640~64976','1333.2'),
 ('취업률(%)','0.8~13.5','14~21.5','21.5~25.6','25.6~31.5','31.6~34.8','34.9~40','40.1~46.3','46.3~50.5','50.5~58.7','59.5~100','36.8'),
 ('채용공고 수요(건)','0~0','0~0','0~2','2~4','4~7','7~14','14~30','30~80','82~296','323~13731','195.4'),
 ('제시임금(만원)','0~0','0~0','0~223','223~242','242~257','258~269','269~285','285~299','299~325','325~500','212.9')]
SCALE=[(r['k'],*r['b'],f"{r['m']:g}") for r in M.get('scale',[])] or SCALE_FB
srow=''.join('<tr><th class="rh2">%s</th>%s<td class="avg">%s</td></tr>'%(r[0],''.join(f'<td>{c}</td>' for c in r[1:11]),r[11]) for r in SCALE)
sec2=f'''<div class="two"><div class="l">
<table class="tb m2"><tr><th class="rh">구성항목<br><span class="sub">(기준)</span></th>{h1}</tr>
<tr><th class="rh"></th>{h2}</tr><tr><th class="rh">척도</th>{h3}</tr><tr><th class="rh">실수치</th>{h4}</tr></table>
<p class="cap capdim">▷ 척도 분석 기준수치 구간표</p>
<table class="tb sct"><colgroup><col style="width:12.5%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"><col style="width:7.95%"></colgroup><tr><th class="rh2">구분</th>{''.join(f'<th>{i}점<br><span class="sub">(하위{(i-1)*10}~{i*10}%)</span></th>' for i in range(1,11))}<th>평균</th></tr>{srow}</table>
<p class="foot">*분석기준 연도 내 시행된 전체 국가기술자격 종목에 대한 구간별 분포 기반. 해당 수치는 매년 변동될 수 있음.</p>
</div><div class="r">{radar(sc)}</div></div>'''

# ───────── Ⅲ 추이 ─────────
res=[('필기접수',n(X['w_reg'])),('필기응시',n(X['w_apply'])),('응시율',p1(X['w_take'])),('필기합격',n(X['w_pass'])),('합격률',p1(X['w_rate'])),
     ('실기접수',n(X['p_reg'])),('실기응시',n(X['p_apply'])),('응시율',p1(X['p_take'])),('실기합격',n(X['p_pass'])),('합격률',p1(X['p_rate'])),('최종취득',f"<b>{n(X['acq_now'])}</b>")]
note='비해당' if not (X.get('prac_only') or X.get('biennial')) else '해당'
ys=M['years']
def tr_row(name,vals,avg,rg,ra):
    return f'<tr><th class="rh2">{name}</th>'+''.join(f'<td>{v}</td>' for v in vals)+f'<td class="avg">{avg}</td><td>{rg}</td><td>{ra}</td></tr>'

sec3=f'''<p class="cap">{M["base_year"]}년 시행 결과</p>
<table class="tb res"><tr>{''.join(f'<th>{k}<span class="sub">({"명" if "률" not in k and "율" not in k else "%"})</span></th>' for k,_ in res)}
<th class="sp">특이사항 ({M["base_year"]})</th></tr>
<tr>{''.join(f'<td>{v}</td>' for _,v in res)}<td class="sp"><b>{note}</b><br><span class="sub">면제검정·격년시행·실기단독 해당 여부</span></td></tr></table>
<div class="two3"><div class="l"><p class="trcap">7개년 추이&nbsp; <span style="color:#1F4E79">&#8213; 응시(필기)</span>&nbsp;<span style="color:#70AD47">&#8213; 응시(실기)</span>&nbsp;<span style="color:#ED7D31">&#8213; 취득</span></p>{trend()}</div><div class="r">
<table class="tb trt"><tr><th class="rh2">구분</th>{''.join(f"<th>\u2019{str(y)[2:]}</th>" for y in ys)}<th>3개년평균</th><th>순위(등급)</th><th>순위(전체)</th></tr>
{tr_row('응시<br>(필기)',[n(v) for v in X['apply']],n(X['apply_avg3']),X['apply_rank_grade'],X['apply_rank_all'])}
{tr_row('응시<br>(실기)',[n(v) for v in (X.get('p_apply_y') or ['—']*len(ys))],n(X.get('p_avg3')),X.get('p_rank_grade') or '—',X.get('p_rank_all') or '—')}
{tr_row('취득<br>(최종)',[n(v) for v in X['acquire']],n(X['acq_avg3']),X.get('acq_rank_grade') or '—',X['acq_rank_all'])}
</table></div></div>'''

# ───────── Ⅳ 수험자 통계 ─────────
_SVY4 = X.get('status') is not None          # 필기 접수자 설문(Ⅳ)
_SVY5 = X.get('g_gender') is not None         # 취득자 설문(Ⅴ)
_D0={'t':0,'i':[]}; _YN={'y':0,'n':1}
if not (_SVY4 and _SVY5):
    X=dict(X)
    if not _SVY4:
        for _k in ['gender','age','edu','purpose','status','worksize']: X[_k]=_D0
        X['relwork']=_YN; X['favor']=_YN; X['pref']={'areas':[]}
    if not _SVY5:
        for _k in ['g_gender','g_nation','g_age','g_edu','g_school','g_status','g_purpose','prep_path']: X[_k]=_D0
        X['avg_age']=None; X['age_stat']={'max':None,'min':None,'sd':None}
svy_t=X['status']['t']
def bar2(y,nn,la,lb,c1='#4472C4',c2='#C9CDD4'):
    t=y+nn; w=(y/t*100) if t else 0
    return (f'<div class="sb" style="height:11px"><i style="left:0;width:{w:.2f}%;background:{c1}"><b>{la}</b></i>'
            f'<i style="left:{w:.2f}%;width:{100-w:.2f}%;background:{c2}"><b style="color:#444;text-shadow:none">{lb}</b></i></div>')
pref_tab=f'''<div class="mx half"><div class="mxt">자격업무관련성{bar2(X['relwork']['y'],X['relwork']['n'],'있음','없음')}</div><table class="tb mt"><tr><th class="rh"></th><th>있음</th><th>없음</th><th class="tt">총계</th></tr>
<tr><th class="rh">인원</th><td>{n(X['relwork']['y'])}</td><td>{n(X['relwork']['n'])}</td><td class="tt">{n(X['relwork']['y']+X['relwork']['n'])}</td></tr>
<tr><th class="rh">비율</th><td>{p1(X['relwork']['y']/(X['relwork']['y']+X['relwork']['n']))}</td><td>{p1(X['relwork']['n']/(X['relwork']['y']+X['relwork']['n']))}</td><td class="tt">-</td></tr></table></div>
<div class="mx half"><div class="mxt">근무처 우대여부{bar2(X['favor']['y'],X['favor']['n'],'우대함','우대안함','#ED7D31')}</div><table class="tb mt"><tr><th class="rh"></th><th>우대함</th><th>우대안함</th><th class="tt">총계</th></tr>
<tr><th class="rh">인원</th><td class="hl2">{n(X['favor']['y'])}</td><td>{n(X['favor']['n'])}</td><td class="tt">{n(X['favor']['y']+X['favor']['n'])}</td></tr>
<tr><th class="rh">비율</th><td>{p1(X['favor']['y']/(X['favor']['y']+X['favor']['n']))}</td><td>{p1(X['favor']['n']/(X['favor']['y']+X['favor']['n']))}</td><td class="tt">-</td></tr></table></div>'''
sec4=(mrow('성별',X['gender'])+mrow('응시연령',X['age'])+mrow('학력',X['edu'])+mrow('응시목적',X['purpose'])+mrow('경제활동상태',X['status'])
 +'<p class="cap mid"><span>↓ [재직자 응답] ↓</span></p>'+mrow('재직회사 규모',X['worksize'])
 +f'<div class="pair">{pref_tab}</div>'
 +mrow('직장내 자격우대 내용',{'t':X['favor']['y'],'i':X['pref']['areas']}))

# ───────── Ⅴ 취득자 통계 ─────────
gs=X['g_school']; gs_i=gs['i']+[('무응답', gs['t']-sum(v for _,v in gs['i']))]
age_ex=[('평균연령', n(X.get('avg_age'))),('최고령',n(X['age_stat']['max'])),('최연소',n(X['age_stat']['min'])),('표준편차',n(X['age_stat']['sd']))]
sec5=(f'''<div class="pair">{mrow('성별',X['g_gender']).replace('class="mx"','class="mx half"')}{mrow('국적',X['g_nation']).replace('class="mx"','class="mx half"')}</div>'''
 +mrow('취득연령',X['g_age'],extra_cols=age_ex)+mrow('학력',X['g_edu'])
 +mrow('학력 재적상태',{'t':gs['t'],'i':gs_i})+mrow('경제활동상태',X['g_status'])
 +mrow('응시목적',X['g_purpose'])+mrow('시험준비경로',X['prep_path']))
if not _SVY4:
    sec4=f'<p class="nosvy">{M["base_year"]}년 필기 접수자 설문 표본이 없어 수험자 통계를 제공하지 않습니다.{"<br>(과정평가형은 필기 접수자 설문 대상이 아닙니다.)" if X["etype"]=="과정형" else ""}</p>'
if not _SVY5:
    sec5=f'<p class="nosvy">{M["base_year"]}년 취득자 설문 표본이 없어 취득자 통계를 제공하지 않습니다.</p>'

# ───────── Ⅵ·Ⅶ ─────────
def insrow2(nm, D, na_cell):
    return (f'<tr><th class="rh2">{nm}</th><td>{n(D.get("t"))}</td><td>{n(D.get("stay"))}</td><td>{p1(D.get("stay_r"))}</td>'
            f'<td>{n(D.get("non"))}</td><td>{n(D.get("e6"))}</td><td><b>{p1(D.get("m6"))}</b></td>'
            f'<td>{n(D.get("eK"))}</td><td><b>{p1(D.get("ref"))}</b></td><td>{na_cell}</td></tr>')
INS=dict(X.get('ins') or {}); INS['m6']=X.get('emp_rate6'); INS['ref']=X.get('emp_rateRef')
HIE=dict(X.get('hi_emp') or {}); HIE['non']=HIE.get('base')
sec6=f"""<table class="tb ins"><tr><th class="rh2">구분</th><th>취득자</th><th>재직자수</th><th>재직률</th><th>비재직자수</th><th>취업자수<br>(6개월)</th><th>취업률<br>(6개월)</th><th>취업자수<br>({M['labor_short']})</th><th>취업률<br>({M['labor_short']})</th><th>조회불가</th></tr>
{insrow2('고용보험',INS,'<span class="dim">—</span>')}
{insrow2('건강보험',HIE,n(HIE.get('na')))}</table>"""
den=M['bench']['검정형']['postnz']['n']
sec7=f'''<table class="tb j24"><tr><th>구인건수</th><th>구인건수규모 순위</th><th>구인인원</th><th>구인인원규모 순위</th><th>제시임금 평균</th><th>자격종목수</th></tr>
<tr><td class="big2">{n(X['post_cnt'])}</td><td>{X['post_rank']}/{den}</td><td class="big2">{n(X['post_head'])}</td><td>{X['post_head_rank']}/{den}</td><td class="big2">{n(X['wage'])}</td><td>{den} <span class="sub">*구인정보 존재 종목 수</span></td></tr></table>'''

# ───────── 조립 ─────────
CSS='''@page{size:A3 portrait;margin:0}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Malgun Gothic','맑은 고딕','Noto Sans KR','Noto Sans CJK KR',sans-serif;color:#1a1a1a;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.sheet{width:297mm;min-height:420mm;padding:4.5mm 6mm 3.5mm;background:#fff;display:flex;flex-direction:column;gap:0.9mm}
.head{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2.2px solid #1F4E79;padding-bottom:1.2mm}
.head .t{font-size:11.5pt;font-weight:800;color:#1F4E79}.head .t b{background:#FFF2CC;padding:0 2mm}
.head .org{font-size:9pt;font-weight:700;color:#1F4E79}
.sec{border:0.9px solid #BFBFBF}
.sech{background:#1F4E79;color:#fff;font-size:7.8pt;font-weight:800;padding:0.55mm 1.8mm;letter-spacing:.02em}
.secb{padding:0.7mm 1.2mm;display:flex;flex-direction:column;gap:0.55mm}
.tb{border-collapse:collapse;width:100%;font-size:6.0pt;table-layout:fixed}
.tb th,.tb td{border:0.6px solid #BFBFBF;padding:0.2mm 0.45mm;text-align:center;overflow:hidden;line-height:1.18}
.tb th{background:#EDF1F7;font-weight:700}
.kvt th.kl{width:7.8%;background:#F2F2F2}.kvt td.kv{text-align:left;padding-left:1.2mm}
.kvt2{table-layout:fixed}.kvt2 th.kl{width:7.8%;background:#F2F2F2}.kvt2 td.kv{text-align:left;padding-left:1.2mm}
.kvt2 td.long{font-size:6.0pt;line-height:1.25}
.hl{background:#FFF2CC;padding:0 1mm;font-size:7.6pt}
.rh{width:9mm;background:#F2F2F2}
.m2 .rh{width:14mm}.rh2{background:#F2F2F2;width:17mm}
.trt .rh2{width:9mm}
.sub{font-size:5.4pt;color:#777;font-weight:400}
.big{font-size:8pt;font-weight:800;color:#1F4E79}.big2{font-size:8.6pt;font-weight:800;color:#1F4E79}
.val{font-weight:700}.avg{background:#FBF4E4;font-weight:700}
.two{display:flex;gap:2mm}.two .l{flex:1}.two .r{width:62mm;display:flex;align-items:center;justify-content:center}
.radar{width:58mm}.rt{font-size:7.5px;font-weight:700;fill:#1F4E79}.rl{font-size:7px;fill:#333}.rv{font-weight:800;fill:#1F4E79}
.cap{font-size:7pt;font-weight:800;color:#1F4E79;margin:0.3mm 0}
.cap.capdim{display:block;margin-top:1.8mm;background:#D9E6F2;color:#2E5A8F;padding:0.5mm 1.2mm;border:0.6px solid #C3D4E6}
.cap.mid{text-align:left;padding-left:103.4mm;color:#555}  /* 경활 표 "재직자" 열 중심 — mxt 폭·열수 변경 시 재계산 */
.cap.mid span{display:inline-block;transform:translateX(-50%)}
.sct td{font-size:5.15pt;padding:0.2mm 0.2mm;white-space:nowrap;color:#9a9a9a;border-color:#E4E4E4}
.sct th{background:#F3F6FA;color:#8d97a5;border-color:#E4E4E4}
.sct th .sub{color:#aab3bd}
.sct .rh2{background:#F6F6F6;color:#8d97a5}
.sct .avg{background:#FCF8EE;color:#b09a62}
.sct .rh2{white-space:nowrap}
.foot{font-size:5.6pt;color:#777}
.res .sp{width:34mm;background:#FBF4E4}
.two3{display:flex;gap:2mm;align-items:stretch}.two3 .l{width:106mm;flex:none;display:flex;flex-direction:column;justify-content:center;gap:0.4mm}.two3 .r{flex:1;min-width:0}
.trcap{font-size:5.8pt;font-weight:700;color:#333}.dim2{color:#999;font-weight:400}
.tr{width:100%}.tt2{font-size:8px;font-weight:700;fill:#333}.lg{font-size:7px}.ax{font-size:6.5px;fill:#666;text-anchor:middle}
.trt{table-layout:auto}.trt th,.trt td{font-size:5.6pt;white-space:nowrap;padding:0.2mm 0.5mm}
.mx{display:flex;gap:1mm;align-items:stretch}
.mxt{width:52mm;background:#F2F2F2;border:0.6px solid #BFBFBF;font-size:6.2pt;font-weight:700;display:flex;flex-direction:column;justify-content:center;gap:0.6mm;padding:0.5mm 0.9mm}
.mt{flex:1}.tt{background:#EDF1F7;font-weight:800}
.sb{position:relative;background:#eee;border-radius:1px;overflow:hidden}
.sb i{position:absolute;top:0;bottom:0;display:flex;align-items:center;justify-content:center;overflow:hidden}
.sb i b{color:#fff;font-size:5.3pt;font-weight:700;white-space:nowrap;text-shadow:0 0 2px rgba(0,0,0,.4)}
.pair{display:flex;gap:2mm}.half{flex:1}
.xc{width:11mm;background:#F7F9FC;font-weight:700}
th.xc{background:#FCE4D6;border-top:1.3px solid #C55A11}
td.xc{border-bottom:1.3px solid #C55A11}
.xf{border-left:1.3px solid #C55A11 !important}
.xl{border-right:1.3px solid #C55A11 !important}
.hl2{background:#FFF2CC;font-weight:800}
.ins th,.ins td{font-size:6.2pt}.j24 td{font-size:6.8pt}
.fix,.fx .fix{display:inline-block;background:repeating-linear-gradient(45deg,#f1f1f1,#f1f1f1 3px,#e4e4e4 3px,#e4e4e4 6px);color:#8a6d1a;border:0.7px dashed #c9a227;border-radius:2px;font-size:5.6pt;font-weight:800;padding:0.2mm 1mm}
.fx{background:#fafafa}.dim{color:#bbb}
.fx2{font-size:5.2pt;padding:0.1mm 0.7mm}
.src{font-size:6.2pt;color:#555;border-top:1.4px solid #1F4E79;padding-top:0.8mm;display:flex;justify-content:space-between}
'''
def section(no,title,body): return f'<div class="sec"><div class="sech">{no}. {title}</div><div class="secb">{body}</div></div>'
html=f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>{esc(X["name"])} One-page(시안)</title><style>{CSS}.nosvy{{border:1.2px dashed #B8BFC9;background:#FBFBF9;color:#5A6472;padding:7mm 4mm;text-align:center;font-size:9pt;margin:1.5mm 0}}
</style></head>
<body><div class="sheet">
<div class="head"><div class="t">국가기술자격 One-page 분석 종합 정보 · 분석기준 <b>{M["base_year"]}년</b></div><div class="org">한국산업인력공단</div></div>
{section('Ⅰ','종목 기초정보',sec1)}
{section('Ⅱ','구성항목별 척도 분석 (10점 만점)',sec2)}
{section('Ⅲ',f'응시·취득 변동 추이 ({ys[0]}~{ys[-1]})',sec3)}
{section('Ⅳ','수험자 통계 (필기시험 응시자 설문)',sec4)}
{section('Ⅴ','취득자 통계 (해당연도 취득자)',sec5)}
{section('Ⅵ','노동시장 활용 통계 (고용보험·건강보험)',sec6)}
{section('Ⅶ','채용공고 분석 (고용24)',sec7)}
<div class="src"><span>출처: 국가기술자격 통계연보 / 기초통계 설문 / 고용보험 DB / 건강보험 DB / 고용24</span><span>데이터 {M.get("built","")} 산출본 · 원장 보강 반영</span></div>
</div></body></html>'''
out=f'sheet_{CODE}.html'
io.open(out,'w',encoding='utf-8').write(html)
print(out,'생성', len(html),'자')
