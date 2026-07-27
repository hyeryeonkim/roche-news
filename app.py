import streamlit as st
import pandas as pd
import requests
import feedparser
import re
import os
from datetime import datetime, timedelta
from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Roche News Monitoring System", layout="wide")
st.title("📰 한국로슈 3대 포털 뉴스 모니터링 (탭별 맞춤 스코어링 엔진)")

HISTORY_FILE = "selected_articles_history.csv"

NAVER_CLIENT_ID = "rdVf0JWe0wNFXCFrPKjI"
NAVER_CLIENT_SECRET = "cxR2cC5hmC"

CATEGORIES_LIST = ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]

# =========================================================
# 🎯 카테고리별 마스터 키워드 데이터베이스
# =========================================================

CORP_KEYWORDS = ["로슈", "Roche", "Genentech", "제넨텍", "제넨테크", "쥬가이", "Chugai", "한국로슈"]

PRODUCT_BRANDS = [
    "티쎈트릭", "Tecentriq", "맙테라", "Mabthera", "알레센자", "Alecensa", "셀셉트", "Cellcept", 
    "아바스틴", "Avastin", "타미플루", "Tamiflu", "조플루자", "Xofluza", "타쎄바", "Tarceva", 
    "허셉틴", "Herceptin", "마도파", "Madopar", "퍼제타", "Perjeta", "캐싸일라", "Kadcyla", 
    "가싸이바", "Gazyva", "폴라이비", "Polivy", "엔스프링", "Enspryng", "에브리스디", "Evrysdi", 
    "로즐리트렉", "Rozlytrek", "바비스모", "Vabysmo", "서스비모", "Susvimo", "페스코", "Phesgo", 
    "룬수미오", "Lunsumio", "오크레부스", "Ocrevus", "컬럼비", "Columvi", "엘레비디스", "Elevidys", 
    "이토베비", "Itovebi", "피아스카이", "Piasky"
]

PRODUCT_INGREDIENTS = [
    "아테졸리주맙", "리툭시맙", "알렉티닙", "미코페놀레이트모페틸", "마이코페놀레이트", "베바시주맙", 
    "발록사비르마르복실", "트라스투주맙", "퍼투주맙", "트라스투주맙 엠탄신", "오비누투주맙", "폴라투주맙", 
    "사트랄리주맙", "리스디플람", "파리시맙", "라니비주맙", "모수네투주맙", "오크렐리주맙", "글로피타맙", 
    "이나볼리십", "크로발리맙", "트론티네맙"
]

PRODUCT_COMBO_FORM = [
    "암질환심의위원회", "암질심", "중증질환", "면역항암제", "바이오의약품", "항체의약품", 
    "이중항체", "세포치료제", "생물의약품", "바이오시밀러"
]
PRODUCT_COMBO_TARGETS = [
    "로슈", "티쎈트릭", "허셉틴", "페스코", "캐싸일라", "퍼제타", "알레센자", 
    "바비스모", "에브리스디", "엔스프링", "오크레부스", "폴라이비", "컬럼비", "룬수미오"
]

COMPETITOR_BRANDS = [
    "키트루다", "옵디보", "임핀지", "이뮤도", "엔허투", "아일리아", "루센티스", "비오뷰", "아필리부", 
    "아이델젠트", "스핀라자", "졸겐스마", "울토미리스", "업리즈나", "킴리아", "예스카타", "넥사바", 
    "렌비마", "알룬브릭", "로비큐아", "림카토", "민쥬비", "엡킨리", "앱킨리", "티사브리", "렘트라다", 
    "티루캡", "피크레이", "CAR-T"
]

COMPETITOR_INGREDIENTS = [
    "펨브롤리주맙", "니볼루맙", "더발루맙", "트레멜리무맙", "트라스투주맙데룩스테칸", "애플리버셉트", 
    "라니비주맙", "브롤루시주맙", "뉴시너센", "오나셈노진 아베파르보벡", "라불리주맙", "이네빌리주맙", 
    "티사젠렉류셀", "악시캅타젠 시콜류셀", "소라페닙", "렌바티닙", "브리가티닙", "롤라티닙", 
    "리툭시맙", "타파시타맙", "엡코리타맙", "나탈리주맙", "알렘투주맙", "카피바세르팁", "알펠리십"
]

