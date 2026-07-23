import streamlit as st
import feedparser
import pandas as pd
import re
from datetime import datetime
from time import mktime

st.set_page_config(page_title="Roche Daily News Monitoring", layout="wide")
st.title("📰 한국로슈 Daily News Monitoring Dashboard")

# 1. 일간지, 경제지, 전문지 전체 수집 매체 리스트
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

# 2. 로슈 모니터링 키워드 사전
KEYWORDS = {
    "Corporate News": [
        "로슈", "Roche", "제넨텍", "Genentech", "쥬가이", "Chugai", "한국로슈"
    ],
    "Product News": [
        "티쎈트릭", "Tecentriq", "알레센자", "Alecensa", "바비스모", "Vabysmo", 
        "에브리스디", "Evrysdi", "허셉틴", "Herceptin", "아바스틴", "Avastin", 
        "타미플루", "Tamiflu", "조플루자", "Xofluza", "캐싸일라", "Kadcyla", 
        "퍼제타", "Perjeta", "폴리비", "Polivy", "페스고", "Phesgo", 
        "로즐리트렉", "Rozlytrek", "엔트렉티닙", "가싸이바", "Gazyva", "엔스프링", "Enspryng"
    ],
    "Disease/ Market News": [
        "루푸스", "다발성경화증", "척수성근위축증", "SMA", "시신경척수염", "NMOSD", 
        "황반변성", "유방암", "간암", "폐암", "면역항암제", "암질심", "중증질환심의위원회", 
        "FDA", "임상 3상", "임상3상", "조기 승인", "RLT", "항암제"
    ],
    "Industry/ Policy News": [
        "약가협상", "약가인하", "KRPIA", "한국글로벌의약산업협회", "혁신신약", 
        "위험분담제", "RSA", "건강보험공단", "건보공단", "심평원", "건강보험심사평가원", 
        "식약처", "보건복지부", "수가", "학술대회", "R&D"
    ]
}

# 3. 부동산/일반경제 등 헬스케어 무관 기사 제거용 제외 키워드 (Negative Keywords)
NEGATIVE_KEYWORDS = [
    "집값", "아파트", "부동산", "규제지역", "분양", "주택", "청약", "전세", "월세",
    "증시", "주가", "코스피", "코스닥", "상한가", "특징주", "매수", "목표가", "종목"
]

# 4. 뉴스 수집 함수
@st.cache_data(ttl=300)
def fetch_all_news():
    results = []
    for m in ALL_MEDIA_LIST:
        try:
            feed = feedparser.parse(m["rss"])
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", entry.get("description", ""))
                full_text = f"{title} {summary}"
                
                # 1) 제외 키워드가 포함되어 있다면 걸러냄
                if any(neg in full_text for neg in NEGATIVE_KEYWORDS):
                    continue
                
                # 2) 실제 기사 게재 날짜 파싱 (MM/DD)
                pub_date_str = datetime.now().strftime('%m/%d')
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                    pub_date_str = dt.strftime('%m/%d')
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    dt = datetime.fromtimestamp(mktime(entry.updated_parsed))
                    pub_date_str = dt.strftime('%m/%d')
                
                # 3) 카테고리 매칭
                matched_cat, matched_kw = None, None
                for cat, kw_list in KEYWORDS.items():
                    for kw in kw_list:
                        if re.search(re.escape(kw), full_text, re.IGNORECASE):
                            matched_cat, matched_kw = cat, kw
                            break
                    if matched_cat: break
                
                if matched_cat:
                    results.append({
                        "선택": False, # 체크박스 기본값
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
        # 중복 제거 및 정렬
        df_res = df_res.sort_values(by=["Tier", "매체명"]).drop_duplicates(subset=["기사제목"], keep="first")
    return df_res

raw_df = fetch_all_news()

# 5. UI 화면
st.subheader(f"📋 실시간 수집된 기사 ({len(raw_df)}건)")
st.info("💡 **사용 방법:** 아래 표의 맨 앞 [선택] 열에 있는 체크박스(✅)를 눌러 포함시킬 기사를 고른 후, 맨 아래 '뉴스레터 생성' 버튼을 누르세요.")

if not raw_df.empty:
    # 대시보드 내 체크박스 편집 표 (st.data_editor)
    edited_df = st.data_editor(
        raw_df,
        column_config={
            "선택": st.column_config.CheckboxColumn(
                "선택 ✅",
                help="뉴스레터에 포함할 기사를 선택하세요.",
                default=False,
            ),
            "기사링크": st.column_config.LinkColumn("기사링크")
        },
        disabled=["카테고리", "매체명", "Tier", "검색키워드", "기사제목", "기사링크", "게재일"],
        hide_index=True,
        use_container_width=True
    )
    
    st.divider()
    
    # 선택된 기사만 추출
    selected_df = edited_df[edited_df["선택"] == True]
    st.write(f"현재 선택된 기사: **{len(selected_df)}건**")
    
    if st.button("🚀 선택한 기사로 뉴스레터 생성하기"):
        if not selected_df.empty:
            today_date = datetime.now().strftime('%b %d')
            output_text = f"**[Roche] Daily News Monitoring {today_date}**\n\n"
            output_text += "NEWS\n\n"
            
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
            st.warning("선택된 기사가 없습니다. 위의 표에서 뉴스레터에 넣을 기사의 체크박스를 먼저 클릭해 주세요!")
else:
    st.info("현재 수집된 기사가 없습니다.")
