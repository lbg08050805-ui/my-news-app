import os
import sys

# 현재 이 파일이 있는 폴더의 절대 경로를 알아내서 작업 폴더로 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

# 파일명: test.py

# [1] 화면 디자인
st.set_page_config(page_title="기사검색", layout="wide")
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    .news-row { display: flex; font-size: 14px; margin-bottom: 8px; border-bottom: 1px solid #f0f0f0; padding-bottom: 8px; }
    .source-badge { 
        background-color: #eee; color: #555; padding: 2px 6px; border-radius: 4px; 
        font-size: 11px; font-weight: bold; margin-right: 8px; white-space: nowrap; height: fit-content;
    }
    .source-naver { background-color: #03C75A; color: white; }
    .source-google { background-color: #4285F4; color: white; }
    .title { color: #1a0dab; text-decoration: none; font-weight: 500; }
    .title:hover { text-decoration: underline; }
    .date { font-size: 12px; color: #006621; margin-left: 10px; min-width: 60px; }
    </style>
    """, unsafe_allow_html=True)

# [2] 뉴스 수집 엔진
def fetch_news_data(inc_list):
    all_news = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    search_keywords = inc_list if inc_list else ["주식"]
    
    for kw in search_keywords:
        # 구글 뉴스 (RSS)
        google_url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(google_url, headers=headers, timeout=5)
            res.encoding = 'utf-8' 
            root = ET.fromstring(res.content)
            
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ""
                display_date = pubDate[5:16] if len(pubDate) > 16 else "최근"

                all_news.append({
                    'source': 'Google',
                    'title': title,
                    'link': link,
                    'time': display_date,
                    'full_text': title.lower()
                })
        except Exception as e:
            print(f"구글 에러: {e}")

        # 네이버 뉴스 (보조)
        naver_url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
        try:
            res = requests.get(naver_url, headers=headers, timeout=3)
            soup = BeautifulSoup(res.text, 'html.parser')
            news_items = soup.select("div.news_wrap")
            
            if news_items: 
                for item in news_items:
                    t_tag = item.select_one("a.news_tit")
                    if t_tag:
                        all_news.append({
                            'source': 'Naver',
                            'title': t_tag.text,
                            'link': t_tag['href'],
                            'time': '네이버',
                            'full_text': t_tag.text.lower()
                        })
        except:
            pass
    
    unique = {n['link']: n for n in all_news}.values()
    return list(unique)

# [3] 사이드바 설정
st.sidebar.title("🔍 검색 옵션")
include_input = st.sidebar.text_input("검색어 (쉼표로 구분)", "삼성전자, 수주, 계약")
exclude_input = st.sidebar.text_input("제외할 단어", "부고, 인사")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

# [4] 메인 화면
st.title("📟 통합 뉴스 모니터링")

# [수정] 이제 버튼을 눌러야만 검색합니다 (자동 실행 방지)
if st.button("🔍 뉴스 검색 시작"):
    with st.spinner('뉴스를 찾아오고 있습니다...'):
        raw_pool = fetch_news_data(inc_words)
        final_list = []

        for n in raw_pool:
            pass_exc = not any(word in n['full_text'] for word in exc_words)
            if pass_exc:
                final_list.append(n)

        st.success(f"검색어: {include_input} | 발견된 기사: {len(final_list)}건")

        if final_list:
            for n in final_list:
                badge_class = "source-naver" if n['source'] == 'Naver' else "source-google"
                st.markdown(f"""
                    <div class="news-row">
                        <span class="source-badge {badge_class}">{n['source']}</span>
                        <a href="{n['link']}" target="_blank" class="title">{n['title']}</a>
                        <span class="date">{n['time']}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("검색 결과가 없습니다.")