RARE_DISEASES = [
    "척수성근위축증", "SMA", "시신경척수염", "NMOSD", "시신경척수염범주질환", "황반변성", 
    "황반부종", "당뇨병성망막병증", "당뇨병성황반부종", "DLBCL", "소포성림프종", "DMD", 
    "뒤센근이영양증", "듀센근이영양증", "다발성경화증"
]

COMMON_DISEASES = ["유방암", "간암", "간세포암", "비소세포폐암", "혈액암", "조기암", "파킨슨", "인플루엔자"]
COMMON_DISEASE_TAILS = [
    "연구", "연구결과", "임상", "허가", "급여", "약평위", "암질심", "치료제", "신약", "학회", 
    "인터뷰", "대표", "사장", "전략", "출시", "포부", "시장", "환자", "투여", "제약", "바이오"
]

COMPETITOR_COMBO_TARGETS = [
    "키트루다", "옵디보", "임핀지", "엔허투", "스핀라자", "아일리아", "킴리아", "졸겐스마", 
    "유방암", "간암", "폐암", "혈액암", "SMA", "NMOSD", "DMD"
]

SOCIETIES = ["대한종양내과학회", "유방암학회", "신경과학회", "신경면역학회", "안과학회", "망막학회", "대한감염학회"]

POLICY_SINGLE_KEYWORDS = [
    "약평위", "암질심", "중증질환심의위원회", "심평원", "건보공단", "복지부", "식약처", "보건복지위", 
    "국정감사", "국감", "KRPIA", "한국글로벌의약산업협회", "KOBIA", "약가협상", "약가인하", "약가제도", 
    "경평면제", "위험분담제", "RSA", "경제성평가", "급여재평가", "고가의약품", "초고가신약", "사전심의", 
    "사용량-약가연동", "RWD", "RWE", "혁신신약", "혁신형제약기업", "정밀의료", "정밀의학", "맞춤의학", 
    "디지털헬스케어", "보건의료데이터", "신의료기술", "건보재정", "건강보험정책", "분산형임상", "DCT", 
    "GIFT", "허평협", "허가평가협상"
]

GLOBAL_MNA_A = ["다국적", "글로벌", "외자사"]
GLOBAL_MNA_B = ["제약사", "제약업계", "제약기업"]
GLOBAL_MNA_C = ["인사", "동정", "수상", "CSR", "사회공헌", "인수", "합병", "리베이트"]

PATIENT_GROUPS = ["환자단체총연합회", "백혈병환우회", "희귀난치성질환연합회", "환우회", "환자단체"]
PATIENT_TAILS = ["항암제", "치료제", "탄원", "정책", "암", "희귀질환", "신약", "급여"]

NEGATIVE_KEYWORDS = [
    "집값", "아파트", "부동산", "규제지역", "분양", "주택", "청약", "전세", 
    "증시", "주가", "코스피", "코스닥", "상한가", "특징주", "목표가", "치과", "한의원", "결혼"
]

SEARCH_KEYWORDS = list(set(
    ["로슈", "Roche", "한국로슈", "티쎈트릭", "바비스모", "에브리스디", "엔스프링", "허셉틴", "퍼제타", "페스코", "폴라이비", "컬럼비", "룬수미오", "오크레부스"] + 
    ["키트루다", "옵디보", "임핀지", "엔허투", "스핀라자", "아일리아", "졸겐스마", "킴리아"] + 
    ["척수성근위축증", "시신경척수염", "황반변성", "유방암", "간암", "비소세포폐암"] + 
    ["약평위", "암질심", "위험분담제", "사용량약가연동", "급여재평가", "KRPIA"]
))

