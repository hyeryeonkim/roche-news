import streamlit as st
import pandas as pd
import requests
import feedparser
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

st.set_page_config(page_title="Roche Daily News Monitoring", layout="wide")
st.title("📰 한국로슈 Daily News Monitoring Dashboard")

# 히스토리 저장 파일 경로
HISTORY_FILE = "selected_articles_history.csv"

# 네이버 Open API 인증키
NAVER_CLIENT_ID = "rdVf0JWe0wNFXCFrPKjI"
NAVER_CLIENT_SECRET = "cxR2cC5hmC"

CATEGORIES_LIST = ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]

# =========================================================
# 🎯 수집 및 분류용 키워드 정의
# =========================================================
SEARCH_KEYWORDS = [
    "한국로슈", "로슈", "Tecentriq", "티쎈트릭", "바비스모", "에브리스디", "엔스프링", 
    "오크레부스", "폴라이비", "컬럼비", "룬수미오", "페스코", "캐싸일라", "퍼제타", "허셉틴", "이토베비",
    "약평위", "암질심", "약가인하", "급여재평가", "위험분담제", "경평면제", "사용량약가연동",
    "척수성근위축증", "시신경척수염", "황반변성", "DLBCL", "소포성림프종"
]

CORPORATE_KEYWORDS = ["로슈", "Roche", "Genentech", "제넨텍", "제넨테크", "쥬가이", "Chugai", "한국로슈"]

PRODUCT_KEYWORDS = [
    "티쎈트릭", "Tecentriq", "아테졸리주맙", "atezolizumab", "맙테라", "Mabthera", "리툭시맙", "Rituximab", 
    "알레센자", "Alecensa", "알렉티닙", "alectinib", "셀셉트", "Cellcept", "미코페놀레이트모페틸", "마이코페놀레이트", 
    "아바스틴", "AVASTIN", "베바시주맙", "Bevacizumab", "타미플루", "Tamiflu", "조플루자", "Xofluza", "발록사비르마르복실", 
    "타쎄바", "타세바", "Tarceva", "허셉틴", "Herceptin", "트라스투주맙", "Trastuzumab", "마도파", "Madopar", 
    "퍼제타", "Perjeta", "퍼투주맙", "Pertuzumab", "캐싸일라", "Kadcyla", "가싸이바", "Gazyva", "오비누투주맙", 
    "폴리비", "폴라투주맙", "폴라이비", "엔스프링", "Enspryng", "사트랄리주맙", "에브리스디", "Evrysdi", "리스디플람", 
    "로즐리트렉", "Rozlytrek", "바비스모", "vabysmo", "파리시맙", "faricimab", "서스비모", "Susvimo", "라니비주맙", 
    "페스코", "페스고", "Phesgo", "모수네투주맙", "룬수미오", "오크레부스", "Ocrevus", "오크렐리주맙", "글로피타맙", 
    "컬럼비", "엘레비디스", "엘리비디스", "이나볼리십", "이토베비", "피아스카이", "크로발리맙", "트론티네맙"
]

DISEASE_KEYWORDS = [
    "킴리아", "예스카타", "졸겐스마", "스핀라자", "오나셈노진아베파르보벡", "뉴시너센", "넥사바", "렌비마", 
    "키트루다", "옵디보", "아일리아", "비오뷰", "루센티스", "아필리부", "아이델젠트", "알룬브릭", "로비큐아", 
    "엔허투", "이뮤도", "임핀지", "림카토", "민쥬비", "척수성근위축증", "SMA", "신경근육질환", 
    "시신경척수염", "NMOSD", "시신경척수염범주질환", "황반변성", "황반부종", "당뇨병성망막병증", "혈액암", 
    "당뇨병성황반부종", "인플루엔자", "유방암", "간암", "간세포암", "비소세포폐암", "파킨슨", "대한종양내과학회", 
    "신경과학회", "신경면역학회", "안과학회", "망막학회", "대한감염학회", "면역항암제", "항체의약품", "세포치료제", 
    "DMD", "뒤센근이영양증", "듀센근이영양증", "DLBCL", "엡킨리", "다발성경화증", "티사브리", "렘트라다", 
    "울토미리스", "Ultomiris", "라불리주맙", "Ravulizumab", "업리즈나", "이네빌리주맙", "티루캡", "피크레이", 
    "조기암", "조기유방암", "젊은유방암"
]

