import streamlit as st
import feedparser
import pandas as pd
import re
from datetime import datetime

st.set_page_config(page_title="한국로슈 전문지 모니터링", layout="wide")
st.title("💊 한국로슈 제약/의료 전문지 모니터링 System")

PROFESSIONAL_MEDIA = [
    {"media": "청년의사", "tier": "2 Tier", "rss": "https://www.docdocdoc.co.kr/rss/allArticle.xml"},
    {"media": "데일리팜", "tier": "2 Tier", "rss": "https://www.dailypharm.com/Users/Rss/Rss.html"},
    {"media": "약업신문", "tier": "2 Tier", "rss": "https://www.yakup.com/rss/"},
    {"media": "의학신문(일간보사)", "tier": "2 Tier", "rss": "https://www.bosa.co.kr/rss/allArticle.xml"},
    {"media": "라포르시안", "tier": "2 Tier", "rss": "https://www.rapportian.com/rss/allArticle.xml"},
    {"media": "메디파나뉴스", "tier": "2 Tier", "rss": "https://www.medipana.com/rss/allArticle.xml"},
    {"media": "의약뉴스", "tier": "2 Tier", "rss": "https://www.newsmp.com/rss/allArticle.xml"},
    {"media": "히트뉴스", "tier": "2 Tier", "rss": "https://www.hitnews.co.kr/rss/allArticle.xml"},
    {"media": "뉴스더보이스", "tier": "2 Tier", "rss": "https://www.newsthevoice.com/rss/allArticle.xml"}
]

KEYWORDS = {
    "Corporate News": ["로슈", "Roche", "제넨텍", "쥬가이"],
    "Product News": ["티쎈트릭", "Tecentriq", "알레센자", "바비스모", "에브리스디", "허셉틴", "아바스틴", "타미플루"],
    "Industry/Policy News": ["약가협상", "약가인하", "KRPIA", "혁신신약", "위험분담제", "RSA", "건강보험"]
}

@st.cache_data(ttl=300)
def fetch_pharma_news():
    results = []
    for m in PROFESSIONAL_MEDIA:
        try:
            feed = feedparser.parse(m["rss"])
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                full_text = f"{title} {summary}"
                
                matched_cat, matched_kw = None, None
                for cat, kw_list in KEYWORDS.items():
                    for kw in kw_list:
                        if re.search(re.escape(kw), full_text, re.IGNORECASE):
                            matched_cat, matched_kw = cat, kw
                            break
                    if matched_cat: break
                
                if matched_cat:
                    results.append({
                        "카테고리": matched_cat, "매체명": m["media"], "Tier": m["tier"],
                        "검색키워드": matched_kw, "기사제목": title, "기사링크": link
                    })
        except:
            pass
    return pd.DataFrame(results)

df = fetch_pharma_news()

tab1, tab2 = st.tabs(["📋 전문지 Raw 데이터 목록", "📰 중복 제거 뉴스레터 생성"])

with tab1:
    st.subheader(f"전문지 매체에서 총 {len(df)}건 포착됨")
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("현재 수집된 기사가 없습니다.")

with tab2:
    st.subheader("📰 중복 제거 및 뉴스레터 양식 생성")
    if st.button("🚀 최종 뉴스레터 텍스트 생성하기"):
        if not df.empty:
            # 제목 기준 중복 제거
            dedup = df.drop_duplicates(subset=["기사제목"], keep="first")
            st.success(f"원문 {len(df)}건 중 중복 제거 후 최종 {len(dedup)}건이 정리되었습니다!")
            st.divider()
            
            # 오늘 날짜
            today_str = datetime.now().strftime('%Y-%m-%d')
            output_text = f"**[한국로슈 Daily News Monitoring - {today_str}]**\n\n"
            
            # 카테고리 순서대로 출력
            for cat in KEYWORDS.keys():
                cat_df = dedup[dedup["카테고리"] == cat]
                if not cat_df.empty:
                    output_text += f"### {cat}\n"
                    for _, r in cat_df.iterrows():
                        # 요청하신 형태: * [기사제목](링크) (매체명 · MM/DD)
                        # 현재 날짜(MM/DD) 양식 포맷팅
                        date_str = datetime.now().strftime('%m/%d')
                        
                        output_text += f"* [{r['기사제목']}]({r['기사링크']}) ({r['매체명']} · {date_str})\n"
                    output_text += "\n"
            
            # 화면에 출력
            st.markdown(output_text)
            
            # 텍스트 복사 및 다운로드 버튼
            st.download_button("📋 텍스트 파일로 다운로드", output_text, f"로슈_뉴스레터_{datetime.now().strftime('%Y%m%d')}.txt")
        else:
            st.warning("수집된 데이터가 없습니다.")
            st.markdown(output_text)
