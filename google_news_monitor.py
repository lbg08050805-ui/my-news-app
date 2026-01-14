# [FILE_PATH]: D:\pgm\google_news_monitor.py
# [EXECUTION_COMMAND]: streamlit run D:\pgm\google_news_monitor.py

import os
import sys

# 기본 경로 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# ------------------------------------------------------------------------------
# [기능 1] 시간 계산 및 포맷팅 (구글 RSS 시간 -> 한국 시간 변환)
# ------------------------------------------------------------------------------
def process_google_time(pubDate_str):
    try:
        dt = parsedate_to_datetime(pubDate_str)
        kst_dt = dt + timedelta(hours=9)
        display_str = kst_dt.strftime("%Y-%m-%d %H:%M")
        timestamp = kst_dt.timestamp()
        return display_str, timestamp
    except:
        now = datetime.now()
        return now.strftime("%Y-%m-%d %H:%M"), now.timestamp()

# ------------------------------------------------------------------------------
# [기능 2] 화면 디자인 (CSS)
# ------------------------------------------------------------------------------
st.set_page_config(page_title="뉴스 모니터", layout="wide")
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    .news-row { display: flex; align-items: center; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid #f0f0f0; padding-bottom: 8px; }
    .badge-google { 
        background-color: #4285F4; color: white; padding: 2px 6px; border-radius: 4px; 
        font-size: 11px; font-weight: bold; margin-right: 8px; white-space: nowrap;
    }
    .title { color: #333; text-decoration: none; font-weight: 500; flex-grow: 1; }
    .title:hover { text-decoration: underline; color: #007bff; }
    .time { font-size: 12px; color: #555; font-family: 'Consolas', monospace; min-width: 120px; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# [기능 3] 구글 뉴스 수집 엔진
# ------------------------------------------------------------------------------
def fetch_google_news(inc_list):
    all_news = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # 검색어가 비어있을 경우 기본 '속보' 검색
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        try:
            url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url, headers=headers, timeout=5)
            
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                for item in root.findall('.//item')[:50]:
                    title = item.find('title').text
                    link = item.find('link').text
                    pubDate = item.find('pubDate').text
                    
                    d_str, ts = process_google_time(pubDate)
                    
                    all_news.append({
                        'source': 'Google',
                        'title': title,
                        'link': link,
                        'time': d_str,
                        'ts': ts,
                        'full_text': title.lower()
                    })
        except Exception:
            pass 

    unique_news = {n['link']: n for n in all_news}.values()
    sorted_news = sorted(unique_news, key=lambda x: x['ts'], reverse=True)
    
    return sorted_news

# ------------------------------------------------------------------------------
# [기능 4] 메인 실행부
# ------------------------------------------------------------------------------
st.sidebar.title("🔍 검색 설정")

# 검색어 입력 (Enter를 치면 즉시 반영됨)
include_input = st.sidebar.text_input(
    "검색어", 
    value="", 
    placeholder="속보, 사건 등 입력 후 엔터..."
)

exclude_input = st.sidebar.text_input(
    "제외어", 
    value="", 
    placeholder="제외할 단어 입력..."
)

# 새로고침 버튼
refresh_button = st.sidebar.button("뉴스 확인 (새로고침)")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

st.title("📰 실시간 뉴스 (구글 기반)")

# [핵심 로직] 검색어가 입력되었거나(엔터), 새로고침 버튼을 눌렀을 때 실행
if include_input or refresh_button:
    with st.spinner('최신 기사를 가져오는 중...'):
        news_list = fetch_google_news(inc_words)
        
        # 제외어 필터링
        final_list = []
        for n in news_list:
            text_check = n.get('full_text', '')
            if not exc_words or not any(word in text_check for word in exc_words):
                final_list.append(n)
        
        # 화면 출력
        if final_list:
            st.success(f"✅ 총 {len(final_list)}건의 기사 (최신순 정렬)")
            for n in final_list:
                st.markdown(f"""
                    <div class="news-row">
                        <span class="badge-google">Google</span>
                        <a href="{n['link']}" target="_blank" class="title">{n['title']}</a>
                        <span class="time">{n['time']}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("조건에 맞는 기사가 없습니다.")
else:
    # 최초 실행 시 안내 메시지
    st.info("왼쪽 사이드바에 검색어를 입력하고 엔터를 치거나 버튼을 눌러주세요.")