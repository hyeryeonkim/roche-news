import streamlit as st
import feedparser
import pandas as pd
import re
from datetime import datetime, timedelta
from time import mktime
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="Roche Daily News Monitoring", layout="wide")
st.title("📰 한국로슈 Daily News Monitoring Dashboard")

# 1. 수집 매체 리스트 (28개 전체 매체)
ALL_MEDIA_LIST = [
    # [1 Tier] 주요 통신사 및 종합 일간지
    {"media": "연합뉴스", "tier": "1 Tier", "rss": "https://www.yna.co.kr/rss/news.xml"},
    {"media": "조선일보", "tier": "1 Tier", "rss": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"},
    {"media": "중앙일보", "tier": "1 Tier", "rss": "https://rss.joongang.co.kr/son/joongang_all.xml"},
    {"media": "동아일보", "tier": "1 Tier", "rss": "https://rss.donga.com/total.xml"},
    {"media": "한겨레", "tier": "1 Tier", "rss": "https://www.hani.co.kr/rss/"},
    {"media": "경향신문", "tier": "1 Tier", "rss": "https://www.khan.co.kr/rss/rssdata/total_news.xml"},
    {"media": "한국일보", "tier": "1 Tier", "rss": "https://hankookilbo.com/baidu/rss/all"},
    {"media": "국민일보", "tier": "1 Tier", "rss": "https://rss.kmib.co.kr/data/kmibRssAll.xml"},
    
    # [1 Tier] 주요 경제지 및 방송사
    {"media": "매일경제", "tier": "1 Tier", "rss": "https://www.mk.co.kr/rss/30000001/"},
    {"media": "한국경제", "tier": "1 Tier", "rss": "https://www.hankyung.com/feed/all-news"},
    {"media": "서울경제", "tier": "1 Tier", "rss": "https://www.sedaily.co.kr/RSS/NewsAll"},
    {"media": "아시아경제", "tier": "1 Tier", "rss": "https://www.asiae.co.kr/rss/all.xml"},
    {"media": "파이낸셜뉴스", "tier": "1 Tier", "rss": "https://www.fnnews.com/rss/fn_realtime_all.xml"},
    {"media": "이데일리", "tier": "1 Tier", "rss": "https://rss.edaily.co.kr/e-health_news.xml"},
    {"media": "YTN", "tier": "1 Tier", "rss": "https://www.ytn.co.kr/_comm/get_rss_news.php?code=0103"},

    # [2 Tier] 제약 / 바이오 / 의료 전문지
    {"media": "청년의사", "tier": "2 Tier", "rss": "https://www.docdocdoc.co.kr/rss/allArticle.xml"},
    {"media": "데일리팜", "tier": "2 Tier", "rss": "https://www.dailypharm.com/Users/Rss/Rss.html"},
    {"media": "약업신문", "tier": "2 Tier", "rss": "https://www.yakup.com/rss/"},
    {"media": "메디칼타임즈", "tier": "2 Tier", "rss": "https://www.medicaltimes.com/Users/Rss/Rss.html"},
    {"media": "의학신문", "tier": "2 Tier", "rss": "https://www.bosa.co.kr/rss/allArticle.xml"},
    {"media": "라포르시안", "tier": "2 Tier", "rss": "https://www.rapportian.com/rss/allArticle.xml"},
    {"media": "메디파나뉴스", "tier": "2 Tier", "rss": "https://www.medipana.com/rss/allArticle.xml"},
    {"media": "의약뉴스", "tier": "2 Tier", "rss": "https://www.newsmp.com/rss/allArticle.xml"},
    {"media": "히트뉴스", "tier": "2 Tier", "rss": "https://www.hitnews.co.kr/rss/allArticle.xml"},
    {"media": "뉴스더보이스", "tier": "2 Tier", "rss": "https://www.newsthevoice.com/rss/allArticle.xml"},
    {"media": "바이오스펙테이터", "tier": "2 Tier", "rss": "https://www.biospectator.com/rss/allArticle.xml"},
    {"media": "헬스코리아뉴스", "tier": "2 Tier", "rss": "https://www.hkn24.com/rss/allArticle.xml"},
    {"media": "팜뉴스", "tier": "2 Tier", "rss": "https://www.pharmnews.com/rss/allArticle.xml"},
    {"media": "메디소비자뉴스", "tier": "2 Tier", "rss": "https://www.medisobizanews.com/rss/allArticle.xml"}
]

CORPORATE_KEYWORDS = ["로슈", "Roche", "Genentech", "제넨텍", "제넨테크", "쥬가이", "Chugai", "한국로슈"]

PRODUCT_KEYWORDS = [
    "티쎈트릭", "Tecentriq", "아테졸리주맙", "atezolizumab", "맙테라", "Mabthera", "리툭시맙", "Rituximab", 
    "알레센자", "Alecensa", "알렉티닙", "alectinib", "셀셉트", "Cellcept", "미코페놀레이트모페틸", "마이코페놀레이트", "Mofetil", 
    "아바스틴", "AVASTIN", "베바시주맙", "Bevacizumab", "타미플루", "Tamiflu", "조플루자", "Xofluza", "발록사비르마르복실", "타쎄바", "타세바", "Tarceva", "허셉틴", "Herceptin", "트라스투주맙", "Trastuzumab", 
    "마도파", "Madopar", "퍼제타", "Perjeta", "퍼투주맙", "Pertuzumab", "캐싸일라", "Kadcyla", "트라스투주맙 엠탄신", 
    "가싸이바", "Gazyva", "오비누투주맙", "Obinutuzumab", "폴리비", "폴라투주맙", "폴라이비", "엔스프링", "Enspryng", "사트랄리주맙", 
    "에브리스디", "Evrysdi", "리스디플람", "risdiplam", "로즐리트렉", "Rozlytrek", "바비스모", "vabysmo", "파리시맙", "faricimab", 
    "서스비모", "Susvimo", "라니비주맙", "페스코", "페스고", "Phesgo", "모수네투주맙", "룬수미오", "오크레부스", "Ocrevus", "오크렐리주맙", 
    "글로피타맙", "컬럼비", "엘레비디스", "엘리비디스", "이나볼리십", "이토베비", "피아스카이", "크로발리맙", "트론티네맙"
]

DISEASE_KEYWORDS = [
    "킴리아", "예스카타", "졸겐스마", "스핀라자", "오나셈노진아베파르보벡", "뉴시너센", "넥사바", "렌비마", 
    "키트루다", "옵디보", "아일리아", "비오뷰", "루센티스", "아필리부", "아이델젠트", "알룬브릭", "로비큐아", 
    "엔허투", "이뮤도", "임핀지", "림카토", "민쥬비", "척수성근위축증", "SMA", "희귀질환", "신경근육질환", 
    "시신경척수염", "NMOSD", "시신경척수염범주질환", "희귀난치성질환", "희귀난치질환", "황반변성", "황반부종", 
    "당뇨병성망막병증", "혈액암", "바이오의약품", "당뇨병성황반부종", "인플루엔자", "유방암", "간암", 
    "간세포암", "비소세포폐암", "파킨슨", "대한종양내과학회", "신경과학회", "신경면역학회", "안과학회", 
    "망막학회", "대한감염학회", "면역항암제", "항체의약품", "세포치료제", "생물의약품", "바이오시밀러", 
    "암질환심의위원회", "암질심", "중증질환심의위원회", "DMD", "뒤센근이영양증", "듀센근이영양증", "DLBCL", 
    "엡킨리", "다발성경화증", "티사브리", "렘트라다", "울토미리스", "Ultomiris", "라불리주맙", "Ravulizumab", 
    "업리즈나", "이네빌리주맙", "티루캡", "피크레이", "조기암", "조기유방암"
]

INDUSTRY_SINGLE_KEYWORDS = [
    "약평위", "암질심", "심평원", "건보공단", "복지부", "식약처", "공정위", "보건복지위", "국정감사", "국감",
    "KRPIA", "한국글로벌의약산업협회", "KOBIA", "한국바이오의약품협회", "한국제약바이오협회",
    "약가협상", "약가인하", "약가제도", "경평면제", "위험분담제", "RSA", "경제성평가", "급여재평가",
    "고가의약품", "초고가신약", "사전심의", "사용량-약가연동", "RWD", "RWE",
    "혁신신약", "혁신형제약기업", "정밀의료", "정밀의학", "맞춤의학", "디지털헬스케어", 
    "디지털바이오마커", "보건의료데이터", "신의료기술", "건보재정", "건강보험정책", "분산형임상", "DCT"
]

NEGATIVE_KEYWORDS = [
    "집값", "아파트", "부동산", "규제지역", "분양", "주택", "청약", "전세", 
    "증시", "주가", "코스피", "코스닥", "상한가", "특징주", "목표가", "치과", "한의원"
]

ROCHE_DISEASE_AREAS = [
    "폐암", "비소세포폐암", "유방암", "간암", "혈액암", "림프종", "DLBCL",
    "SMA", "척수성근위축증", "NMOSD", "시신경척수염", "황반변성", "황반부종",
    "희귀질환", "희귀난치성질환", "루푸스", "다발성경화증", "DMD", "근이영양증"
]

UNRELATED_DISEASE_AREAS = [
    "아토피", "건선", "당뇨", "고혈압", "치매", "알츠하이머", "탈모", "통풍", "골다공증", "성조숙증", "비만"
]

# 카테고리 매칭 함수
def classify_article_by_rules(text):
    text_lower = text.lower()
    if re.search(r"로슈|Roche|제넨텍|Genentech|쥬가이|Chugai", text, re.I) and re.search(r"한국|본사|실적|대표|인사|CSR|사회공헌|한국로슈", text):
        return "Corporate News", "(로슈*기업동향/CSR)"
        
    for ck in CORPORATE_KEYWORDS:
        if ck.lower() in text_lower:
            return "Corporate News", ck

    for p in PRODUCT_KEYWORDS:
        if p.lower() in text_lower:
            return "Product News", p

    for dk in DISEASE_KEYWORDS:
        if dk.lower() in text_lower:
            return "Disease/ Market News", dk

    if re.search(r"암", text) and re.search(r"항암제", text) and re.search(r"임상|허가|급여|적응증|3상|제약|신약|FDA|암질심", text):
        return "Disease/ Market News", "(암*항암제*제약이슈)"
    if re.search(r"독감|인플루엔자", text) and re.search(r"항바이러스제|치료제|치료|질병관리청|국가감염병|통계|조사", text):
        return "Disease/ Market News", "(독감*치료제/감염병)"

    for ik in INDUSTRY_SINGLE_KEYWORDS:
        if ik.lower() in text_lower:
            return "Industry/ Policy News", ik

    if re.search(r"다국적|글로벌|외자사", text, re.I) and re.search(r"제약사|제약업계|제약기업|제약업체", text) and re.search(r"인사|동정|수상|CSR|사회공헌|인수|합병|리베이트", text):
        return "Industry/ Policy News", "(글로벌제약사*동향/CSR/인사)"
    if re.search(r"임상시험|R&D|연구개발|특허", text, re.I) and re.search(r"의약품|약품|치료제|신약", text):
        return "Industry/ Policy News", "(R&D/특허*의약품)"
    if re.search(r"급여|접근성|보장성|보험|비급여", text) and re.search(r"의약품|약품|신약|항암|치료", text):
        return "Industry/ Policy News", "(급여/보장성*의약품)"
    if re.search(r"환자단체총연합회|백혈병환우회|희귀난치성질환연합회|환우회|환자단체", text) and re.search(r"항암제|치료제|탄원|정책|암|희귀질환|신약", text):
        return "Industry/ Policy News", "(환자단체*정책)"

    return None, None

# 점수 계산 함수
def calculate_relevance_score(title, summary, category, tier="2 Tier"):
    full_text = f"{title} {summary}"
    score = 3

    if category == "Corporate News":
        score += 4
        if any(k in full_text for k in ["로슈", "Roche", "한국로슈"]): score += 2

    elif category == "Product News":
        score += 3
        if any(core in full_text for core in ["티쎈트릭", "바비스모", "에브리스디", "페스코", "캐싸일라", "퍼제타", "허셉틴", "이토베비"]): score += 2

    elif category == "Disease/ Market News":
        score += 3
        if any(comp in full_text for comp in ["키트루다", "옵디보", "타그리소", "렉라자", "엔허투", "아일리아", "루센티스", "스핀라자", "졸겐스마", "울토미리스", "업리즈나", "피크레이", "티루캡"]):
            score += 2
        if any(dis in full_text for dis in ["비소세포폐암", "폐암", "유방암", "SMA", "황반변성", "간암", "NMOSD"]):
            if any(evt in full_text for evt in ["급여", "임상", "3상", "허가", "FDA", "적응증", "약평위", "암질심"]):
                score += 1

    elif category == "Industry/ Policy News":
        score += 2
        if any(p in full_text for p in ["약가인하", "약가협상", "약가제도", "위험분담제", "RSA", "경평면제", "급여재평가", "사용량-약가연동"]): score += 2
        if any(gov in full_text for gov in ["보건복지위", "국정감사", "국감", "법안", "발의", "입법", "개정안"]): score += 2
        if any(org in full_text for org in ["식약처", "심평원", "건보공단", "복지부"]):
            if any(policy in full_text for policy in ["정책", "개편", "가이드라인", "고시", "제도", "인사"]): score += 1
        if any(mNC in full_text for mNC in ["다국적", "글로벌", "외자사", "KRPIA"]):
            if any(m_evt in full_text for m_evt in ["약가", "규제", "제도", "인사", "CSR"]): score += 1
        if any(pt in full_text for pt in ["환자단체", "환우회", "환자"]):
            if any(r_dis in full_text for r_dis in ROCHE_DISEASE_AREAS): score += 2
            if any(u_dis in full_text for u_dis in UNRELATED_DISEASE_AREAS): score -= 2

    if category == "Industry/ Policy News":
        if any(k in title for k in ["약가", "급여", "보건복지위", "국감", "국정감사", "위험분담제", "RSA", "경평면제", "심평원", "식약처", "약평위", "암질심"]): score += 2
    else:
        if any(k in title for k in ["로슈", "Roche", "티쎈트릭", "바비스모", "에브리스디", "알레센자", "페스코", "이토베비", "키트루다", "타그리소", "렉라자", "엔허투", "아일리아", "스핀라자", "피크레이", "티루캡"]): score += 2

    if re.search(r"폐암|비소세포폐암", full_text, re.I):
        if re.search(r"ALK|KRAS", full_text, re.I):
            if not re.search(r"(ALK|KRAS)\s*(음성|미검출|제외|없음)", full_text, re.I): score += 2
        if re.search(r"EGFR|ROS1|\bROS\b", full_text, re.I): score -= 2

    if re.search(r"유방암", full_text, re.I):
        if re.search(r"HER2|HER2양성|HER2\+", full_text, re.I): score += 2
        if re.search(r"HR\+|HR양성|호르몬\s*양성|호르몬\s*수용체", full_text, re.I):
            if re.search(r"이토베비|PIK3CA|피크레이|티루캡|이나볼리십", full_text, re.I): score += 2
        if re.search(r"삼중음성|TNBC", full_text, re.I): score -= 2

    if tier == "1 Tier": score += 1
    return max(1, min(score, 10))

# 단일 매체 파싱
def parse_single_media(m, time_limit):
    sub_results = []
    try:
        feed = feedparser.parse(m["rss"])
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", entry.get("description", ""))
            full_text = f"{title} {summary}"
            
            if any(neg in full_text for neg in NEGATIVE_KEYWORDS):
                continue
            
            pub_dt = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime.fromtimestamp(mktime(entry.published_parsed))
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_dt = datetime.fromtimestamp(mktime(entry.updated_parsed))
            
            if pub_dt and pub_dt < time_limit:
                continue
            
            pub_date_str = pub_dt.strftime('%m/%d') if pub_dt else datetime.now().strftime('%m/%d')
            matched_cat, matched_kw = classify_article_by_rules(full_text)
            
            if matched_cat:
                rel_score = calculate_relevance_score(title, summary, matched_cat, tier=m["tier"])
                sub_results.append({
                    "선택": False,
                    "연관도점수": rel_score,
                    "카테고리": matched_cat,
                    "매체명": m["media"],
                    "Tier": m["tier"],
                    "검색키워드": matched_kw,
                    "기사제목": title,
                    "기사링크": link,
                    "게재일": pub_date_str
                })
    except:
        pass
    return sub_results

# 병렬 수집 로직
@st.cache_data(ttl=1800)
def fetch_recent_news():
    time_limit = datetime.now() - timedelta(hours=36)
    all_results = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(parse_single_media, m, time_limit) for m in ALL_MEDIA_LIST]
        for future in futures:
            all_results.extend(future.result())
    
    df_res = pd.DataFrame(all_results)
    if not df_res.empty:
        df_res = df_res.sort_values(by=["연관도점수", "Tier"], ascending=[False, True]).drop_duplicates(subset=["기사제목"], keep="first")
    return df_res

