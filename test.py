import os
import sys

# [1] 기본 경로 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import re
from email.utils import parsedate_to_datetime

# ------------------------------------------------------------------------------
# [기능 1] 날짜/시간 변환기 (YYYY-MM-DD HH:MM 형식 통일)
# ------------------------------------------------------------------------------
def get_time_info(source, text):
    now = datetime.now()
    calc_time = now # 기본값
    
    try:
        text = str(text).strip()
        
        # [A] 다음/네이버 상대시간 처리 ("방금 전", "1분 전")
        if source in ['Daum', 'Naver']:
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
                # 날짜만 있으면 정렬을 위해 그날 09:00로 설정
                calc_time = datetime.strptime(text[:10], "%Y.%m.%d").replace(hour=9, minute=0)
                
        # [B] 구글 RSS 시간 처리
        elif source == 'Google':
            dt = parsedate_to_datetime(text)
            calc_time = dt + timedelta(hours=9) # 한국 시간 보정 (+9h)
            
    except:
        calc_time = now # 계산 실패시 현재 시간

    # 결과 반환: (화면표시용 문자열, 정렬용 숫자)
    return calc_time.strftime("%Y-%m-%d %H:%M"), calc_time.timestamp()

# ------------------------------------------------------------------------------
# [기능 2] 화면 디자인 (날짜 공간 확보)
# ------------------------------------------------------------------------------
st.set_page_config(page_title="뉴스 통합 레이더", layout="wide")
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
    .time { font-size: 12px; color: #555; font-family: 'Consolas', monospace; min-width: 120px; text-align: right; letter-spacing: -0.5px;}
    </style>
    """, unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# [기능 3] 데이터 수집 엔진 (3사 통합 + 에러 방지)
# ------------------------------------------------------------------------------
def fetch_all_news(inc_list):
    all_news = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}
    
    search_keywords = inc_list if inc_list else ["속보"]
    
    for kw in search_keywords:
        # [1] 다음(Daum) 뉴스 - 우선 순위
        try:
            url = f"https://search.daum.net/search?w=news&q={kw}&sort=recency"
            res = requests.get(url, headers=headers, timeout=3)
            # [수정] 괄호 에러가 났던 부분 수정 완료
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for item in soup.select("ul.list_news > li"):
                title = item.select_one("a.tit_main")
                time_tag = item.select_one("span.txt_info")
                if title:
                    raw_time = time_tag.text if time_tag else "방금 전"
                    d_str, ts = get_time_info('Daum', raw_time)
                    
                    all_news.append({
                        'source': 'Daum',
                        'title': title.text,
                        'link': title['href'],
                        'time': d_str,
                        'ts': ts,
                        'full_text': title.text.lower() # [수정] 누락되었던 키 추가 완료
                    })
        except Exception:
            pass # 에러 무시하고 다음으로

        # [2] 네이버(Naver) 뉴스
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
            res = requests.get(url, headers=headers, timeout=2)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for item in soup.select("div.news_wrap"):
                title = item.select_one("a.news_tit")
                time_tag = item.select_one("span.info")
                if title and time_tag:
                    if "전" in time_tag.text: # 최신 뉴스만
                        d_str, ts = get_time_info('Naver', time_tag.text)
                        
                        all_news.append({
                            'source': 'Naver',
                            'title': title.text,
                            'link': title['href'],
                            'time': d_str,
                            'ts': ts,
                            'full_text': title.text.lower() # [수정] 누락되었던 키 추가 완료
                        })
        except Exception:
            pass

        # [3] 구글(Google) 뉴스 - 백업용
        try:
            url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
            res = requests.get(url, headers=headers, timeout=4)
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
                        'ts': ts - count, # 동시간대 순서 보정
                        'full_text': title.lower() # [확인] 여기는 원래 있었음
                    })
                    count += 1
        except Exception:
            pass

    # [최종] 시간순 정렬 (최신이 위로)
    # 중복 제거 (링크 기준)
    unique = {n['link']: n for n in all_news}.values()
    sorted_news = sorted(unique, key=lambda x: x['ts'], reverse=True)
    
    return sorted_news

# ------------------------------------------------------------------------------
# [4] 메인 실행부
# ------------------------------------------------------------------------------
st.sidebar.title("📡 검색 옵션")
include_input = st.sidebar.text_input("검색어 (콤마 구분)", "삼성전자, 수주, 계약, 공시")
exclude_input = st.sidebar.text_input("제외어 (콤마 구분)", "부고, 인사, 광고")

inc_words = [w.strip() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip() for w in exclude_input.split(",") if w.strip()]

st.title("📡 뉴스 통합 레이더")

if st.button("레이더 가동 (새로고침)"):
    with st.spinner('다음/네이버/구글 뉴스를 통합 수집 중...'):
        news_list = fetch_all_news(inc_words)
        
        final_list = []
        for n in news_list:
            # [수정] KeyError 방지: .get()을 사용하여 안전하게 꺼냄
            text_for_check = n.get('full_text', '')
            pass_exc = not any(word in text_for_check for word in exc_words)
            if pass_exc:
                final_list.append(n)
        
        if final_list:
            st.success(f"✅ 총 {len(final_list)}건 수집 완료 (최신순)")
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