# ---------------------------------------------------------
# 🌐 매체 등급 분류 및 한글 매체명 1:1 완벽 매핑
# ---------------------------------------------------------
TRADE_MEDIA_MAP = {
    "dailypharm.com": "데일리팜", "docdocdoc.co.kr": "청년의사", "dailymedi.com": "데일리메디",
    "medicaltimes.com": "메디칼타임즈", "monews.co.kr": "메디칼업저버", "medipana.com": "medipana",
    "pharmnews.com": "팜뉴스", "newsmp.com": "의약뉴스", "doctorsnews.co.kr": "의협신문",
    "bosa.co.kr": "의학신문", "koreabiomed.com": "KBR", "koreahealthlog.com": "코리아헬스로그",
    "hitnews.co.kr": "히트뉴스", "medigate.net": "메디게이트뉴스", "medisobizanews.com": "메디소비자뉴스",
    "kormedi.com": "코메디닷컴", "mediphasstoday.com": "메디팜스투데이", "kpanews.co.kr": "약사공론",
    "e-mednews.com": "e-의료정보", "medicaltribune.co.kr": "메디칼트리뷴", "rapportian.com": "라포르시안",
    "hns.or.kr": "후생신보", "yakup.com": "약업신문", "thebio.co.kr": "더바이오",
    "biospectator.com": "바이오스펙테이터", "medipana.com": "메디파나뉴스", "medworld.co.kr": "메디컬월드뉴스",
    "bokjiro.go.kr": "보건신문", "mdtoday.co.kr": "메디컬투데이", "medico.co.kr": "메디코파마"
}

GENERAL_MEDIA_MAP = {
    "yna.co.kr": "연합뉴스", "news1.kr": "뉴스1", "newsis.com": "뉴시스",
    "chosun.com": "조선일보", "joongang.co.kr": "중앙일보", "donga.com": "동아일보",
    "hankookilbo.com": "한국일보", "khan.co.kr": "경향신문", "seoul.co.kr": "서울신문",
    "segye.com": "세계일보", "munhwa.com": "문화일보", "hani.co.kr": "한겨레",
    "mk.co.kr": "매일경제", "hankyung.com": "한국경제", "fnnews.com": "파이낸셜뉴스",
    "sedaily.co.kr": "서울경제", "mt.co.kr": "머니투데이", "edaily.co.kr": "이데일리",
    "asiae.co.kr": "아시아경제", "heraldcorp.com": "헤럴드경제", "etnews.com": "전자신문",
    "dt.co.kr": "디지털타임스", "kbs.co.kr": "KBS", "imbc.com": "MBC", "sbs.co.kr": "SBS",
    "ytn.co.kr": "YTN", "jtbc.co.kr": "JTBC", "mbn.co.kr": "MBN", "channela.com": "채널A"
}

def identify_media_info(link, original_link=""):
    target_link = original_link if original_link else link
    domain = urlparse(target_link).netloc.lower()
    
    # 1. Tier 1 주요 제약 전문지 체크
    for d, name in TRADE_MEDIA_MAP.items():
        if d in domain:
            return name, "Tier1_Trade"
            
    # 2. Tier 2 주요 일간지/경제지/통신사 체크
    for d, name in GENERAL_MEDIA_MAP.items():
        if d in domain:
            return name, "Tier2_General"
            
    # 3. 기타 인터넷 언론 국문 변환
    cleaned = domain.replace("www.", "").replace("m.", "").replace("news.", "").split(".")[0].capitalize()
    return cleaned if cleaned else "뉴스", "Tier3_Others"

def calculate_jaccard_similarity(str1, str2):
    set1 = set(re.findall(r'\w+', str1.lower()))
    set2 = set(re.findall(r'\w+', str2.lower()))
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)