INDUSTRY_KEYWORDS = [
    "약평위", "암질심", "중증질환심의위원회", "심평원", "건보공단", "복지부", "식약처", "공정위", "보건복지위", "국정감사", "국감",
    "KRPIA", "한국글로벌의약산업협회", "KOBIA", "한국바이오의약품협회", "한국제약바이오협회",
    "약가협상", "약가인하", "약가제도", "경평면제", "위험분담제", "RSA", "경제성평가", "급여재평가",
    "고가의약품", "초고가신약", "사전심의", "사용량-약가연동", "RWD", "RWE", "희귀난치성질환", "희귀난치질환", "희귀질환",
    "혁신신약", "혁신형제약기업", "정밀의료", "정밀의학", "맞춤의학", "디지털헬스케어", "디지털바이오마커", "보건의료데이터", "신의료기술", "건보재정", "건강보험정책"
]

NEGATIVE_KEYWORDS = [
    "집값", "아파트", "부동산", "규제지역", "분양", "주택", "청약", "전세", 
    "증시", "주가", "코스피", "코스닥", "상한가", "특징주", "목표가", "치과", "한의원"
]

# 💡 URL 도메인 기반 실제 매체명 파싱 함수
def extract_media_name(link, original_link=""):
    target_link = original_link if original_link else link
    domain = urlparse(target_link).netloc.lower()

    domain_map = {
        "dailypharm.com": "데일리팜",
        "docdocdoc.co.kr": "청년의사",
        "medipana.com": "메디파나뉴스",
        "monews.co.kr": "메디칼업저버",
        "bosa.co.kr": "의학신문",
        "hitnews.co.kr": "히트뉴스",
        "pharmnews.com": "팜뉴스",
        "newsmp.com": "의약뉴스",
        "doctorsnews.co.kr": "의협신문",
        "koreabiomed.com": "KBR",
        "koreahealthlog.com": "코리아헬스로그",
        "dailymedi.com": "데일리메디",
        "medicaltimes.com": "메디칼타임즈",
        "yna.co.kr": "연합뉴스",
        "news1.kr": "뉴스1",
        "newsis.com": "뉴시스",
        "chosun.com": "조선일보",
        "joongang.co.kr": "중앙일보",
        "donga.com": "동아일보",
        "hankookilbo.com": "한국일보",
        "segye.com": "세계일보",
        "munhwa.com": "문화일보",
        "kmib.co.kr": "국민일보",
        "kukinews.com": "쿠키뉴스",
        "hani.co.kr": "한겨레",
        "seoul.co.kr": "서울신문",
        "mk.co.kr": "매일경제",
        "mbn.co.kr": "MBN",
        "hankyung.com": "한국경제",
        "wowtv.co.kr": "한국경제TV",
        "fnnews.com": "파이낸셜뉴스",
        "sedaily.co.kr": "서울경제",
        "heraldcorp.com": "헤럴드경제",
        "mt.co.kr": "머니투데이",
        "asiae.co.kr": "아시아경제",
        "edaily.co.kr": "이데일리",
        "etoday.co.kr": "이투데이",
        "dt.co.kr": "디지털타임스",
        "etnews.com": "전자신문",
        "zdnet.co.kr": "지디넷코리아",
        "thebell.co.kr": "더벨",
        "yakup.com": "약업신문",
        "kpanews.co.kr": "약사공론",
        "biospectator.com": "바이오스펙테이터"
    }

    for d, name in domain_map.items():
        if d in domain:
            return name

    # 도메인 파싱 실패 시 기본 구명
    cleaned_domain = domain.replace("www.", "").replace("m.", "").split(".")[0].capitalize()
    return cleaned_domain if cleaned_domain else "주요언론사"

