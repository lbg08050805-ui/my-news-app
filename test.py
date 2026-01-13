import os
import sys

# 현재 작업 폴더 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re

# [1] 시간 변환기 (네이버 "1분 전" & 구글 날짜 통합)
def parse_date(source, text):
    now = datetime.now()
    try:
        if source == 'Naver':
            if "방금" in text: return now
            elif "분 전" in text:
                mins = int(re.search(r'(\d+)', text).group(1))
                return now - timedelta(minutes=mins)
            elif "시간 전" in text:
                hours = int(re.search(r'(\d+)', text).group(1))
                return now - timedelta(hours=hours)
            elif "일 전" in text:
                days = int(re.search(r'(\d+)', text).group(1))
                return now - timedelta(days=days)
            else:
                return now # 인식 불가시 현재 시간으로 처리

        elif source == 'Google':
            # 구글 날짜 파싱 (ex: Mon, 13 Jan 2026 ...)
            # 복잡하므로 단순화: 오늘 날짜로 간주하되 RSS 순서 믿음
            # (정확한 파싱보다 속도가 중요)
            return now 
    except:
        return now
    return now

# [2] 디자인 설정
st.set_page_config(page_title="뉴스 레이더", layout="wide")
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    .news-row { display: flex; align-items: center; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid #f0f0f0; padding-bottom: 8px; }
    .badge { 
        padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 8px; white-space: nowrap; width: 60px; text-align: center;
    }
    .badge-naver { background-color: #03C75A; color: white; }
    .badge-google { background-color: #4285F4; color: white; }
    .title { color: #333; text-decoration: none; font-weight: 500; flex-grow: 1; }
    .title:hover { text-decoration: underline; color: #007bff; }
    .time { font-size: 12px; color: #d93025; font-weight: bold; min-width: 80px; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# [3] 뉴스 수집 엔진 (하이브리드)
def fetch_hybrid_news(inc_list):
    all_news = []
    
    # 강력한 헤더
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        # --- [A] 네이버 뉴스 시도 (속도 우선) ---
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
            res = requests.get(url, headers=headers, timeout=2) # 2초 안에 안오면 패스
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.select("div.news_wrap")
            
            for item in items:
                title = item.select_one("a.news_tit")
                time_tag = item.select_one("span.info")
                if title and time_tag:
                    time_txt = time_tag.text
                    if "전" in time_txt or "." in time_txt: # 최신 뉴스만
                        dt = parse_date('Naver', time_txt)
                        all_news.append({
                            'source': 'Naver',
                            'title': title.text,
                            'link': title['href'],
                            'display_time': time_txt,
                            'timestamp': dt.timestamp(),
                            'full_text': title.text.lower()
                        })
        except:
            pass # 네이버 실패해도 조용히 넘어감

        # --- [B] 구글 뉴스 보충 (안정성 우선) ---
        try:
            url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url, headers=headers, timeout=3)
            root = ET.fromstring(res.content)
            
            # 구글은 이미 관련성 높은 순이므로 상위 10개만 가져옴 (속도 위해)
            count = 0
            for item in root.findall('.//item'):
                if count > 15: break
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('