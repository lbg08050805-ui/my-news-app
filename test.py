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

# [1] 시간 변환기
def parse_date(text):
    now = datetime.now()
    try:
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
    except:
        pass
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
    .badge-daum { background-color: #F7E600; color: #333; }
    .badge-google { background-color: #4285F4; color: white; }
    .title { color: #333; text-decoration: none; font-weight: 500; flex-grow: 1; }
    .title:hover { text-decoration: underline; color: #007bff; }
    .time { font-size: 12px; color: #d93025; font-weight: bold; min-width: 80px; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# [3] 뉴스 수집 엔진 (3중 하이브리드)
def fetch_triple_news(inc_list):
    all_news = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        # --- [A] 네이버 뉴스 (1순위) ---
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select("div.news_wrap"):
                title = item.select_one("a.news_tit")
                time_tag = item.select_one("span.info")
                if title and time_tag:
                    if "전" in time_tag.text:
                        all_news.append({
                            'source': 'Naver',
                            'title': title.text,
                            'link': title['href'],
                            'display_time': time_tag.text,
                            'timestamp': parse_date(time_tag.text).timestamp(),
                            'full_text': title.text.lower()
                        })
        except: 
            pass # 네이버 에러 무시

        # --- [B] 다음 뉴스 (2순위) ---
        try:
            url = f"https://search.daum.net/search?w=news&q={kw}&sort=recency"
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select("ul.list_news > li"):
                title = item.select_one("a.tit_main")
                time_tag = item.select_one("span.txt_info")
                if title and time_tag:
                    all_news.append({
                        'source': 'Daum',
                        'title': title.text,
                        'link': title['href'],
                        'display_time': time_tag.text,
                        'timestamp': parse_date(time_tag.text).timestamp(),
                        'full_text': title.text.lower()
                    })
        except: 
            pass # 다음 에러 무시

        # --- [C] 구글 뉴스 (3순위) ---
        try:
            url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url, headers=headers, timeout=3)
            root = ET.fromstring(res.content)
            count = 0
            for item in root.findall('.//item'):
                if count > 10: break
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text
                display_time = pubDate[17:22] if len(pubDate) > 20 else "Google"
                
                all_news.append({
                    'source': 'Google',
                    'title': title,
                    'link': link,
                    'display_time': display_time,
                    'timestamp': datetime.now().timestamp() - (count * 60),
                    'full_text': title.lower()
                })
                count += 1
        except: 
            pass # 구글 에러 무시 (이 부분이 빠져서 에러가 났었습니다)

    # 통합 및 정렬