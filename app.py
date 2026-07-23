import os
import re
from datetime import datetime, timedelta
from time import mktime
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

import feedparser
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Roche Daily News Monitoring", layout="wide")
st.title("📰 한국로슈 Daily News Monitoring Dashboard")

# 히스토리 저장 파일 경로
HISTORY_FILE = "selected_articles_history.csv"

# 1. 수집 매체 전체 통합 리스트
ALL_MEDIA_LIST = [
    # General / Economy
    {"media": "연합뉴스", "type": "General", "tier": "1 Tier", "rss": "https://www.yna.co.kr/rss/news.xml"},
    {"media": "뉴시스", "type": "General", "tier": "1 Tier", "rss": "https://www.newsis.com/RSS/sitemap.xml"},
    {"media": "뉴스1", "type": "General", "tier": "1 Tier", "rss": "https://www.news1.kr/rss/all.xml"},
    {"media": "조선일보", "type": "General", "tier": "1 Tier", "rss": "https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml"},
    {"media": "중앙일보", "type": "General", "tier": "1 Tier", "rss": "https://rss.joongang.co.kr/son/joongang_all.xml"},
    {"media": "동아일보", "type": "General", "tier": "1 Tier", "rss": "https://rss.donga.com/total.xml"},
    {"media": "매일경제", "type": "General", "tier": "1 Tier", "rss": "https://www.mk.co.kr/rss/30000001/"},
    {"media": "한국경제", "type": "General", "tier": "1 Tier", "rss": "https://www.hankyung.com/feed/all-news"},
    {"media": "조선비즈", "type": "General", "tier": "2 Tier", "rss": "https://biz.chosun.com/rss/all.xml"},
    {"media": "IT조선", "type": "General", "tier": "2 Tier", "rss": "https://it.chosun.com/rss/all.xml"},
    {"media": "코리아중앙데일리", "type": "General", "tier": "2 Tier", "rss": "https://koreajoongangdaily.joins.com/rss/all.xml"},
    {"media": "동아닷컴", "type": "General", "tier": "2 Tier", "rss": "https://rss.donga.com/total.xml"},
    {"media": "한국일보", "type": "General", "tier": "2 Tier", "rss": "https://hankookilbo.com/baidu/rss/all"},
    {"media": "데일리한국", "type": "General", "tier": "2 Tier", "rss": "https://daily.hankooki.com/rss/allArticle.xml"},
    {"media": "세계일보", "type": "General", "tier": "2 Tier", "rss": "https://www.segye.com/Articles/RSS/rss_all.xml"},
    {"media": "문화일보", "type": "General", "tier": "2 Tier", "rss": "https://www.munhwa.com/news/rss.xml"},
    {"media": "국민일보", "type": "General", "tier": "2 Tier", "rss": "https://rss.kmib.co.kr/data/kmibRssAll.xml"},
    {"media": "쿠키뉴스", "type": "General", "tier": "2 Tier", "rss": "https://www.kukinews.com/rss/allArticle.xml"},
    {"media": "한겨레", "type": "General", "tier": "2 Tier", "rss": "https://www.hani.co.kr/rss/"},
    {"media": "서울신문", "type": "General", "tier": "2 Tier", "rss": "https://www.seoul.co.kr/rss/rssData/total_news.xml"},
    {"media": "내일신문", "type": "General", "tier": "2 Tier", "rss": "http://www.naeil.com/news/rss/all.xml"},
    {"media": "매일일보", "type": "General", "tier": "2 Tier", "rss": "https://www.m-i.kr/rss/allArticle.xml"},
    {"media": "아시아투데이", "type": "General", "tier": "2 Tier", "rss": "https://www.asiatoday.co.kr/rss/all.xml"},
    {"media": "MBN", "type": "General", "tier": "2 Tier", "rss": "https://www.mbn.co.kr/rss/all.xml"},
    {"media": "한국경제TV", "type": "General", "tier": "2 Tier", "rss": "https://www.wowtv.co.kr/rss/all.xml"},
    {"media": "파이낸셜뉴스", "type": "General", "tier": "2 Tier", "rss": "https://www.fnnews.com/rss/fn_realtime_all.xml"},
    {"media": "서울경제", "type": "General", "tier": "2 Tier", "rss": "https://www.sedaily.co.kr/RSS/NewsAll"},
    {"media": "서울경제TV", "type": "General", "tier": "2 Tier", "rss": "https://www.sentv.co.kr/rss/all.xml"},
    {"media": "헤럴드경제", "type": "General", "tier": "2 Tier", "rss": "https://biz.heraldcorp.com/common/rss.php"},
    {"media": "머니투데이", "type": "General", "tier": "2 Tier", "rss": "https://rss.mt.co.kr/mt_news_all.xml"},
    {"media": "아시아경제", "type": "General", "tier": "2 Tier", "rss": "https://www.asiae.co.kr/rss/all.xml"},
    {"media": "이데일리", "type": "General", "tier": "2 Tier", "rss": "https://rss.edaily.co.kr/e-health_news.xml"},
    {"media": "이투데이", "type": "General", "tier": "2 Tier", "rss": "https://www.etoday.co.kr/rss/all.xml"},
    {"media": "디지털타임스", "type": "General", "tier": "2 Tier", "rss": "https://www.dt.co.kr/rss/all.xml"},
    {"media": "전자신문", "type": "General", "tier": "2 Tier", "rss": "https://www.etnews.com/etnews_rss.xml"},
    {"media": "지디넷코리아", "type": "General", "tier": "2 Tier", "rss": "https://zdnet.co.kr/rss/all.xml"},
    {"media": "더벨", "type": "General", "tier": "2 Tier", "rss": "https://www.thebell.co.kr/free/rss/rss.xml"},
    {"media": "비즈월드", "type": "General", "tier": "2 Tier", "rss": "https://www.bizwnews.com/rss/allArticle.xml"},
    {"media": "브릿지경제", "type": "General", "tier": "2 Tier", "rss": "https://www.viva100.com/rss/all.xml"},
    {"media": "시사위크", "type": "General", "tier": "2 Tier", "rss": "https://www.sisaweek.com/rss/allArticle.xml"},
    {"media": "세계비즈", "type": "General", "tier": "2 Tier", "rss": "https://www.segyebiz.com/rss/all.xml"},
    {"media": "스포츠조선", "type": "General", "tier": "2 Tier", "rss": "https://sports.chosun.com/rss/all.xml"},
    {"media": "스포츠비즈", "type": "General", "tier": "2 Tier", "rss": "https://www.sporbiz.co.kr/rss/allArticle.xml"},
    {"media": "메트로서울", "type": "General", "tier": "2 Tier", "rss": "https://www.metroseoul.co.kr/rss/all.xml"},
    {"media": "프라임경제", "type": "General", "tier": "2 Tier", "rss": "https://www.newsprime.co.kr/rss/allArticle.xml"},
    {"media": "뉴스핌", "type": "General", "tier": "2 Tier", "rss": "https://www.newspim.com/rss/all.xml"},
    {"media": "이코노믹데일리", "type": "General", "tier": "2 Tier", "rss": "https://www.economidaily.com/rss/all.xml"},
    {"media": "이뉴스투데이", "type": "General", "tier": "2 Tier", "rss": "https://www.enewstoday.co.kr/rss/allArticle.xml"},
    {"media": "뉴데일리", "type": "General", "tier": "2 Tier", "rss": "https://www.newdaily.co.kr/rss/all.xml"},
    {"media": "뉴스투데이", "type": "General", "tier": "2 Tier", "rss": "https://www.news2day.co.kr/rss/allArticle.xml"},
    {"media": "서울와이어", "type": "General", "tier": "2 Tier", "rss": "https://www.seoulwire.com/rss/allArticle.xml"},
    {"media": "톱데일리", "type": "General", "tier": "2 Tier", "rss": "https://www.topdaily.kr/rss/allArticle.xml"},
    {"media": "KPI뉴스", "type": "General", "tier": "2 Tier", "rss": "https://www.kpinews.kr/rss/allArticle.xml"},
    {"media": "시사저널EBN", "type": "General", "tier": "2 Tier", "rss": "https://www.sisajournal-e.com/rss/allArticle.xml"},
    {"media": "신아일보", "type": "General", "tier": "2 Tier", "rss": "https://www.shinailbo.co.kr/rss/allArticle.xml"},
    {"media": "베타뉴스", "type": "General", "tier": "2 Tier", "rss": "https://www.betanews.net/rss/all.xml"},
    {"media": "위키리크스", "type": "General", "tier": "2 Tier", "rss": "https://www.wikileaks-kr.org/rss/allArticle.xml"},
    {"media": "한국팍스경제TV", "type": "General", "tier": "2 Tier", "rss": "https://www.paxetv.com/rss/allArticle.xml"},
    {"media": "뉴스저널리즘", "type": "General", "tier": "2 Tier", "rss": "https://www.ngetnews.com/rss/allArticle.xml"},
    {"media": "오피니언뉴스", "type": "General", "tier": "2 Tier", "rss": "https://www.opinionnews.co.kr/rss/allArticle.xml"},
    {"media": "포춘코리아", "type": "General", "tier": "2 Tier", "rss": "https://www.fortunekorea.co.kr/rss/allArticle.xml"},
    {"media": "로이슈", "type": "General", "tier": "2 Tier", "rss": "https://www.lawissue.co.kr/rss/allArticle.xml"},
    {"media": "한국면세뉴스", "type": "General", "tier": "2 Tier", "rss": "https://www.kdfnews.com/rss/allArticle.xml"},
    {"media": "블로터", "type": "General", "tier": "2 Tier", "rss": "https://www.bloter.net/rss/allArticle.xml"},
    {"media": "뉴스인스페이스", "type": "General", "tier": "2 Tier", "rss": "https://www.space.or.kr/rss/allArticle.xml"},
    {"media": "청년일보", "type": "General", "tier": "2 Tier", "rss": "https://www.youthdaily.co.kr/rss/allArticle.xml"},
    {"media": "스카이데일리", "type": "General", "tier": "2 Tier", "rss": "https://www.skyedaily.com/rss/allArticle.xml"},
    {"media": "뉴스토마토", "type": "General", "tier": "2 Tier", "rss": "https://www.newstomato.com/rss/all.xml"},
    {"media": "뷰어스", "type": "General", "tier": "2 Tier", "rss": "https://theviewers.co.kr/rss/allArticle.xml"},
    {"media": "뉴스웨이", "type": "General", "tier": "2 Tier", "rss": "https://www.newsway.co.kr/rss/allArticle.xml"},

    # Pharma Specialty
    {"media": "청년의사", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.docdocdoc.co.kr/rss/allArticle.xml"},
    {"media": "데일리팜", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.dailypharm.com/Users/Rss/Rss.html"},
    {"media": "의학신문", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.bosa.co.kr/rss/allArticle.xml"},
    {"media": "뉴스더보이스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.newsthevoice.com/rss/allArticle.xml"},
    {"media": "히트뉴스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.hitnews.co.kr/rss/allArticle.xml"},
    {"media": "의약뉴스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.newsmp.com/rss/allArticle.xml"},
    {"media": "팜뉴스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.pharmnews.com/rss/allArticle.xml"},
    {"media": "메디칼타임즈", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.medicaltimes.com/Users/Rss/Rss.html"},
    {"media": "KBR", "type": "Specialty", "tier": "1 Tier", "rss": "http://www.koreabiomed.com/rss/allArticle.xml"},
    {"media": "코리아헬스로그", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.koreahealthlog.com/rss/allArticle.xml"},
    {"media": "데일리메디", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.dailymedi.com/rss/allArticle.xml"},
    {"media": "메디파나뉴스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.medipana.com/rss/allArticle.xml"},
    {"media": "메디칼업저버", "type": "Specialty", "tier": "1 Tier", "rss": "http://www.monews.co.kr/rss/allArticle.xml"},
    {"media": "헬스동아", "type": "Specialty", "tier": "1 Tier", "rss": "https://donga.com/news/rss/health"},
    {"media": "동아사이언스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.dongascience.com/rss/all.xml"},
    {"media": "헬스조선", "type": "Specialty", "tier": "1 Tier", "rss": "https://health.chosun.com/site/data/rss/rss.xml"},
    {"media": "매경헬스", "type": "Specialty", "tier": "1 Tier", "rss": "https://www.mkhealth.co.kr/rss/allArticle.xml"},
    {"media": "헬스중앙", "type": "Specialty", "tier": "1 Tier", "rss": "https://jhealthmedia.joins.com/rss/allArticle.xml"},
    {"media": "건강보험신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.khip.co.kr/rss/allArticle.xml"},
    {"media": "건강보험저널", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.khnews.co.kr/rss/allArticle.xml"},
    {"media": "닥터W", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.doctorw.co.kr/rss/allArticle.xml"},
    {"media": "라포르시안", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.rapportian.com/rss/allArticle.xml"},
    {"media": "메디팜스투데이", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.pharmstoday.com/rss/allArticle.xml"},
    {"media": "메디칼트리뷴", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.medicaltribune.co.kr/rss/allArticle.xml"},
    {"media": "메디컬헤럴드", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.medherald.co.kr/rss/allArticle.xml"},
    {"media": "메디포뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.medifonews.com/rss/allArticle.xml"},
    {"media": "메디게이트뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.medigatenews.com/rss/allArticle.xml"},
    {"media": "메디소비자뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.medisobizanews.com/rss/allArticle.xml"},
    {"media": "메디팜헬스뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.medipharmhealth.co.kr/rss/allArticle.xml"},
    {"media": "메디칼통신", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.mcommunication.co.kr/rss/allArticle.xml"},
    {"media": "메디컬월드뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://medicalworldnews.co.kr/rss/allArticle.xml"},
    {"media": "바이오스펙테이터", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.biospectator.com/rss/allArticle.xml"},
    {"media": "병원신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.khanews.com/rss/allArticle.xml"},
    {"media": "보건신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.bokjiro.go.kr/rss/allArticle.xml"},
    {"media": "보건타임즈", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.baag.co.kr/rss/allArticle.xml"},
    {"media": "사이언스엠디뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.sciencemd.com/rss/allArticle.xml"},
    {"media": "식약신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.fmnews.co.kr/rss/allArticle.xml"},
    {"media": "아이팜뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.ipharmnews.com/rss/allArticle.xml"},
    {"media": "약사공론", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.kpanews.co.kr/rss/allArticle.xml"},
    {"media": "약업신문", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.yakup.com/rss/"},
    {"media": "의약품유통신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.kda.or.kr/rss/allArticle.xml"},
    {"media": "의계신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.medworld.co.kr/rss/allArticle.xml"},
    {"media": "e-의료정보", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.egye.co.kr/rss/allArticle.xml"},
    {"media": "의사신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.doctorstimes.com/rss/allArticle.xml"},
    {"media": "의협신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.doctorsnews.co.kr/rss/allArticle.xml"},
    {"media": "엠디저널", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.mdjournal.kr/rss/allArticle.xml"},
    {"media": "의료일보", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.kmedinfo.co.kr/rss/allArticle.xml"},
    {"media": "이엠디", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.kmdnews.uk/rss/allArticle.xml"},
    {"media": "코메디닷컴", "type": "Specialty", "tier": "2 Tier", "rss": "https://kormedi.com/rss/allArticle.xml"},
    {"media": "헬스코리아뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.hkn24.com/rss/allArticle.xml"},
    {"media": "헬스포커스뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.healthfocus.co.kr/rss/allArticle.xml"},
    {"media": "현대건강신문", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.hhealth.co.kr/rss/allArticle.xml"},
    {"media": "후생신보", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.whosaeng.com/rss/allArticle.xml"},
    {"media": "클리닉저널", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.clinicjournal.co.kr/rss/allArticle.xml"},
    {"media": "헬스앤라이프", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.healthi.kr/rss/allArticle.xml"},
    {"media": "파마투데이", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.pharmatoday.co.kr/rss/allArticle.xml"},
    {"media": "헬스인뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.healthinnews.co.kr/rss/allArticle.xml"},
    {"media": "더바이오", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.thebio.co.kr/rss/allArticle.xml"},
    {"media": "파마타임스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.pharmatimes.co.kr/rss/allArticle.xml"},
    {"media": "메디컬투데이", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.mdtoday.co.kr/rss/allArticle.xml"},
    {"media": "메디코파마뉴스", "type": "Specialty", "tier": "2 Tier", "rss": "http://www.medicopharma.co.kr/rss/allArticle.xml"},
    {"media": "헬스경향", "type": "Specialty", "tier": "2 Tier", "rss": "https://www.k-health.com/rss/allArticle.xml"}
]

CATEGORIES_LIST = ["Corporate News", "Product News", "Disease/ Market News", "Industry/ Policy News"]

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
    "엔허투", "이뮤도", "임핀지", "림카토", "민쥬비", "척수성근위축증", "SMA", "신경근육질환", 
    "시신경척수염", "NMOSD", "시신경척수염범주질환", "황반변성", "황반부종", 
    "당뇨병성망막병증", "혈액암", "바이오의약품", "당뇨병성황반부종", "인플루엔자", "유방암", "간암", 
    "간세포암", "비소세포폐암", "파킨슨", "대한종양내과학회", "신경과학회", "신경면역학회", "안과학회", 
    "망막학회", "대한감염학회", "면역항암제", "항체의약품", "세포치료제", "생물의약품", "바이오시밀러", 
    "DMD", "뒤센근이영양증", "듀센근이영양증", "DLBCL", 
    "엡킨리", "다발성경화증", "티사브리", "렘트라다", "울토미리스", "Ultomiris", "라불리주맙", "Ravulizumab", 
    "업리즈나", "이네빌리주맙", "티루캡", "피크레이", "조기암", "조기유방암", "젊은유방암", "타그리소", "렉라자"
]

INDUSTRY_SINGLE_KEYWORDS = [
    "약평위", "암질심", "중증질환심의위원회", "심평원", "건보공단", "복지부", "식약처", "공정위", "보건복지위", "국정감사", "국감",
    "KRPIA", "한국글로벌의약산업협회", "KOBIA", "한국바이오의약품협회", "한국제약바이오협회",
    "약가협상", "약가인하", "약가제도", "경평면제", "위험분담제", "RSA", "경제성평가", "급여재평가",
    "고가의약품", "초고가신약", "사전심의", "사용량-약가연동", "RWD", "RWE", "희귀난치성질환", "희귀난치질환", "희귀질환",
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

def calculate_relevance_score(title, summary, category, tier="2 Tier"):
    full_text = f"{title} {summary}"
    score = 0

    if re.search(r"컬럼비아\s*대|컬럼비아대|컬럼비아\s*대학교|columbia\s*univ", full_text, re.I):
        score -= 8

    if any(neg in full_text for neg in ["음식", "레시피", "여름철", "10계명", "운동법", "자가진단"]):
        score -= 4

    score += 1

    if category == "Corporate News":
        if any(k in full_text for k in ["로슈", "Roche", "한국로슈"]):
            score += 3
        if re.search(r"실적|대표|인사|CSR|사회공헌|투자|협약", full_text):
            score += 2

    elif category == "Product News":
        if any(core in full_text for core in ["티쎈트릭", "아바스틴", "알레센자", "바비스모", "에브리스디", "엔스프링", "오크레부스", "폴라이비", "컬럼비", "룬수미오", "페스코", "캐싸일라", "퍼제타", "허셉틴", "이토베비"]):
            score += 3
        if any(evt in full_text for evt in ["급여", "임상", "3상", "허가", "FDA", "적응증", "약평위", "암질심"]):
            score += 2

    elif category == "Disease/ Market News":
        comp_drugs = ["키트루다", "엔허투", "타그리소", "렉라자", "아일리아", "스핀라자", "옵디보", "임핀지", "이뮤도", "알룬브릭", "로비큐아", "예스카타", "울토미리스", "업리즈나"]
        target_conditions = ["HER2", "HER2양성", "HER2+", "DLBCL", "소포성림프종", "ALK", "SMA", "척수성근위축증", "NMOSD", "시신경척수염", "황반변성", "비소세포폐암", "TNBC", "삼중음성"]
        major_events = ["급여", "임상", "3상", "허가", "FDA", "적응증", "약평위", "암질심"]
        
        has_comp = any(c in full_text for c in comp_drugs)
        has_target = any(re.search(tc, full_text, re.I) for tc in target_conditions)
        has_event = any(ev in full_text for ev in major_events)

        if has_comp and has_target and has_event:
            score += 4
        elif has_comp and (has_target or has_event):
            score += 2

        is_kol_research = re.search(r"(교수|연구팀|임상\s*발표|국제학회|게재|학술지|연구결과|발표회)", full_text)
        is_gov_stats = re.search(r"(질병청|질병관리청|통계|발병률\s*1위|주의보|가이드라인|치료지침|지침\s*개정)", full_text)

        if (is_kol_research or is_gov_stats) and has_target:
            score += 3
        elif is_kol_research or is_gov_stats:
            score += 1

    elif category == "Industry/ Policy News":
        if any(p in full_text for p in ["약가인하", "약가협상", "약가제도", "위험분담제", "RSA", "경평면제", "급여재평가", "사용량-약가연동"]):
            score += 3
        if any(gov in full_text for gov in ["보건복지위", "국정감사", "국감", "법안", "발의", "입법", "개정안"]):
            score += 2
        if any(org in full_text for org in ["식약처", "심평원", "건보공단", "복지부"]):
            score += 1

    if any(k in title for k in ["로슈", "Roche", "티쎈트릭", "바비스모", "에브리스디", "알레센자", "페스코", "이토베비", "키트루다", "타그리소", "렉라자", "약가", "급여", "국감"]):
        score += 1

    if re.search(r"폐암|비소세포폐암", full_text, re.I):
        if re.search(r"ALK|KRAS", full_text, re.I):
            if not re.search(r"(ALK|KRAS)\s*(음성|미검출|제외|없음)", full_text, re.I):
                score += 1
        if re.search(r"EGFR|ROS1|\bROS\b", full_text, re.I):
            score -= 1

    if tier == "1 Tier":
        score += 1

    return max(1, min(score, 10))

def parse_single_media(m, time_limit):
    sub_results = []
    try:
        response = requests.get(m["rss"], timeout=3, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code != 200:
            return sub_results
            
        feed = feedparser.parse(response.content)
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
                    "게재일": pub_date_str,
                    "pub_dt": pub_dt if pub_dt else datetime.now()
                })
    except Exception:
        pass
    return sub_results

def extract_keywords_set(text):
    """기사 제목에서 대괄호/특수문자 제거 후 2글자 이상 핵심 단어 집합 반환"""
    cleaned = re.sub(r"\[.*?\]|\(.*?\)|\<.*?\>", "", text)
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    words = [w.lower() for w in cleaned.split() if len(w) >= 2]
    return set(words), cleaned.strip().lower()

# 🎯 고도화된 유사도 기반 중복 기사 군집화 및 대표 1건 선정 함수
def cluster_and_mark_representatives(df, threshold=0.55):
    if df.empty:
        df["is_representative"] = False
        df["cluster_id"] = -1
        return df
    
    # 🎯 [핵심] 인덱스 재정렬 (인덱스 불일치 오류 완벽 처리)
    df = df.reset_index(drop=True)
    df["is_representative"] = False
    df["cluster_id"] = -1
    
    title_meta = [extract_keywords_set(str(t)) for t in df["기사제목"]]
    
    cluster_cnt = 0
    assigned = [False] * len(df)
    
    for i in range(len(df)):
        if assigned[i]:
            continue
        
        cluster_indices = [i]
        assigned[i] = True
        set_i, str_i = title_meta[i]
        
        for j in range(i + 1, len(df)):
            if assigned[j]:
                continue
            
            set_j, str_j = title_meta[j]
            
            # 1. 단어 집합 자카드 유사도 (Jaccard Similarity)
            intersection = len(set_i.intersection(set_j))
            union = len(set_i.union(set_j))
            jaccard_sim = intersection / union if union > 0 else 0
            
            # 2. 문자열 유사도 (SequenceMatcher)
            seq_sim = SequenceMatcher(None, str_i, str_j).ratio()
            
            # 단어 집합 유사도 50% 이상 or 문자열 유사도 threshold 이상 시 중복으로 인정
            if jaccard_sim >= 0.50 or seq_sim >= threshold:
                cluster_indices.append(j)
                assigned[j] = True
        
        df.loc[cluster_indices, "cluster_id"] = cluster_cnt
        
        # 대표 1건 차출 (1 Tier 매체 우선 -> 연관도 높은 순 -> 빠른 게재일)
        sub_df = df.loc[cluster_indices].copy()
        sub_df["tier_score"] = sub_df["Tier"].apply(lambda x: 1 if x == "1 Tier" else 2)
        best_idx = sub_df.sort_values(
            by=["tier_score", "연관도점수", "pub_dt"],
            ascending=[True, False, True]
        ).index[0]
        
        df.loc[best_idx, "is_representative"] = True
        cluster_cnt += 1
        
    return df

@st.cache_data(ttl=1800)
def fetch_recent_news():
    time_limit = datetime.now() - timedelta(hours=36)
    all_results = []

    with ThreadPoolExecutor(max_workers=60) as executor:
        futures = [executor.submit(parse_single_media, m, time_limit) for m in ALL_MEDIA_LIST]
        for future in futures:
            all_results.extend(future.result())
    
    empty_df = pd.DataFrame(columns=[
        "선택", "연관도점수", "카테고리", "매체명", "Tier", "검색키워드", 
        "기사제목", "기사링크", "게재일", "pub_dt", "is_representative", "cluster_id"
    ])
    
    if all_results:
        df_res = pd.DataFrame(all_results)
        df_res = df_res.sort_values(by=["연관도점수", "Tier"], ascending=[False, True]).drop_duplicates(subset=["기사제목"], keep="first")
        df_res = cluster_and_mark_representatives(df_res)
        return df_res
    else:
        return empty_df

def save_selected_history(selected_df):
    try:
        save_data = selected_df.copy()
        save_data["선택시각"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cols_to_drop = [c for c in ["pub_dt", "is_representative", "cluster_id", "대표여부"] if c in save_data.columns]
        if cols_to_drop:
            save_data = save_data.drop(columns=cols_to_drop)

        if os.path.exists(HISTORY_FILE):
            save_data.to_csv(HISTORY_FILE, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            save_data.to_csv(HISTORY_FILE, mode='w', header=True, index=False, encoding='utf-8-sig')
    except Exception:
        pass

if "news_df" not in st.session_state:
    st.session_state["news_df"] = fetch_recent_news()

col_title, col_btn = st.columns([4, 1])
with col_btn:
    if st.button("🔄 실시간 뉴스 새로고침"):
        st.cache_data.clear()
        st.session_state["news_df"] = fetch_recent_news()
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

st.write(f"⚡ 초고속 수집 완료: 최신 기사 **{len(raw_df)}건** | 🧠 AI 학습용 데이터 축적: **{history_count}건**")

if not raw_df.empty:
    if st.button("🎯 중요 기사 자동 선별하기 (대표 기사 Top 5 자동 체크)", type="primary"):
        auto_df = raw_df.copy()
        auto_df["선택"] = False
        
        if "is_representative" in auto_df.columns:
            for cat in CATEGORIES_LIST:
                cat_rep_indices = auto_df[
                    (auto_df["카테고리"] == cat) & (auto_df["is_representative"] == True)
                ].sort_values(by="연관도점수", ascending=False).head(5).index
                auto_df.loc[cat_rep_indices, "선택"] = True
        
        st.session_state["analyzed_df"] = auto_df
        st.success("대표 기사 위주 스마트 분석 완료!")

    display_df = st.session_state.get("analyzed_df", raw_df)
    tabs = st.tabs([f"📌 {cat}" for cat in CATEGORIES_LIST])
    
    all_edited_dfs = []
    
    for i, cat in enumerate(CATEGORIES_LIST):
        with tabs[i]:
            cat_df = display_df[display_df["카테고리"] == cat].copy()
            st.markdown(f"### {cat} ({len(cat_df)}건)")
            
            if not cat_df.empty:
                if "is_representative" in cat_df.columns:
                    cat_df["대표여부"] = cat_df["is_representative"].apply(lambda x: "⭐ 대표" if x else "🔗 유사중복")
                else:
                    cat_df["대표여부"] = "⭐ 대표"
                
                show_cols = ["선택", "대표여부", "연관도점수", "카테고리", "매체명", "Tier", "검색키워드", "기사제목", "기사링크", "게재일"]
                
                edited = st.data_editor(
                    cat_df[show_cols],
                    column_config={
                        "선택": st.column_config.CheckboxColumn("선택 ✅", default=False),
                        "대표여부": st.column_config.TextColumn("대표 구분 💡"),
                        "카테고리": st.column_config.SelectboxColumn(
                            "카테고리 🔄",
                            help="기사를 다른 카테고리로 변경하려면 클릭하여 선택하세요 (변경 후 Enter)",
                            options=CATEGORIES_LIST,
                            required=True
                        ),
                        "연관도점수": st.column_config.NumberColumn("연관도 🎯", help="10점 만점 기준"),
                        "기사링크": st.column_config.LinkColumn("기사링크")
                    },
                    disabled=["대표여부", "연관도점수", "매체명", "Tier", "검색키워드", "기사제목", "기사링크", "게재일"],
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

# 🧠 AI 학습 데이터 개별 / 전체 삭제 및 관리 센터
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
            disabled=["선택시각", "카테고리", "매체명", "기사제목", "기사링크", "Tier", "검색키워드", "연관도점수", "게재일"],
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