# 텍스트 단어 유사도 단순 계산 함수
def calculate_jaccard_similarity(str1, str2):
    set1 = set(re.findall(r'\w+', str1.lower()))
    set2 = set(re.findall(r'\w+', str2.lower()))
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

# 카테고리 유연 자동 분류 규칙
def classify_article_by_rules(text):
    text_lower = text.lower()
    
    # 1. Product News
    for p in PRODUCT_KEYWORDS:
        if p.lower() in text_lower:
            return "Product News", p

    # 2. Corporate News
    if re.search(r"로슈|Roche|제넨텍|Genentech|쥬가이|Chugai", text, re.I):
        return "Corporate News", "로슈(Roche)"

    # 3. Industry / Policy News
    for ik in INDUSTRY_KEYWORDS:
        if ik.lower() in text_lower:
            return "Industry/ Policy News", ik

    # 4. Disease / Market News
    for dk in DISEASE_KEYWORDS:
        if dk.lower() in text_lower:
            return "Disease/ Market News", dk

    if re.search(r"급여|접근성|보장성|보험|비급여|약가|심평원|식약처", text):
        return "Industry/ Policy News", "(보건정책/급여)"

    if re.search(r"암|질환|치료제|임상|학회|투여|적응증", text):
        return "Disease/ Market News", "(질환/시장동향)"

    return None, None

# =========================================================
# 🎯 고도화 스코어링 엔진 (1점 베이스 Zero-based Approach)
# =========================================================
def calculate_relevance_score(title, summary, category):
    full_text = f"{title} {summary}"
    score = 1  # 기본 1점 시작

    # 🚫 [강력 감점 1] 컬럼비아 대학교 관련 연구 기사 오탐 제거 (-8점)
    if re.search(r"컬럼비아\s*대|컬럼비아대|컬럼비아\s*대학교|columbia\s*univ", full_text, re.I):
        return 1

    # 🚫 [강력 감점 2] 일반 생활건강/식습관/다이어트/칼럼
    if any(neg in full_text for neg in ["음식", "레시피", "여름철", "10계명", "운동법", "자가진단", "식습관"]):
        return 1

    # 🚫 [감점 3] 해외 소식 (FDA/EMA/글로벌 등) 중 국내 키워드가 없으면 후순위 (-2점)
    is_global = any(g_kw in full_text for g_kw in ["FDA", "EMA", "NCCN", "미국", "유럽", "글로벌", "본사"])
    is_domestic = any(d_kw in full_text for d_kw in ["한국", "국내", "식약처", "심평원", "건보공단", "복지부", "약평위", "암질심"])
    if is_global and not is_domestic:
        score -= 2

    # 🎯 [카테고리별 가점]
    if category == "Corporate News":
        score += 3
        if any(k in full_text for k in ["로슈", "Roche", "한국로슈"]): score += 3

    elif category == "Product News":
        score += 2
        if any(core in full_text for core in ["티쎈트릭", "바비스모", "에브리스디", "엔스프링", "오크레부스", "폴라이비", "컬럼비", "룬수미오", "페스코", "캐싸일라", "퍼제타", "허셉틴", "이토베비"]):
            score += 3

    elif category == "Disease/ Market News":
        score += 2
        combo_matched = False
        
        # SMA
        if any(p in full_text for p in ["졸겐스마", "스핀라자", "오나셈노진", "뉴시너센"]) and any(d in full_text for d in ["척수성근위축증", "SMA", "신경근육"]):
            score += 4; combo_matched = True
        # NMOSD / MS
        elif any(p in full_text for p in ["울토미리스", "업리즈나", "티사브리", "렘트라다", "라불리주맙", "이네빌리주맙"]) and any(d in full_text for d in ["시신경척수염", "NMOSD", "다발성경화증"]):
            score += 4; combo_matched = True
        # 안과 (nAMD / DME)
        elif any(p in full_text for p in ["아일리아", "비오뷰", "루센티스", "아필리부"]) and any(d in full_text for d in ["황반변성", "황반부종", "당뇨병성망막병증", "DME", "nAMD"]):
            score += 4; combo_matched = True
        # 혈액암 / DLBCL
        elif any(p in full_text for p in ["킴리아", "예스카타", "엡킨리", "앱킨리", "림카토", "민쥬비"]) and any(d in full_text for d in ["DLBCL", "소포성림프종", "거대B세포림프종", "혈액암"]):
            score += 4; combo_matched = True
        # HER2+ 유방암
        elif "엔허투" in full_text and re.search(r"유방암|HER2|HER2양성|HER2\+", full_text, re.I):
            score += 4; combo_matched = True

        if combo_matched and any(evt in full_text for evt in ["급여", "임상", "3상", "허가", "FDA", "약평위", "암질심"]):
            score += 1

        if any(kol in full_text for kol in ["교수", "연구팀", "발병률 1위", "주의보", "질병청 통계", "치료 가이드라인 개정", "학술대회발표"]):
            if any(r_dis in full_text for r_dis in ["유방암", "폐암", "간암", "혈액암", "황반변성", "척수성근위축증", "시신경척수염"]):
                score += 3

    elif category == "Industry/ Policy News":
        score += 3
        if any(p in full_text for p in ["약가인하", "약가협상", "약가제도", "위험분담제", "RSA", "경평면제", "급여재평가", "사용량-약가연동"]): score += 3
        if any(gov in full_text for gov in ["보건복지위", "국정감사", "국감", "법안", "발의", "입법", "식약처", "심평원"]): score += 2

    if any(k in title for k in ["로슈", "Roche", "티쎈트릭", "바비스모", "에브리스디", "알레센자", "페스코", "약가", "급여", "암질심", "약평위"]):
        score += 2

    return max(1, min(score, 10))