# 💡 카테고리 엄격 분류
def classify_article_strictly(text):
    text_lower = text.lower()

    for p in PRODUCT_BRANDS + PRODUCT_INGREDIENTS:
        if p.lower() in text_lower:
            return "Product News", p

    if any(f.lower() in text_lower for f in PRODUCT_COMBO_FORM) and any(t.lower() in text_lower for t in PRODUCT_COMBO_TARGETS):
        return "Product News", "(자사 심의/제형 이슈)"

    for c in CORP_KEYWORDS:
        if c.lower() in text_lower:
            return "Corporate News", c

    for pk in POLICY_SINGLE_KEYWORDS:
        if pk.lower() in text_lower:
            return "Industry/ Policy News", pk

    if any(a in text_lower for a in GLOBAL_MNA_A) and any(b in text_lower for b in GLOBAL_MNA_B) and any(c in text_lower for c in GLOBAL_MNA_C):
        return "Industry/ Policy News", "(글로벌 M&A/동향)"

    if any(pg in text_lower for pg in PATIENT_GROUPS) and any(pt in text_lower for pt in PATIENT_TAILS):
        return "Industry/ Policy News", "(환자단체/탄원)"

    for cb in COMPETITOR_BRANDS + COMPETITOR_INGREDIENTS:
        if cb.lower() in text_lower:
            return "Disease/ Market News", cb

    for rd in RARE_DISEASES:
        if rd.lower() in text_lower:
            return "Disease/ Market News", rd

    if any(cd in text_lower for cd in COMMON_DISEASES) and any(cdt in text_lower for cdt in COMMON_DISEASE_TAILS):
        return "Disease/ Market News", "(일반질환/동향)"

    if "비소세포폐암" in text_lower and any(k in text_lower for k in ["면역항암제", "alk", "임상", "급여"]):
        return "Disease/ Market News", "(폐암 서브타입)"

    if "유방암" in text_lower and any(k in text_lower for k in ["her2", "조기유방암", "임상", "급여"]):
        return "Disease/ Market News", "(유방암 서브타입)"

    if any(f.lower() in text_lower for f in PRODUCT_COMBO_FORM) and any(ct.lower() in text_lower for ct in COMPETITOR_COMBO_TARGETS):
        return "Disease/ Market News", "(경쟁사/질환 심의)"

    if any(s in text_lower for s in SOCIETIES):
        return "Disease/ Market News", "(학회 소식)"

    return None, None

# 🎯 [핵심] 카테고리별 맞춤형 스코어링 시스템
def calculate_custom_score(category, title, summary, media_tier, pub_dt):
    score = 0.0
    full_text = f"{title} {summary}"
    title_lower = title.lower()
    text_lower = full_text.lower()

    # 1. Corporate News 스코어링
    if category == "Corporate News":
        if any(c.lower() in title_lower for c in CORP_KEYWORDS):
            score += 5.0
        else:
            score += 3.0
            
        # 단순 나열 감점
        if sum(text_lower.count(c.lower()) for c in CORP_KEYWORDS) <= 1 and any(comp.lower() in text_lower for comp in COMPETITOR_BRANDS[:5]):
            score -= 2.0

    # 2. Product News 스코어링
    elif category == "Product News":
        if any(b.lower() in title_lower for b in PRODUCT_BRANDS):
            score += 5.0
        elif any(i.lower() in title_lower for i in PRODUCT_INGREDIENTS):
            score += 3.0
        else:
            score += 2.0
            
        # 매체 가점
        if media_tier == "Tier1_Trade":
            score += 2.0
        elif media_tier == "Tier2_General":
            score += 1.0

        # 단순 나열 감점
        total_mentions = sum(text_lower.count(b.lower()) for b in PRODUCT_BRANDS + PRODUCT_INGREDIENTS)
        if total_mentions <= 1:
            score -= 1.5

    # 3. Disease / Market News 스코어링
    elif category == "Disease/ Market News":
        # 경쟁사 인터뷰/전략 가점
        if any(k in text_lower for k in ["인터뷰", "대표", "사장", "전략", "출시", "포부", "비전", "시장"]):
            score += 4.0
            
        # 학회/임상데이터 발표 가점
        if any(k in text_lower for k in ["asco", "esmo", "임상3상", "fda", "ema", "os", "pfs", "데이터 발표", "학술대회"]):
            score += 3.0
            
        if any(cb.lower() in title_lower for cb in COMPETITOR_BRANDS) or any(rd.lower() in title_lower for rd in RARE_DISEASES):
            score += 2.0
            
        if media_tier == "Tier1_Trade":
            score += 1.5

        # 일반 건강상식 감점
        if any(neg in text_lower for neg in ["예방법", "원인", "증상", "자가진단", "음식", "생활습관"]):
            score -= 2.0

    # 4. Industry / Policy News 스코어링
    elif category == "Industry/ Policy News":
        # 1급 핵심 심의/급여 통과 가점
        if any(k in text_lower for k in ["암질심", "암질환심의위원회", "약평위", "약제급여평가위원회", "건정심", "급여 통과", "급여 상정", "약가협상 타결"]):
            score += 5.0
        # 2급 주요 정책 개편 가점
        elif any(k in text_lower for k in ["위험분담제", "rsa", "급여재평가", "사용량-약가연동", "경평면제", "복지부", "심평원", "식약처"]):
            score += 3.0
        else:
            score += 1.5

        if media_tier == "Tier1_Trade":
            score += 1.5

    # 최신 게재 시간 미세 소수점 가점 (동점 줄세우기 방지)
    hours_ago = (datetime.now() - pub_dt).total_seconds() / 3600
    recency_bonus = round(max(0, (36 - hours_ago) / 100), 3)
    score += recency_bonus

    return round(score, 2)

