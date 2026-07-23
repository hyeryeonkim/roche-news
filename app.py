import streamlit as st
import feedparser
import pandas as pd
import re
from datetime import datetime, timedelta
from time import mktime

st.set_page_config(page_title="Roche Daily News Monitoring", layout="wide")
st.title("📰 한국로슈 Daily News Monitoring Dashboard (지능형 스크리닝)")

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

# 2. 키워드 사전 및 제외 키워드
KEYWORDS = {
    "Corporate News": ["로슈", "Roche", "제넨텍", "Genentech", "쥬가이", "Chugai", "한국로슈"],
    "Product News": ["티쎈트릭", "Tecentriq", "알레센자", "Alecensa", "바비스모", "Vabysmo", "에브리스디", "Evrysdi", "허셉틴", "Herceptin", "아바스틴", "Avastin", "타미플루", "Tamiflu", "조플루자", "Xofluza", "캐싸일라", "Kadcyla", "퍼제타", "Perjeta", "폴리비", "Polivy", "페스고", "Phesgo", "로즐리트렉", "Rozlytrek"],
    "Disease/ Market News": ["루푸스", "다발성경화증", "척수성근위축증", "SMA", "시신경척수염", "NMOSD", "황반변성", "유방암", "간암", "폐암", "면역항암제", "암질심", "중증질환심의위원회", "FDA", "임상 3상", "임상3상", "RLT", "항암제"],
    "Industry/ Policy News": ["약가협상", "약가인하", "KRPIA", "한국글로벌의약산업협회", "혁신신약", "위험분담제", "RSA", "건강보험공단", "심평원", "건강보험심사평가원", "식약처", "보건복지부", "수가", "R&D"]
}

NEGATIVE_KEYWORDS = ["집값", "아파트", "부동산", "규제지역", "분양", "주택", "청약", "전세", "증시", "주가", "코스피", "코스닥", "상한가", "특징주", "목표가"]

# 3. 자체 연관도 점수 계산 알고리즘
def calculate_relevance_score(title, summary, category):
    full_text = f"{title} {summary}"
    score = 3  # 기본 점수
    
    # 1) 로슈 / 브랜드 직접 언급 (최상위 가점 +5)
    if any(k in full_text for k in ["로슈", "Roche", "한국로슈", "제넨텍", "쥬가이"]):
        score += 5
        
    # 2) 로슈 주요 제품명 언급 (+4)
    if any(p in full_text for p in ["티쎈트릭", "바비스모", "에브리스디", "알레센자", "허셉틴", "아바스틴", "타미플루", "폴리비", "페스고"]):
        score += 4
        
    # 3) 중요 정책/약가 이슈 (+2)
    if any(policy in full_text for policy in ["약가", "암질심", "위험분담제", "RSA", "급여", "심평원", "식약처 허가"]):
        score += 2
        
    # 4) 제목에 직접 키워드가 포함된 경우 (+1 추가)
    if any(k in title for k in ["로슈", "Roche", "약가", "허가", "급여"]):
        score += 1
        
    return min(score, 10) # 최대 10점

# 4. 뉴스 수집 및 처리
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
                
                matched_cat, matched_kw = None, None
                for cat, kw_list in KEYWORDS.items():
                    for kw in kw_list:
                        if re.search(re.escape(kw), full_text, re.IGNORECASE):
                            matched_cat, matched_kw = cat, kw
                            break
                    if matched_cat: break
                
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
        df_res = df_res.sort_values(by=["Tier", "매체명"]).drop_duplicates(subset=["기사제목"], keep="first")
    return df_res

raw_df = fetch_recent_news()

# 5. UI 화면
st.write(f"⏰ 수집된 최근 기사: **{len(raw_df)}건**")

if not raw_df.empty:
    # 지능형 자동 선별 버튼
    if st.button("🎯 중요 기사 자동 선별하기 (Top 5 자동 체크)", type="primary"):
        auto_df = raw_df.copy()
        # 카테고리별 연관도 점수 상위 5개 자동 체크
        for cat in KEYWORDS.keys():
            cat_indices = auto_df[auto_df["카테고리"] == cat].sort_values(by="연관도점수", ascending=False).head(5).index
            auto_df.loc[cat_indices, "선택"] = True
        st.session_state["analyzed_df"] = auto_df
        st.success("스마트 분석 완료! 카테고리별 핵심 기사 상위 5개가 선택되었습니다.")

    display_df = st.session_state.get("analyzed_df", raw_df)

    tab_names = list(KEYWORDS.keys())
    tabs = st.tabs([f"📌 {cat}" for cat in tab_names])
    
    all_edited_dfs = []
    
    for i, cat in enumerate(tab_names):
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
                
                for cat in KEYWORDS.keys():
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
                st.warning("선택된 기사가 없습니다. 상단에서 자동 선별 버튼을 누르거나 체크박스를 직접 클릭해 주세요!")
else:
    st.info("현재 수집된 기사가 없습니다.")