# =========================================================
# 📡 1. 네이버 뉴스 API 수집 함수 (최근 36시간 필터링)
# =========================================================
def fetch_naver_news(keyword, time_limit):
    results = []
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    enc_kw = quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news.json?query={enc_kw}&display=50&sort=date"
    
    try:
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code == 200:
            items = res.json().get("items", [])
            for item in items:
                title = re.sub(r'<[^>]+>', '', item.get("title", ""))
                summary = re.sub(r'<[^>]+>', '', item.get("description", ""))
                link = item.get("link", "")
                origin_link = item.get("originallink", "")
                
                pub_date_raw = item.get("pubDate", "")
                pub_dt = datetime.now()
                try:
                    pub_dt = datetime.strptime(pub_date_raw, '%a, %d %b %Y %H:%M:%S +0900')
                except:
                    pass

                # ⏱️ [최근 36시간 이전 기사 배제]
                if pub_dt < time_limit:
                    continue

                # 💡 명확한 매체명 추출
                media_name = extract_media_name(link, origin_link)

                full_text = f"{title} {summary}"
                if any(neg in full_text for neg in NEGATIVE_KEYWORDS):
                    continue

                matched_cat, matched_kw = classify_article_by_rules(full_text)
                if matched_cat:
                    score = calculate_relevance_score(title, summary, matched_cat)
                    results.append({
                        "선택": False,
                        "연관도점수": score,
                        "카테고리": matched_cat,
                        "매체명": media_name,
                        "검색키워드": matched_kw,
                        "기사제목": title,
                        "기사링크": origin_link if origin_link else link,
                        "게재일": pub_dt.strftime('%m/%d'),
                        "pub_dt": pub_dt
                    })
    except Exception:
        pass
    return results

