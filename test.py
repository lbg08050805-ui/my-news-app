import os
import sys

# 작업 폴더 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
from email.utils import parsedate_to_datetime # 구글 날짜 해석용 도구

# [1] 통합 시간 계산기 (결과: "2026-01-13 14:30", 정렬용 숫자)
def get_time_info(source, text):
    now = datetime.now()
    display_str = now.strftime("%Y-%m-%d %H:%M") # 기본값
    timestamp = now.timestamp()
    
    try:
        # [A] 네이버/다음: "방금 전", "10분 전" 등 상대 시간
        if source in ['Naver', 'Daum']:
            if "방금" in text:
                calc_time = now
            elif "분 전" in text:
                mins = int(re.search(r'(\d+)', text).group(1))
                calc_time = now - timedelta(minutes=mins)
            elif "시간 전" in text:
                hours = int(re.search(r'(\d+)', text).group(1))
                calc_time = now - timedelta(hours=hours)
            elif "일 전" in text:
                days = int(re.search(r'(\d+)', text).group(1))
                calc_time = now - timedelta(days=days)
            elif "." in text and len(text) >= 10: # 2026.01.13. 형식
                # 날짜만 있는 경우 09:00로 가정
                calc_time = datetime.strptime(text[:10], "%Y.%m.%d")
            else:
                calc_time = now
            
            display_str = calc_time.strftime("%m-%d %H:%M") # 월-일 시:분
            timestamp = calc_time.timestamp()

        # [B] 구글: "Tue, 13 Jan 2026 05:00:00 GMT" 형식
        elif source == 'Google':
            # RSS 날짜 해석
            dt = parsedate_to_datetime(text)
            # 한국 시간으로 변환 (+9시간)
            kst_dt = dt + timedelta(hours=9)
            
            display_str = kst_dt.strftime("%m-%d %H:%M")
            timestamp = kst_dt.timestamp()

    except Exception:
        pass # 에러나면 현재시간으로 유지

    return display_str, timestamp

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
    .badge-daum { background-color: #F7E600; color: #333; }
    .badge-google { background-color: #4285F4; color: white; }
    .title { color: #333; text-decoration: none; font-weight: 500; flex-grow: 1; }
    .title:hover { text-decoration: underline; color: #007bff; }
    /* 날짜 나오는 부분 디자인 (폭을 넓힘) */
    .time { font-size: 12px; color: #666; font-family: 'Consolas', monospace; min-width: 90px; text-align: right; letter-spacing: -0.5px;}
    </style>
    """, unsafe_allow_html=True)

# [3] 뉴스 수집 엔진
def fetch_final_news(inc_list):
    all_news = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        # 1. 다음(Daum)
        try:
            url = f"https://search.daum.net/search?w=news&q={kw}&sort=recency"
            res = requests.get(url, headers=headers, timeout=3)
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select("ul.list_news > li"):
                title = item.select_one("a.tit_main")
                time_tag = item.select_one("span.txt_info")
                if title:
                    time_txt = time_tag.text if time_tag else "방금 전"
                    d_str, ts = get_time_info('Daum', time_txt)
                    all_news.append({'source':'Daum', 'title':title.text, 'link':title['href'], 'time':d_str, 'ts':ts, 'full':title.text})
        except: pass

        # 2. 구글(Google)
        try:
            url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                count = 0
                for item in root.findall('.//item'):
                    if count > 30: break
                    title = item.find('title').text
                    link = item.find('link').text
                    pubDate = item.find('pubDate').text # RSS 원본 시간
                    
                    d_str, ts = get_time_info('Google', pubDate)
                    
                    all_news.append({'source':'Google', 'title':title, 'link':link, 'time':d_str, 'ts':ts, 'full':title})
                    count += 1
        except: pass

        # 3. 네이버(Naver)
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(