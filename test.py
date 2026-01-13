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

# [1] 시간 변환기 (방금 전, 1분 전 -> 실제 시간으로)
def parse_relative_time(text):
    now = datetime.now()
    try:
        text = str(text)
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

# [3] 뉴스 수집 엔진 (Daum + Google + Naver)
def fetch_final_news(inc_list):
    all_news = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        # ------------------------------------------------
        # [A] 다음(Daum) 뉴스: 속도 빠름, 차단 덜 함
        # ------------------------------------------------
        try:
            url = f"https://search.daum.net/search?w=news&q={kw}&sort=recency"
            res = requests.get(url, headers=headers, timeout=3)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for item in soup.select("ul.list_news > li"):
                title_tag = item.select_one("a.tit_main")
                time_tag = item.select_one("span.txt_info")
                
                if title_tag:
                    time_txt = time_tag.text if time_tag else "최근"
                    all_news.append({
                        'source': 'Daum',
                        'title': title_tag.text,
                        'link': title_tag['href'],
                        'display_time': time_txt,
                        'timestamp': parse_relative_time(time_txt).timestamp(),
                        'full_text': title_tag.text.lower()
                    })
        except Exception:
            pass # 에러나면 조용히 다음 단계로

        # ------------------------------------------------
        # [B] 구글(Google) 뉴스: 데이터 확실함 (106개 보장)
        # ------------------------------------------------
        try:
            url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url, headers=headers, timeout=5)
            
            if res.status_code == 200:
                root = ET.fromstring(res.content)
                count = 0
                for item in root.findall('.//item'):
                    if count > 30: break # 너무 많으면 화면 복잡하니 30개만
                    
                    title = item.find('title').text
                    link = item.find('link').text
                    pubDate = item.find('pubDate').text
                    
                    # 시간 표시 (HH:MM)
                    display_time = pubDate[17:22] if len(pubDate) > 20 else "Google"
                    
                    all_news.append({
                        'source': 'Google',
                        'title': title,
                        'link': link,
                        'display_time': display_time,
                        # 구글은 순서대로 오니까 현재시간에서 1분씩 빼서 정렬 맞춤
                        'timestamp': datetime.now().timestamp() - (count * 60),
                        'full_text': title.lower()
                    })
                    count += 1
        except Exception:
            pass 

        # ------------------------------------------------
        # [C] 네이버(Naver) 뉴스: 차단 심하지만 시도는 해봄
        # ------------------------------------------------
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
                            'timestamp': parse_relative_time(time_tag.text).timestamp(),
                            'full_text': title.text.lower()
                        })
        except Exception:
            pass

    # [최종] 시간순 정렬 (최신이 위로)
    unique = {n['link']: n for n in all_news}.values()
    sorted_news = sorted(unique, key=lambda x: x['timestamp'], reverse=True)
    
    return sorted_news

# [4] 메인 화면
st.sidebar.title("📡 뉴스 필터")
include_input = st.sidebar.text_input("검색어", "삼성전자, 수주, 계약, 공시")
exclude_input = st.sidebar.text_input("제외어", "부고, 인사, 광고")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

st.title("📡 실시간 뉴스 레이더 (Daum/Google)")

if st.button("레이더 가동 (새로고침)"):
    with st.spinner('뉴스를 긁어오는 중입니다...'):
        news_list = fetch_final_news(inc_words)
        
        final_list = []
        for n in news_list:
            pass_exc = not any(word in n['full_text'] for word in exc_words)
            if pass_exc:
                final_list.append(n)
        
        if final_list:
            st.success(f"✅ 총 {len(final_list)}건 발견")
            for n in final_list:
                if n['source'] == 'Naver': badge = 'badge-naver'
                elif n['source'] == 'Daum': badge = 'badge-daum'
                else: badge = 'badge-google'
                
                st.markdown(f"""
                    <div class="news-row">
                        <span class="badge {badge}">{n['source']}</span>
                        <a href="{n['link']}" target="_blank" class="title">{n['title']}</a>
                        <span class="time">{n['display_time']}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("결과가 없습니다.")