# =========================================================
# 📡 2. 구글 뉴스 RSS 수집 함수 (최근 36시간 필터링)
# =========================================================
def fetch_google_news(keyword, time_limit):
    results = []
    enc_kw = quote(f"{keyword} when:2d")
    rss_url = f"https://news.google.com/rss/search?q={enc_kw}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")
            
            pub_dt = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                from time import mktime
                pub_dt = datetime.fromtimestamp(mktime(entry.published_parsed))

            if pub_dt < time_limit:
                continue

            media_name = "구글제휴매체"
            if " - " in title:
                parts = title.rsplit(" - ", 1)
                title = parts[0]
                media_name = parts[1]

            full_text = f"{title} {summary}"
            if any(neg in full_text for neg in NEGATIVE_KEYWORDS):
                continue

            matched_cat, matched_kw = classify_article_by_rules(full_text)
            if matched_cat:
                score = calculate_relevance_score(title, summary, matched_cat)
                results.append({
                    "선택": False,
                    "연관도점수": score,
                    "카테고리": matched_cat,
                    "매체명": media_name,
                    "검색키워드": matched_kw,
                    "기사제목": title,
                    "기사링크": link,
                    "게재일": pub_dt.strftime('%m/%d'),
                    "pub_dt": pub_dt
                })
    except Exception:
        pass
    return results

# =========================================================
# 🚀 전체 뉴스 통합 수집 및 자동 중복 정돈 함수
# =========================================================
@st.cache_data(ttl=1800)
def fetch_all_integrated_news():
    all_raw = []
    time_limit = datetime.now() - timedelta(hours=36)
    
    # 카테고리 균형을 위해 대표 키워드 균등 수집
    for kw in SEARCH_KEYWORDS:
        all_raw.extend(fetch_naver_news(kw, time_limit))
        all_raw.extend(fetch_google_news(kw, time_limit))
        
    df = pd.DataFrame(all_raw)
    if df.empty:
        return df

    # 완전 동일 기사 중복 제거
    df = df.drop_duplicates(subset=["기사제목"], keep="first")

    # 과거 선택 학습 히스토리 가산점 부여
    if os.path.exists(HISTORY_FILE):
        try:
            history_df = pd.read_csv(HISTORY_FILE)
            if len(history_df) >= 5 and "기사제목" in history_df.columns:
                past_titles = history_df["기사제목"].dropna().tolist()
                for idx, row in df.iterrows():
                    curr_title = row["기사제목"]
                    max_sim = max([calculate_jaccard_similarity(curr_title, pt) for pt in past_titles], default=0)
                    if max_sim > 0.35:
                        df.loc[idx, "연관도점수"] = min(10, df.loc[idx, "연관도점수"] + round(max_sim * 2, 1))
        except Exception:
            pass

    df = df.sort_values(by=["연관도점수", "pub_dt"], ascending=[False, False]).drop(columns=["pub_dt"])
    return df