# 세션 초기화
if "news_df" not in st.session_state:
    st.session_state["news_df"] = fetch_recent_news()

# UI 레이아웃
col_title, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 실시간 뉴스 새로고침"):
        st.cache_data.clear()
        st.session_state["news_df"] = fetch_recent_news()
        st.session_state.pop("analyzed_df", None)
        st.rerun()

raw_df = st.session_state["news_df"]
st.write(f"⏰ 수집된 최신 기사: **{len(raw_df)}건**")

if not raw_df.empty:
    if st.button("🎯 중요 기사 자동 선별하기 (Top 5 자동 체크)", type="primary"):
        auto_df = raw_df.copy()
        for cat in ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]:
            cat_indices = auto_df[auto_df["카테고리"] == cat].sort_values(by="연관도점수", ascending=False).head(5).index
            auto_df.loc[cat_indices, "선택"] = True
        st.session_state["analyzed_df"] = auto_df
        st.success("스마트 분석 완료!")

    display_df = st.session_state.get("analyzed_df", raw_df)
    categories = ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]
    tabs = st.tabs([f"📌 {cat}" for cat in categories])
    
    all_edited_dfs = []
    
    for i, cat in enumerate(categories):
        with tabs[i]:
            cat_df = display_df[display_df["카테고리"] == cat].copy()
            st.markdown(f"### {cat} ({len(cat_df)}건)")
            
            if not cat_df.empty:
                edited = st.data_editor(
                    cat_df,
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택 ✅", default=False),
                        "연관도점수": st.column_config.NumberColumn("연관도 🎯", help="10점 만점 기준"),
                        "기사링크": st.column_config.LinkColumn("기사링크")
                    },
                    disabled=["연관도점수", "카테고리", "매체명", "Tier", "검색키워드", "기사제목", "기사링크", "게재일"],
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_{cat}"
                )
                all_edited_dfs.append(edited)
            else:
                st.info(f"현재 {cat} 관련 최신 기사가 없습니다.")

    st.divider()

    # ★ 실제 [Roche] 메일 발송 양식 규격으로 출력 생성 ★
    if all_edited_dfs:
        full_edited_df = pd.concat(all_edited_dfs, ignore_index=True)
        selected_df = full_edited_df[full_edited_df["선택"] == True]
        
        st.subheader(f"✅ 현재 총 **{len(selected_df)}건**의 기사가 선택되었습니다.")
        
        if st.button("🚀 선택한 기사로 뉴스레터 생성하기"):
            if not selected_df.empty:
                now = datetime.now()
                title_date_str = now.strftime('%b %d')        # 예: Jul 23
                header_date_str = now.strftime('%d %B, %Y')   # 예: 23 July, 2026
                
                # 1. 메일 양식 텍스트 헤더
                output_text = f"제목: [Roche] Daily News Monitoring {title_date_str}\n\n"
                output_text += f"Roche Daily News Highlights\n"
                output_text += f"{header_date_str}\n\n"
                output_text += f"NEWS\n\n"
                
                # 2. 카테고리별 기사 리스팅 (PDF 양식과 100% 동일)
                for cat in categories:
                    output_text += f"{cat}\n"
                    cat_df = selected_df[selected_df["카테고리"] == cat]
                    
                    if not cat_df.empty:
                        for _, r in cat_df.iterrows():
                            # 양식: * 기사제목 (매체명 MM/DD)
                            output_text += f"* [{r['기사제목']}]({r['기사링크']}) ({r['매체명']} {r['게재일']})\n"
                    else:
                        output_text += "* (관련 주요 기사 없음)\n"
                    output_text += "\n"
                
                # 3. 메일 푸터 및 서명
                output_text += f"[한국로슈 Communications & Public Affairs Chapter]\n"
                output_text += f"이미규 | migyu.lee@roche.com\n"
                output_text += f"김혜련 | hyeryeon.kim@roche.com\n"
                output_text += f"박수윤 | sue.park@roche.com\n\n"
                output_text += f"© {now.year} Roche Korea Co.,Ltd\n"
                
                st.markdown(output_text)
                st.download_button("📋 텍스트 파일로 다운로드", output_text, f"Roche_News_{now.strftime('%Y%m%d')}.txt")
            else:
                st.warning("선택된 기사가 없습니다.")
else:
    st.info("현재 수집된 기사가 없습니다.")
