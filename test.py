import os
import sys

# [기본 설정] 현재 작업 폴더로 경로 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
from email.utils import parsedate_to_datetime

# ------------------------------------------------------------------------------
# [1] 시간 계산 및 포맷팅 함수 (핵심: 연-월-일 시:분 통일)
# ------------------------------------------------------------------------------
def get_time_info(source, text):
    now = datetime.now()
    calc_time = now # 기본값
    
    try:
        # [A] 다음/네이버 (상대 시간: "방금 전", "1분 전")
        if source in ['Daum', 'Naver']:
            text = str(text).strip()
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
            elif "." in text and len(text) >= 10: # 2026.01.13. 날짜만 있는 경우
                # 날짜만 있으면 그날 오전 9시로 가정 (정렬 편의상)
                calc_time = datetime.strptime(text[:10], "%Y.%m.%d").replace(hour=9, minute=0)
            else:
                calc_time = now # 인식 실패시 현재시간
                
        # [B] 구글 (RSS 시간: "Tue, 13 Jan 2026...")
        elif source == 'Google':
            dt = parsedate_to_datetime(text)
            calc_time = dt + timedelta(hours=9) # 한국 시간 보정
            
    except:
        calc_time = now # 에러나면 현재시간

    # [결과 반환]
    # 1. 화면 표시용: "2026-01-13 14:30" (연-월-일 시:분)
    display_str = calc_time.strftime("%Y-%m-%d %H:%M")
    # 2. 정렬용 숫자 (Timestamp)
    timestamp = calc_time.timestamp()
    
    return display_str, timestamp

# ------------------------------------------------------------------------------
# [2] 화면 디자인 설정
# ------------------------------------------------------------------------------
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
    .time { font-size: 12px; color: #555; font-family: 'Consolas', monospace; min-width: 120px; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# [3] 뉴스 수집 엔진 (3중 구조: 다음 -> 구글 -> 네이버)
# ------------------------------------------------------------------------------
def fetch_final_news(inc_list):
    all_news = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        # [A] 다음(Daum) 뉴스
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
                    
                    all_news.append({
                        'source': 'Daum',
                        'title': title.text,
                        'link': title['href'],
                        'time': d_str,
                        'ts': ts,
                        'full_text': title.text.lower() # [중요] 필터링용 텍스트
                    })
        except: pass

        # [B] 구글(Google) 뉴스
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
                    pubDate = item.find('pubDate').text
                    
                    d_str, ts = get_time_info('Google', pubDate)
                    
                    all_news.append({
                        'source': 'Google',
                        'title': title,
                        'link': link,
                        'time': d_str,
                        'ts': ts - count, # 같은 시간일 경우 순서 보장용 미세 조정
                        'full_text': title.lower() # [중요] 필터링용 텍스트
                    })
                    count += 1
        except: pass

        # [C] 네이버(Naver) 뉴스
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
                        all_news.append({
                            'source': 'Naver',
                            'title': title.text,
                            'link': title['href'],
                            'time': d_str,
                            'ts': ts,
                            'full_text': title.text.lower() # [중요] 필터링용 텍스트
                        })
        except: pass

    # [최종 정렬] ts(타임스탬프) 기준 내림차순 (가장 최신이 위로)
    unique = {n['link']: n for n in all_news}.values()
    sorted_news = sorted(unique, key=lambda x: x['ts'], reverse=True)
    
    return sorted_news

# ------------------------------------------------------------------------------
# [4] 메인 화면 실행
# ------------------------------------------------------------------------------
st.sidebar.title("📡 뉴스 필터")
include_input = st.sidebar.text_input("검색어 (콤마 구분)", "삼성전자, 수주, 계약, 공시")
exclude_input = st.sidebar.text_input("제외어 (콤마 구분)", "부고, 인사, 광고")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

st.title("📡 실시간 뉴스 레이더 (최신순)")

if st.button("레이더 가동 (새로고침)"):
    with st.spinner('뉴스를 모아서 날짜순으로 정렬 중입니다...'):
        news_list = fetch_final_news(inc_words)
        
        final_list = []
        for n in news_list:
            # [에러 수정 핵심] .get('full_text', '')를 써서 키가 없어도 죽지 않게 함
            target_text = n.get('full_text', '') 
            pass_exc = not any(word in target_text for word in exc_words)
            if pass_exc:
                final_list.append(n)
        
        if final_list:
            st.success(f"✅ 총 {len(final_list)}건 발견 (YYYY-MM-DD HH:MM)")
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