def fetch_naver_news(keyword, time_limit):
    results = []
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    enc_kw = quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news.json?query={enc_kw}&display=100&sort=date"
    
    try:
        res = requests.get(url, headers=headers, timeout=3)
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

                if pub_dt < time_limit:
                    continue

                full_text = f"{title} {summary}"
                if any(neg in full_text for neg in NEGATIVE_KEYWORDS):
                    continue

                media_name, media_tier = identify_media_info(link, origin_link)
                matched_cat, matched_kw = classify_article_strictly(full_text)
                
                if matched_cat:
                    score = calculate_custom_score(matched_cat, title, summary, media_tier, pub_dt)
                    results.append({
                        "선택": False,
                        "연관도점수": score,
                        "카테고리": matched_cat,
                        "출처포털": "네이버",
                        "매체명": media_name,
                        "검색키워드": matched_kw,
                        "기사제목": title,
                        "기사링크": origin_link if origin_link else link,
                        "게재일": pub_dt.strftime('%m/%d %H:%M'),
                        "pub_dt": pub_dt
                    })
    except Exception:
        pass
    return results

def fetch_daum_news(keyword, time_limit):
    results = []
    enc_kw = quote(keyword)
    rss_url = f"https://news.daum.net/api/service/rss/search/all.xml?q={enc_kw}"
    
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:10]:
            title = entry.get("title", "")
            link = entry.get("link", "")
            summary = entry.get("summary", "")

            pub_dt = datetime.now()
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                from time import mktime
                pub_dt = datetime.fromtimestamp(mktime(entry.published_parsed))

            if pub_dt < time_limit:
                continue

            full_text = f"{title} {summary}"
            if any(neg in full_text for neg in NEGATIVE_KEYWORDS):
                continue

            media_name, media_tier = identify_media_info(link)
            matched_cat, matched_kw = classify_article_strictly(full_text)
            
            if matched_cat:
                score = calculate_custom_score(matched_cat, title, summary, media_tier, pub_dt)
                results.append({
                    "선택": False,
                    "연관도점수": score,
                    "카테고리": matched_cat,
                    "출처포털": "다음",
                    "매체명": media_name,
                    "검색키워드": matched_kw,
                    "기사제목": title,
                    "기사링크": link,
                    "게재일": pub_dt.strftime('%m/%d %H:%M'),
                    "pub_dt": pub_dt
                })
    except Exception:
        pass
    return results

