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
from email.utils import parsedate_to_datetime

# [1] 통합 시간 계산기 (결과: "2026-01-13 14:30", 정렬용 숫자)
def get_time_info(source, text):
    now = datetime.now()
    # 기본값 설정
    display_str = now.strftime("%Y-%m-%d %H:%M")
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
                # 날짜만 있는 경우 그날 아침 09:00로 가정 (정렬 위해)
                calc_time = datetime.strptime(text[:10], "%Y.%m.%d").replace(hour=9, minute=0)
            else:
                calc_time = now
            
            # [수정] 상무님 요청 포맷: 연-월-일 시:분
            display_str = calc_time.strftime("%Y-%m-%d %H:%M")
            timestamp = calc_time.timestamp()

        # [B] 구글: "Tue, 13 Jan 2026 05:00:00 GMT" 형식
        elif source == 'Google':
            # RSS 날짜 해석
            dt = parsedate_to_datetime(text)
            # 한국 시간으로 변환 (+9시간)
            kst_dt = dt + timedelta(hours=9)
            
            # [수정] 상무님 요청 포맷: 연-월-일 시:분
            display_str = kst_dt.strftime("%Y-%m-%d %H:%M")
            timestamp = kst_dt.timestamp()

    except Exception:
        pass # 에러나면 현재시간 유지

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
    /* 날짜 디자인: 폭을 110px로 늘려서 연월일 시분 다 보이게 함 */
    .time { font-size: 12px; color: #666; font-family: 'Consolas', monospace; min-width: 110px; text-align: right; letter-spacing: -0.5px;}
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
                    
                    # 구글은 순서대로 오므로, 같은 시간대면 순서 유지위해 미세조정
                    all_news.append({'source':'Google', 'title':title, 'link':link, 'time':d_str, 'ts':ts - count, 'full':title})
                    count += 1
        except: pass

        # 3. 네이버(Naver)
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select("div.news_wrap"):
                title = item.select_one("a.news_tit")
                time_tag = item.select_one("span.info")
                if title and time_tag:
                    if "전" in time_tag.text:
                        d_str, ts = get_time_info('Naver', time_tag.text)
                        all_news.append({'source':'Naver', 'title':title.text, 'link':title['href'], 'time':d_str, 'ts':ts, 'full':title.text})
        except: pass

    # [최종 정렬] ts(시간숫자) 기준 내림차순 (최신순)
    unique = {n['link']: n for n in all_news}.values()
    sorted_news = sorted(unique, key=lambda x: x['ts'], reverse=True)
    
    return sorted_news

# [4] 메인 화면
st.sidebar.title("📡 뉴스 필터")
include_input = st.sidebar.text_input("검색어", "삼성전자, 수주, 계약, 공시")
exclude_input = st.sidebar.text_input("제외어", "부고, 인사, 광고")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

st.title("📡 실시간 뉴스 레이더 (시간순)")

if st.button("레이더 가동 (새로고침)"):
    with st.spinner('최신순 정렬 중...'):
        news_list = fetch_final_news(inc_words)
        
        final_list = []
        for n in news_list:
            pass_exc = not any(word in n['full_text'] for word in exc_words)
            if pass_exc:
                final_list.append(n)
        
        if final_list:
            st.success(f"✅ 총 {len(final_list)}건 발견 (최신순 정렬)")
            for n in final_list:
                if n['source'] == 'Naver': badge = 'badge-naver'
                elif n['source'] == 'Daum': badge = 'badge-daum'
                else: badge = 'badge-google'
                
                st.markdown(f"""
                    <div class="news-row">
                        <span class="badge {badge}">{n['source']}</span>
                        <a href="{n['link']}" target="_blank" class="title">{n['title']}</a>
                        <span class="time">{n['time']}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("검색 결과가 없습니다.")