def save_selected_history(selected_df):
    try:
        save_data = selected_df.copy()
        save_data["선택시각"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if os.path.exists(HISTORY_FILE):
            save_data.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            save_data.to_csv(HISTORY_FILE, mode='w', header=True, index=False, encoding='utf-8-sig')
    except Exception:
        pass

# =========================================================
# 💻 UI 메인 대시보드 화면
# =========================================================
if "news_df" not in st.session_state:
    st.session_state["news_df"] = fetch_all_integrated_news()

col_title, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 실시간 뉴스 새로고침"):
        st.cache_data.clear()
        st.session_state["news_df"] = fetch_all_integrated_news()
        st.session_state.pop("analyzed_df", None)
        st.rerun()

raw_df = st.session_state["news_df"]

history_count = 0
history_df = pd.DataFrame()
if os.path.exists(HISTORY_FILE):
    try:
        history_df = pd.read_csv(HISTORY_FILE)
        history_count = len(history_df)
    except Exception:
        pass

st.write(f"⚡ 최근 36시간 통합 포털 수집 완료: 최신 기사 **{len(raw_df)}건** | 🧠 AI 학습 데이터 축적: **{history_count}건**")

if not raw_df.empty:
    if st.button("🎯 중요 기사 자동 선별하기 (유사 보도자료 중 대표 1건만 선별)", type="primary"):
        auto_df = raw_df.copy()
        
        for cat in CATEGORIES_LIST:
            cat_df = auto_df[auto_df["카테고리"] == cat].sort_values(by="연관도점수", ascending=False)
            selected_indices = []
            selected_titles = []
            
            for idx, row in cat_df.iterrows():
                title = row["기사제목"]
                is_duplicate = False
                for s_title in selected_titles:
                    sim = calculate_jaccard_similarity(title, s_title)
                    if sim > 0.4:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    selected_indices.append(idx)
                    selected_titles.append(title)
                
                if len(selected_indices) >= 5:
                    break
            
            auto_df.loc[selected_indices, "선택"] = True
            
        st.session_state["analyzed_df"] = auto_df
        st.success("스마트 대표 기사 선별 완료!")

    display_df = st.session_state.get("analyzed_df", raw_df)
    tabs = st.tabs([f"📌 {cat}" for cat in CATEGORIES_LIST])
    
    all_edited_dfs = []
    
    for i, cat in enumerate(CATEGORIES_LIST):
        with tabs[i]:
            cat_df = display_df[display_df["카테고리"] == cat].copy()
            st.markdown(f"### {cat} ({len(cat_df)}건)")
            
            if not cat_df.empty:
                edited = st.data_editor(
                    cat_df,
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택 ✅", default=False),
                        "카테고리": st.column_config.SelectboxColumn(
                            "카테고리 🔄",
                            options=CATEGORIES_LIST,
                            required=True
                        ),
                        "연관도점수": st.column_config.NumberColumn("연관도 🎯"),
                        "기사링크": st.column_config.LinkColumn("기사링크")
                    },
                    disabled=["연관도점수", "매체명", "검색키워드", "기사제목", "기사링크", "게재일"],
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
                save_selected_history(selected_df)
                
                now = datetime.now()
                title_date_str = now.strftime('%b %d')
                header_date_str = now.strftime('%d %B, %Y')
                
                html_body = f'<div style="font-family:\'Segoe UI\',Arial,sans-serif;max-width:680px;color:#333333;line-height:1.5;border:1px solid #e2e8f0;padding:25px;border-radius:8px;background-color:#ffffff;">'
                html_body += f'<div style="border-bottom:2px solid #0066CC;padding-bottom:12px;margin-bottom:20px;"><table style="width:100%;border-collapse:collapse;"><tr><td style="font-size:24px;font-weight:bold;color:#0066CC;">Roche Daily News Highlights</td><td style="text-align:right;font-size:14px;color:#666666;vertical-align:bottom;">{header_date_str}</td></tr></table></div>'
                html_body += f'<div style="font-size:20px;font-weight:bold;color:#222222;margin-bottom:18px;letter-spacing:0.5px;">NEWS</div>'
                
                for cat in CATEGORIES_LIST:
                    cat_df = selected_df[selected_df["카테고리"] == cat]
                    html_body += f'<div style="margin-bottom:22px;"><div style="font-size:15px;font-weight:bold;color:#0066CC;margin-bottom:8px;border-bottom:1px dashed #cbd5e1;padding-bottom:4px;">{cat}</div><ul style="margin:0;padding-left:18px;font-size:14px;color:#333333;">'
                    
                    if not cat_df.empty:
                        for _, r in cat_df.iterrows():
                            html_body += f'<li style="margin-bottom:6px;"><a href="{r["기사링크"]}" target="_blank" style="color:#1a0dab;text-decoration:underline;font-weight:500;">{r["기사제목"]}</a> <span style="color:#666666;font-size:13px;">({r["매체명"]} {r["게재일"]})</span></li>'
                    else:
                        html_body += f'<li style="color:#888888;list-style-type:none;margin-left:-18px;">(관련 주요 기사 없음)</li>'
                    
                    html_body += f'</ul></div>'
                
                html_body += f'<div style="margin-top:30px;padding-top:15px;border-top:1px solid #e2e8f0;font-size:12px;color:#666666;line-height:1.6;"><p style="font-weight:bold;color:#333333;margin:0 0 4px 0;">[한국로슈 Communications & Public Affairs Chapter]</p><p style="margin:0;">이미규 | migyu.lee@roche.com</p><p style="margin:0;">김혜련 | hyeryeon.kim@roche.com</p><p style="margin:0 0 10px 0;">박수윤 | sue.park@roche.com</p><p style="color:#999999;margin:0;">© {now.year} Roche Korea Co.,Ltd</p></div></div>'

                st.success("🎉 뉴스레터 생성이 완료되었습니다! (선택 데이터가 기록되었습니다)")
                st.info(f"📌 **메일 제목:** [Roche] Daily News Monitoring {title_date_str}")
                
                st.markdown("### 📧 이메일 뉴스레터 완제품 (마우스 드래그 복사)")
                st.html(html_body)
                
                st.divider()
                st.download_button(
                    label="💾 이메일용 HTML 파일 다운로드",
                    data=html_body,
                    file_name=f"Roche_News_{now.strftime('%Y%m%d')}.html",
                    mime="text/html"
                )
            else:
                st.warning("선택된 기사가 없습니다.")

st.divider()

# ★ 🧠 AI 학습 데이터 개별 / 전체 삭제 및 관리 센터 ★
with st.expander("🧠 AI 학습용 데이터 관리 & 개별 삭제 센터 (클릭하여 열기)", expanded=False):
    if os.path.exists(HISTORY_FILE) and not history_df.empty:
        st.write(f"현재 총 **{len(history_df)}건**의 선택 데이터가 누적 저장되어 있습니다.")
        st.caption("💡 지우고 싶은 기사의 '삭제 선택 ✅' 칸에 체크한 뒤, 아래 [🗑️ 선택한 항목만 삭제] 버튼을 누르세요.")
        
        history_df_edit = history_df.copy()
        history_df_edit.insert(0, "삭제 선택", False)
        
        edited_history = st.data_editor(
            history_df_edit,
            column_config={
                "삭제 선택": st.column_config.CheckboxColumn("삭제 선택 ✅", default=False),
                "기사링크": st.column_config.LinkColumn("기사링크")
            },
            disabled=["선택시각", "카테고리", "매체명", "기사제목", "기사링크", "검색키워드", "연관도점수", "게재일"],
            hide_index=True,
            use_container_width=True,
            key="history_editor"
        )
        
        col_del1, col_del2, col_del3 = st.columns([1, 1, 1])
        
        with col_del1:
            if st.button("🗑️ 선택한 항목만 삭제", type="primary"):
                to_keep = edited_history[edited_history["삭제 선택"] == False].drop(columns=["삭제 선택"])
                if len(to_keep) < len(history_df):
                    to_keep.to_csv(HISTORY_FILE, index=False, encoding='utf-8-sig')
                    st.success("선택한 항목이 정상적으로 삭제되었습니다!")
                    st.rerun()
                else:
                    st.warning("삭제할 항목이 선택되지 않았습니다.")

        with col_del2:
            csv_data = history_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 누적 데이터 CSV 다운로드",
                data=csv_data,
                file_name=f"Roche_History_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
            
        with col_del3:
            if st.button("🔥 학습 데이터 전체 초기화"):
                os.remove(HISTORY_FILE)
                st.success("모든 히스토리 데이터가 초기화되었습니다!")
                st.rerun()
    else:
        st.info("현재 축적된 AI 학습 데이터가 없습니다. 뉴스레터를 생성하면 선택된 기사가 여기에 저장됩니다.")
