import streamlit as st
import pandas as pd
import requests
import feedparser
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse

st.set_page_config(page_title="Roche Daily News Monitoring (Trade Only)", layout="wide")
st.title("📰 한국로슈 전문지(74개) 전용 Monitoring Dashboard")

HISTORY_FILE = "selected_articles_history.csv"

# 네이버 Open API 인증키
NAVER_CLIENT_ID = "rdVf0JWe0wNFXCFrPKjI"
NAVER_CLIENT_SECRET = "cxR2cC5hmC"

CATEGORIES_LIST = ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]

# =========================================================
# 🎯 74개 전문지 마스터 라인업 정의
# =========================================================
# Track A: 네이버 제휴 전문지 29개
TRACK_A_MEDIA = [
    "데일리팜", "청년의사", "데일리메디", "메디칼타임즈", "메디칼업저버", "메디파나뉴스", "팜뉴스", 
    "의약뉴스", "의협신문", "의학신문", "KBR", "코리아헬스로그", "히트뉴스", "메디게이트뉴스", 
    "메디소비자뉴스", "코메디닷컴", "메디팜스투데이", "약사공론", "e-의료정보", "메디칼트리뷴", 
    "라포르시안", "후생신보", "약업신문", "더바이오", "바이오스펙테이터", "메디컬월드뉴스", 
    "보건신문", "메디컬투데이", "메디코파마"
]

# Track B: 구글 우회 제휴 전문지 8개 (매체명: 타깃 도메인)
TRACK_B_MEDIA = {
    "뉴스더보이스": "newsthevoice.com",
    "메디포뉴스": "medifonews.com",
    "현대건강신문": "hhealth.co.kr",
    "식약신문": "fmnews.kr",
    "의계신문(메드월드뉴스)": "medworld.co.kr",
    "헬스오": "healtho.co.kr",
    "바이오타임즈": "biotimes.co.kr",
    "팍스메디컬뉴스": "paxmedicalnews.com"
}

# Track C: 직접 크롤링 전문지 37개 (매체명: 사이트 URL)
TRACK_C_MEDIA = {
    "병원신문": "http://www.khanews.com",
    "의사신문": "http://www.doctorstimes.com",
    "헬스코리아뉴스": "http://www.hkn24.com",
    "파마타임스": "https://www.pharmatimes.co.kr",
    "메디컬헤럴드": "http://www.medherald.co.kr",
    "데일리메디팜": "http://www.dailymedipharm.com",
    "건강보험신문": "https://www.gunbo.kr",
    "건강보험저널": "https://hijournal.co.kr",
    "닥터W": "http://www.doctorw.co.kr",
    "메디팜헬스뉴스": "http://www.medipharmhealth.co.kr",
    "메디칼통신": "https://www.medicalagency.co.kr",
    "보건타임즈": "http://www.bktimes.net",
    "사이언스엠디뉴스": "http://www.sciencemd.com",
    "식약일보": "https://www.kfdn.co.kr",
    "아이팜뉴스": "http://www.ipharmnews.com",
    "의약품유통신문": "http://www.kpdanews.kr",
    "엠디저널": "http://www.mdjournal.kr",
    "헬스포커스뉴스": "http://www.healthfocus.co.kr",
    "클리닉저널": "http://www.clinicjournal.co.kr",
    "헬스앤라이프": "http://www.healthi.kr",
    "파마투데이": "http://www.pharmatoday.co.kr",
    "메디트리트저널": "https://www.mtjpost.com",
    "메디텔레스코프뉴스": "https://www.meditelescope.co.kr",
    "성인병뉴스": "https://www.cdpnews.co.kr",
    "안티에이징뉴스": "https://medichacha.co.kr",
    "엠디포스트": "http://www.mdpost.co.kr",
    "한국식약경제신문": "http://www.kefm.co.kr",
    "헬스앤마켓": "https://www.h-money.co.kr",
    "웰스데일리": "http://www.wealthdaily.co.kr",
    "메디팜뉴스": "http://www.medipharmnews.com",
    "헬스비즈": "http://www.healthbiz.co.kr",
    "뉴스맥": "http://www.newsmac.co.kr",
    "키닥터": "http://www.keydoctor.co.kr",
    "약품신문": "https://www.yakpum.co.kr"
}

