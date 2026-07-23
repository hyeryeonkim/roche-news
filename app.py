import streamlit as st
import feedparser
import pandas as pd
import re
from datetime import datetime, timedelta
from time import mktime

st.set_page_config(page_title="Roche Daily News Monitoring", layout="wide")
st.title("📰 한국로슈 Daily News Monitoring Dashboard")

# 1. 수집 매체 리스트
ALL_MEDIA_LIST = [
    {"media": "연합뉴스", "tier": "1 Tier", "rss": "https://www.yna.co.kr/rss/news.xml"},
    {"media": "조선일보", "tier": "1 Tier", "rss": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"},
    {"media": "중앙일보", "tier": "1 Tier", "rss": "https://rss.joongang.co.kr/son/joongang_all.xml"},
    {"media": "동아일보", "tier": "1 Tier", "rss": "https://rss.donga.com/total.xml"},
    {"media": "매일경제", "tier": "1 Tier", "rss": "https://www.mk.co.kr/rss/30000001/"},
    {"media": "한국경제", "tier": "1 Tier", "rss": "https://www.hankyung.com/feed/all-news"},
    {"media": "서울경제", "tier": "1 Tier", "rss": "https://www.sedaily.co.kr/RSS/NewsAll"},
    {"media": "이데일리", "tier": "1 Tier", "rss": "https://rss.edaily.co.kr/e-health_news.xml"},
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
    {"media": "팜뉴스", "tier": "2 Tier", "rss": "https://www.pharmnews.com/rss/allArticle.xml"}
]

# 2. Product 단독 키워드 리스트
PRODUCT_KEYWORDS = [
    "티쎈트릭", "Tecentriq", "아테졸리주맙", "atezolizumab", "맙테라", "Mabthera", "리툭시맙", "Rituximab", 
    "알레센자", "Alecensa", "알렉티닙", "alectinib", "셀셉트", "Cellcept", "미코페놀레이트모페틸", "마이코페놀레이트", "Mofetil", 
    "아바스틴", "AVASTIN", "베바시주맙", "Bevacizumab", "타미플루", "Tamiflu", "오셀타미비르", "Oseltamivir", 
    "조플루자", "Xofluza", "발록사비르마르복실", "타쎄바", "타세바", "Tarceva", "허셉틴", "Herceptin", "트라스투주맙", "Trastuzumab", 
    "마도파", "Madopar", "퍼제타", "Perjeta", "퍼투주맙", "Pertuzumab", "캐싸일라", "Kadcyla", "트라스투주맙 엠탄신", 
    "가싸이바", "Gazyva", "오비누투주맙", "Obinutuzumab", "폴리비", "폴라투주맙", "폴라이비", "엔스프링", "Enspryng", "사트랄리주맙", 
    "에브리스디", "Evrysdi", "리스디플람", "risdiplam", "로즐리트렉", "Rozlytrek", "바비스모", "vabysmo", "파리시맙", "faricimab", 
    "서스비모", "Susvimo", "라니비주맙", "페스코", "페스고", "Phesgo", "모수네투주맙", "룬수미오", "오크레부스", "Ocrevus", "오크렐리주맙", 
    "글로피타맙", "컬럼비", "엘레비디스", "엘리비디스", "이나볼리십", "이토베비", "피아스카이", "크로발리맙", "트론티네맙"
]

# 3. 제외 키워드
NEGATIVE_KEYWORDS = ["집값", "아파트", "부동산", "규제지역", "분양", "주택", "청약", "전세", "증시", "주가", "코스피", "코스닥", "상한가", "특징주", "목표가"]

# 4. 정교 조합 검색 매칭 함수 (요청사항 반영)
def classify_article_by_rules(text):
    # 1) Corporate News 매칭 (순수 로슈 자사 전용)
    if re.search(r"한국로슈|로슈그룹|로슈진단", text, re.I):
        return "Corporate News", "한국로슈/기업 전용"

    # 2) Product News 매칭 (단독 제품명)
    for p in PRODUCT_KEYWORDS:
        if re.search(re.escape(p), text, re.I):
            return "Product News", p

    # 3) Disease / Market News 불리언 조합 매칭
    if re.search(r"암", text) and re.search(r"항암제", text) and re.search(r"임상|허가|급여|적응증|3상|제약|신약|FDA|암질심", text):
        return "Disease/ Market News", "(암*항암제*제약이슈)"
    if re.search(r"독감|인플루엔자", text) and re.search(r"항바이러스제|치료제|치료|질병관리청|국가감염병|통계|조사", text):
        return "Disease/ Market News", "(독감*치료제/감염병)"
    if re.search(r"척수성근위축증|SMA|시신경척수염|NMOSD|황반변성|루푸스|다발성경화증|유방암|간암|비소세포폐암|혈액암|DMD", text, re.I) and re.search(r"치료제|신약|임상|급여|진단", text):
        return "Disease/ Market News", "(주요질환*치료제)"
    if re.search(r"킴리아|예스카타|졸겐스마|스핀라자|넥사바|렌비마|키트루다|옵디보|아일리아|비오뷰|루센티스|엔허투|임핀지|울토미리스|업리즈나", text, re.I):
        return "Disease/ Market News", "경합/타사 제품"

    # 4) Industry / Policy News 불리언 조합 매칭 (요청 조합식 대거 탑재!)
    # [요청식 1] ((로슈 | Roche | 제넨텍 | 쥬가이) * (한국 | 본사 | 실적 | 대표 | 인사 | CSR | 사회공헌))
    if re.search(r"로슈|Roche|제넨텍|Genentech|쥬가이|Chugai", text, re.I) and re.search(r"한국|본사|실적|대표|인사|CSR|사회공헌", text):
        return "Industry/ Policy News", "(로슈*기업동향/CSR)"

    # [요청식 2] ((다국적 | 글로벌 | 외자사) * (제약사 | 제약업계) * (인사 | 동정 | 수상 | CSR | 사회공헌 | 인수 | 합병))
    if re.search(r"다국적|글로벌|외자사", text, re.I) and re.search(r"제약사|제약업계|제약기업|제약업체", text) and re.search(r"인사|동정|수상|CSR|사회공헌|인수|합병|리베이트", text):
        return "Industry/ Policy News", "(글로벌제약사*동향/CSR/인사)"

    # 기타 Industry 조합
    if re.search(r"임상시험|R&D|연구개발|특허", text, re.I) and re.search(r"의약품|약품|치료제|신약", text):
        return "Industry/ Policy News", "(R&D/특허*의약품)"
    if re.search(r"급여|접근성|보장성|보험|비급여", text) and re.search(r"의약품|약품|신약|항암|치료", text):
        return "Industry/ Policy News", "(급여/보장성*의약품)"
    if re.search(r"위험분담제|RSA|RWD|RWE|사전심의", text, re.I) and re.search(r"의약품|제약|치료제|도매", text):
        return "Industry/ Policy News", "(RSA/RWD*제약)"
    if re.search(r"환자단체총연합회|백혈병환우회|희귀난치성질환연합회", text) and re.search(r"항암제|치료제|탄원|정책|암|희귀질환|신약", text):
        return "Industry/ Policy News", "(환자단체*정책)"
    if re.search(r"리베이트|공정거래위원회|공정위|국세청|보건복지부|복지부|질병관리청|국민건강보험공단|건보공단|건강보험심사평가원|심평원|식품의약품안전처|식약처", text) and re.search(r"제약회사|제약업계|제약산업|제약사|외자사|의약품|비급여|급여", text):
        return "Industry/ Policy News", "(정부기관*제약업계)"
    if re.search(r"보건의료|헬스케어|제약|국회", text) and re.search(r"입법|발의|개정|보건복지위|정부규제", text):
        return "Industry/ Policy News", "(국회/입법*보건의료)"

    return None, None

# 5. 연관도 점수 자동 산정
def calculate_relevance_score(title, summary, category):
    full_text = f"{title} {summary}"
    score = 4
    if category == "Corporate News": score += 5
    elif category == "Product News": score += 4
    if any(k in full_text for k in ["로슈", "Roche", "한국로슈", "티쎈트릭", "바비스모", "에브리스디"]): score += 2
    if any(p in full_text for p in ["약가", "암질심", "위험분담제", "급여", "심평원", "식약처"]): score += 1
    return min(score, 10)

# 6. 뉴스 수집 로직
@st.cache_data(ttl=300)
def fetch_recent_news():
    results = []
    now = datetime.now()
    time_limit = now - timedelta(hours=36)

    for m in ALL_MEDIA_LIST:
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
                
                pub_date_str = pub_dt.strftime('%m/%d') if pub_dt else now.strftime('%m/%d')
                
                matched_cat, matched_kw = classify_article_by_rules(full_text)
                
                if matched_cat:
                    rel_score = calculate_relevance_score(title, summary, matched_cat)
                    results.append({
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
    
    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res = df_res.sort_values(by=["연관도점수", "Tier"], ascending=[False, True]).drop_duplicates(subset=["기사제목"], keep="first")
    return df_res

raw_df = fetch_recent_news()

# 7. UI 화면 구성
st.write(f"⏰ 실시간 수집된 주요 뉴스: **{len(raw_df)}건**")

if not raw_df.empty:
    if st.button("🎯 중요 기사 자동 선별하기 (Top 5 자동 체크)", type="primary"):
        auto_df = raw_df.copy()
        for cat in ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]:
            cat_indices = auto_df[auto_df["카테고리"] == cat].sort_values(by="연관도점수", ascending=False).head(5).index
            auto_df.loc[cat_indices, "선택"] = True
        st.session_state["analyzed_df"] = auto_df
        st.success("스마트 분석 완료! 카테고리별 핵심 기사 상위 5개가 선택되었습니다.")

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

    if all_edited_dfs:
        full_edited_df = pd.concat(all_edited_dfs, ignore_index=True)
        selected_df = full_edited_df[full_edited_df["선택"] == True]
        
        st.subheader(f"✅ 현재 총 **{len(selected_df)}건**의 기사가 선택되었습니다.")
        
        if st.button("🚀 선택한 기사로 뉴스레터 생성하기"):
            if not selected_df.empty:
                today_date = datetime.now().strftime('%b %d')
                output_text = f"**[Roche] Daily News Monitoring {today_date}**\n\nNEWS\n\n"
                
                for cat in categories:
                    output_text += f"**{cat}**\n"
                    cat_df = selected_df[selected_df["카테고리"] == cat]
                    
                    if not cat_df.empty:
                        for _, r in cat_df.iterrows():
                            output_text += f"* [{r['기사제목']}]({r['기사링크']}) ({r['매체명']} {r['게재일']})\n"
                    else:
                        output_text += "* (관련 최신 기사 없음)\n"
                    output_text += "\n"
                
                st.markdown(output_text)
                st.download_button("📋 텍스트 파일로 다운로드", output_text, f"Roche_News_{datetime.now().strftime('%Y%m%d')}.txt")
            else:
                st.warning("선택된 기사가 없습니다. 상단 버튼을 누르거나 직접 선택해 주세요!")
else:
    st.info("현재 수집된 기사가 없습니다.")