def fetch_google_news(keyword, time_limit):
    results = []
    enc_kw = quote(keyword)
    rss_url = f"https://news.google.com/rss/search?q={enc_kw}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:8]:
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

            media_name, media_tier = identify_media_info(link)
            matched_cat, matched_kw = classify_article_strictly(full_text)
            
            if matched_cat:
                score = calculate_custom_score(matched_cat, title, summary, media_tier, pub_dt)
                results.append({
                    "선택": False,
                    "연관도점수": score,
                    "카테고리": matched_cat,
                    "출처포털": "구글",
                    "매체명": media_name,
                    "검색키워드": matched_kw,
                    "기사제목": title,
                    "기사링크": link,
                    "게재일": pub_dt.strftime('%m/%d %H:%M'),
                    "pub_dt": pub_dt
                })
    except Exception:
        pass
    return results

@st.cache_data(ttl=1800)
def fetch_all_integrated_news():
    all_raw = []
    time_limit = datetime.now() - timedelta(hours=36)
    
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = []
        for kw in SEARCH_KEYWORDS:
            futures.append(executor.submit(fetch_naver_news, kw, time_limit))
            
        for kw in SEARCH_KEYWORDS[:10]:
            futures.append(executor.submit(fetch_daum_news, kw, time_limit))

        for kw in SEARCH_KEYWORDS[:10]:
            futures.append(executor.submit(fetch_google_news, kw, time_limit))

        for future in as_completed(futures):
            try:
                res = future.result()
                if res:
                    all_raw.extend(res)
            except Exception:
                pass

    df = pd.DataFrame(all_raw)
    if df.empty:
        return df

    # 네이버 우선 및 제목 중복 제거
    df = df.sort_values(by=["출처포털", "연관도점수", "pub_dt"], ascending=[False, False, False])
    df = df.drop_duplicates(subset=["기사제목"], keep="first")

    # 유사 보도자료 축약
    cleaned_rows = []
    titles_seen = []
    
    for idx, row in df.iterrows():
        title = row["기사제목"]
        is_sim_dup = False
        for t in titles_seen:
            if calculate_jaccard_similarity(title, t) >= 0.38:
                is_sim_dup = True
                break
        if not is_sim_dup:
            cleaned_rows.append(row)
            titles_seen.append(title)
            
    df_cleaned = pd.DataFrame(cleaned_rows)

    # 🎯 탭별 연관도점수 내림차순 정렬
    df_cleaned = df_cleaned.sort_values(by=["연관도점수", "pub_dt"], ascending=[False, False]).drop(columns=["pub_dt"])
    return df_cleaned

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
    if st.button("🔄 실시간 3대 포털 뉴스 새로고침"):
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

st.write(f"⚡ 최근 36시간 포털(네이버/다음/구글) 통합 고속 수집: 최신 기사 **{len(raw_df)}건** | 🧠 AI 학습 데이터 축적: **{history_count}건**")

if not raw_df.empty:
    if st.button("🎯 중요 기사 자동 선별하기 (카테고리별 상위 5건 체크)", type="primary"):
        auto_df = raw_df.copy()
        for cat in CATEGORIES_LIST:
            cat_df = auto_df[auto_df["카테고리"] == cat].sort_values(by="연관도점수", ascending=False)
            selected_indices = cat_df.index[:5]
            auto_df.loc[selected_indices, "선택"] = True
            
        st.session_state["analyzed_df"] = auto_df
        st.success("카테고리별 중요도 상위 기사 자동 체크 완료!")

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
                        "연관도점수": st.column_config.NumberColumn("중요도 🎯", format="%.2f"),
                        "카테고리": st.column_config.SelectboxColumn(
                            "카테고리 🔄",
                            options=CATEGORIES_LIST,
                            required=True
                        ),
                        "출처포털": st.column_config.TextColumn("출처 🌐"),
                        "기사링크": st.column_config.LinkColumn("기사링크")
                    },
                    disabled=["연관도점수", "출처포털", "매체명", "검색키워드", "기사제목", "기사링크", "게재일"],
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

                st.success("🎉 선택하신 모든 기사로 뉴스레터 생성이 완료되었습니다!")
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