# =========================================================
# 🎯 키워드 세트 정의
# =========================================================
SEARCH_KEYWORDS = [
    "로슈", "Roche", "한국로슈", "티쎈트릭", "바비스모", "에브리스디", "엔스프링", 
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

def calculate_jaccard_similarity(str1, str2):
    set1 = set(re.findall(r'\w+', str1.lower()))
    set2 = set(re.findall(r'\w+', str2.lower()))
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

def identify_media_name(link, default_name="전문지"):
    domain = urlparse(link).netloc.lower()
    
    mapping = {
        "dailypharm.com": "데일리팜",
        "docdocdoc.co.kr": "청년의사",
        "dailymedi.com": "데일리메디",
        "medicaltimes.com": "메디칼타임즈",
        "monews.co.kr": "메디칼업저버",
        "medipana.com": "메디파나뉴스",
        "pharmnews.com": "팜뉴스",
        "newsmp.com": "의약뉴스",
        "doctorsnews.co.kr": "의협신문",
        "bosa.co.kr": "의학신문",
        "koreabiomed.com": "KBR",
        "koreahealthlog.com": "코리아헬스로그",
        "hitnews.co.kr": "히트뉴스",
        "medigate.net": "메디게이트뉴스",
        "medisobizanews.com": "메디소비자뉴스",
        "kormedi.com": "코메디닷컴",
        "mediphasstoday.com": "메디팜스투데이",
        "kpanews.co.kr": "약사공론",
        "e-mednews.com": "e-의료정보",
        "medicaltribune.co.kr": "메디칼트리뷴",
        "rapportian.com": "라포르시안",
        "hns.or.kr": "후생신보",
        "yakup.com": "약업신문",
        "thebio.co.kr": "더바이오",
        "biospectator.com": "바이오스펙테이터",
        "medicalworldnews.co.kr": "메디컬월드뉴스",
        "bokgunnews.com": "보건신문",
        "mdtoday.co.kr": "메디컬투데이",
        "medicopharma.co.kr": "메디코파마"
    }
    
    for d, name in mapping.items():
        if d in domain:
            return name
    return default_name

def classify_article_by_rules(text):
    text_lower = text.lower()
    for p in PRODUCT_KEYWORDS:
        if p.lower() in text_lower:
            return "Product News", p

    if re.search(r"로슈|Roche|제넨텍|Genentech|쥬가이|Chugai", text, re.I):
        return "Corporate News", "로슈(Roche)"

    for ik in INDUSTRY_KEYWORDS:
        if ik.lower() in text_lower:
            return "Industry/ Policy News", ik

    for dk in DISEASE_KEYWORDS:
        if dk.lower() in text_lower:
            return "Disease/ Market News", dk

    if re.search(r"급여|접근성|보장성|보험|비급여|약가|심평원|식약처", text):
        return "Industry/ Policy News", "(보건정책/급여)"

    if re.search(r"암|질환|치료제|임상|학회|투여|적응증", text):
        return "Disease/ Market News", "(질환/시장동향)"

    return None, None

def calculate_relevance_score(title, summary, category):
    full_text = f"{title} {summary}"
    score = 1

    if re.search(r"컬럼비아\s*대|컬럼비아대|컬럼비아\s*대학교|columbia\s*univ", full_text, re.I):
        return 1
    if any(neg in full_text for neg in ["음식", "레시피", "여름철", "10계명", "운동법", "자가진단", "식습관"]):
        return 1

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
        if any(p in full_text for p in ["졸겐스마", "스핀라자", "오나셈노진", "뉴시너센"]) and any(d in full_text for d in ["척수성근위축증", "SMA", "신경근육"]):
            score += 4; combo_matched = True
        elif any(p in full_text for p in ["울토미리스", "업리즈나", "티사브리", "렘트라다"]) and any(d in full_text for d in ["시신경척수염", "NMOSD", "다발성경화증"]):
            score += 4; combo_matched = True
        elif any(p in full_text for p in ["아일리아", "비오뷰", "루센티스", "아필리부"]) and any(d in full_text for d in ["황반변성", "황반부종", "DME", "nAMD"]):
            score += 4; combo_matched = True
        elif any(p in full_text for p in ["킴리아", "예스카타", "엡킨리"]) and any(d in full_text for d in ["DLBCL", "소포성림프종", "혈액암"]):
            score += 4; combo_matched = True
        elif "엔허투" in full_text and re.search(r"유방암|HER2|HER2양성", full_text, re.I):
            score += 4; combo_matched = True

        if combo_matched and any(evt in full_text for evt in ["급여", "임상", "3상", "허가", "FDA", "약평위", "암질심"]):
            score += 1

    elif category == "Industry/ Policy News":
        score += 3
        if any(p in full_text for p in ["약가인하", "약가협상", "약가제도", "위험분담제", "RSA", "경평면제", "급여재평가", "사용량-약가연동"]): score += 3

    if any(k in title for k in ["로슈", "Roche", "티쎈트릭", "바비스모", "에브리스디", "알레센자", "페스코", "약가", "급여", "암질심", "약평위"]):
        score += 2

    return max(1, min(score, 10))

# =========================================================
# 📡 1. Track A: 네이버 API 전용 수집 (29개 전문지 필터링)
# =========================================================
def fetch_track_a_news(keyword, time_limit):
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
                link = item.get("originallink", item.get("link", ""))
                
                pub_date_raw = item.get("pubDate", "")
                pub_dt = datetime.now()
                try:
                    pub_dt = datetime.strptime(pub_date_raw, '%a, %d %b %Y %H:%M:%S +0900')
                except:
                    pass

                if pub_dt < time_limit:
                    continue

                media_name = identify_media_name(link)
                if media_name not in TRACK_A_MEDIA:
                    continue

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
# 📡 2. Track B: 구글 뉴스 site: 우회 수집 (8개 전문지)
# =========================================================
def fetch_track_b_news(keyword, time_limit):
    results = []
    for media_name, domain in TRACK_B_MEDIA.items():
        enc_kw = quote(f"site:{domain} {keyword}")
        rss_url = f"https://news.google.com/rss/search?q={enc_kw}&hl=ko&gl=KR&ceid=KR:ko"
        
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:5]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")
                
                if " - " in title:
                    title = title.rsplit(" - ", 1)[0]

                pub_dt = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    from time import mktime
                    pub_dt = datetime.fromtimestamp(mktime(entry.published_parsed))

                if pub_dt < time_limit:
                    continue

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
# 📡 3. Track C: 정규식 기반 직접 도메인 크롤링 (37개 전문지)
# =========================================================
def fetch_track_c_news(time_limit):
    results = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    for media_name, target_url in TRACK_C_MEDIA.items():
        try:
            res = requests.get(target_url, headers=headers, timeout=4)
            if res.status_code == 200:
                html_text = res.text
                # 정규식으로 <a> 태그 내 링크 및 제목 추출 (bs4 패키지 무의존)
                pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
                matches = re.findall(pattern, html_text, re.IGNORECASE | re.DOTALL)
                
                for href, title_raw in matches:
                    title = re.sub(r'<[^>]+>', '', title_raw).strip()
                    title = re.sub(r'\s+', ' ', title)
                    
                    if len(title) < 10 or any(ignore in href.lower() for ignore in ["javascript", "login", "banner", "bbs"]):
                        continue

                    full_url = href if href.startswith("http") else target_url.rstrip('/') + '/' + href.lstrip('/')
                    
                    matched_cat, matched_kw = classify_article_by_rules(title)
                    if matched_cat:
                        score = calculate_relevance_score(title, "", matched_cat)
                        results.append({
                            "선택": False,
                            "연관도점수": score,
                            "카테고리": matched_cat,
                            "매체명": media_name,
                            "검색키워드": matched_kw,
                            "기사제목": title,
                            "기사링크": full_url,
                            "게재일": datetime.now().strftime('%m/%d'),
                            "pub_dt": datetime.now()
                        })
        except Exception:
            pass
    return results

