import os
import sys

# 현재 이 파일이 있는 폴더의 절대 경로를 알아내서 작업 폴더로 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime # 날짜 정밀 변환 도구

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
    .date { font-size: 12px; color: #d93025; margin-left: auto; min-width: 110px; text-align: right; font-weight: bold;}
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
        # ---------------------------------------------------------
        # A. 구글 뉴스 (RSS)
        # ---------------------------------------------------------
        google_url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
        try:
            res = requests.get(google_url, headers=headers, timeout=5)
            res.encoding = 'utf-8' 
            root = ET.fromstring(res.content)
            
            for item in root.findall('.//item'):
                title = item.find('title').text
                link = item.find('link').text
                pubDate_str = item.find('pubDate').text
                
                # [핵심] 날짜/시간 정밀 계산 및 한국 시간 변환
                try:
                    # 1. RSS 날짜 형식 파싱
                    dt_obj = parsedate_to_datetime(pubDate_str)
                    # 2. 한국 시간(KST)으로 변환 (+9시간)
                    # 이미 타임존 정보가 있다면 astimezone으로 변환, 없다면 수동 계산
                    if dt_obj.tzinfo:
                        # 타임존 정보가 있으면 9시간 더하는 방식이 아니라 그냥 시차 적용
                        # 하지만 구글은 보통 GMT로 줌. 단순히 보기 좋게 포맷팅
                        kst_time = dt_obj.astimezone() # 서버 로컬(UTC) -> KST 변환은 환경에 따라 다름
                        # 확실한 방법: 타임스탬프 + 9시간
                        final_dt = dt_obj + timedelta(hours=9)
                    else:
                        final_dt = dt_obj
                    
                    # 3. 화면 표시용 문자열 (년-월-일 시:분)
                    display_time = final_dt.strftime("%Y-%m-%d %H:%M")
                    # 4. 정렬용 숫자 (timestamp)
                    sort_key = final_dt.timestamp()
                    
                except:
                    display_time = "날짜정보없음"
                    sort_key = 0

                all_news.append({
                    'source': 'Google',
                    'title': title,
                    'link': link,
                    'time': display_time,
                    'sort_key': sort_key, # 정렬을 위한 비밀 키
                    'full_text': title.lower()
                })
        except Exception as e:
            print(f"구글 에러: {e}")

        # ---------------------------------------------------------
        # B. 네이버 뉴스 (보조)
        # ---------------------------------------------------------
        naver_url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
        try:
            res = requests.get(naver_url, headers=headers, timeout=3)
            soup = BeautifulSoup(res.text, 'html.parser')
            news_items = soup.select("div.news_wrap")
            
            if news_items: 
                for item in news_items:
                    t_tag = item.select_one("a.news_tit")
                    tm_tag = item.select_one("span.info") # "1시간 전" 같은 텍스트
                    if t_tag:
                        # 네이버는 정확한 시간이 아니라 '1시간 전' 형식이므로
                        # 정렬 순서를 위해 현재시간(가장 최신)으로 간주
                        current_ts = datetime.now().timestamp()
                        
                        all_news.append({
                            'source': 'Naver',
                            'title': t_tag.text,
                            'link': t_tag['href'],
                            'time': tm_tag.text if tm_tag else "최근",
                            'sort_key': current_ts, # 네이버 나오면 일단 최신으로 침
                            'full_text': t_tag.text.lower()
                        })
        except:
            pass
    
    # 중복 제거 (링크 기준)
    unique_dict = {n['link']: n for n in all_news}
    unique_list = list(unique_dict.values())
    
    # [최종 정렬] sort_key(시간 숫자) 기준으로 내림차순(최신순) 정렬
    unique_list.sort(key=lambda x: x['sort_key'], reverse=True)
    
    return unique_list

# [3] 사이드바 설정
st.sidebar.title("🔍 검색 옵션")
include_input = st.sidebar.text_input("검색어 (쉼표로 구분)", "삼성전자, 수주, 계약")
exclude_input = st.sidebar.text_input("제외할 단어", "부고, 인사")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

# [4] 메인 화면
st.title("📟 통합 뉴스 모니터링")

if st.button("🔍 뉴스 검색 시작"):
    with st.spinner('최신순으로 정렬 중입니다...'):
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