# =========================================================
# 🚀 전문지 74개 통합 수집 엔진
# =========================================================
@st.cache_data(ttl=1800)
def fetch_all_trade_news():
    all_raw = []
    time_limit = datetime.now() - timedelta(hours=36)
    
    for kw in SEARCH_KEYWORDS[:10]:
        all_raw.extend(fetch_track_a_news(kw, time_limit))
        
    for kw in SEARCH_KEYWORDS[:6]:
        all_raw.extend(fetch_track_b_news(kw, time_limit))
        
    all_raw.extend(fetch_track_c_news(time_limit))

    df = pd.DataFrame(all_raw)
    if df.empty:
        return df

    df = df.drop_duplicates(subset=["기사제목"], keep="first")

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
    st.session_state["news_df"] = fetch_all_trade_news()

col_title, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 실시간 전문지 뉴스 새로고침"):
        st.cache_data.clear()
        st.session_state["news_df"] = fetch_all_trade_news()
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

st.write(f"⚡ 74개 전문지 타깃 수집 완료: 최신 기사 **{len(raw_df)}건** | 🧠 AI 학습 데이터 축적: **{history_count}건**")

if not raw_df.empty:
    if st.button("🎯 중요 기사 자동 선별하기 (대표 기사만 선택)", type="primary"):
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
        st.success("대표 기사 자동 선별 완료!")

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

                st.success("🎉 뉴스레터 생성이 완료되었습니다!")
                st.info(f"📌 **메일 제목:** [Roche] Daily News Monitoring {title_date_str}")
                
                st.markdown("### 📧 이메일 뉴스레터 완제품")
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

with st.expander("🧠 AI 학습용 데이터 관리 센터", expanded=False):
    if os.path.exists(HISTORY_FILE) and not history_df.empty:
        st.write(f"현재 총 **{len(history_df)}건**의 선택 데이터가 저장되어 있습니다.")
        if st.button("🔥 학습 데이터 전체 초기화"):
            os.remove(HISTORY_FILE)
            st.success("모든 히스토리 데이터가 초기화되었습니다!")
            st.rerun()
    else:
        st.info("현재 축적된 AI 학습 데이터가 없습니다.")
