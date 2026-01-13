import os
import sys

# 작업 폴더 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime

# [1] 기본 설정
st.set_page_config(page_title="시스템 점검", layout="wide")
st.title("🛠 뉴스 시스템 진단 모드")

# [2] 뉴스 수집 함수 (에러를 숨기지 않고 화면에 출력함)
def fetch_debug_news(inc_list):
    all_news = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    search_keywords = inc_list if inc_list else ["속보"]
    
    # 상태 로그창
    log_area = st.expander("📡 시스템 작동 로그 (클릭해서 확인)", expanded=True)
    
    with log_area:
        for kw in search_keywords:
            st.write(f"--- 키워드 '{kw}' 검색 시작 ---")
            
            # [A] 구글 뉴스 (가장 확실한 방법부터 시도)
            try:
                url = f"https://news.google.com/rss/search?q={kw}&hl=ko&gl=KR&ceid=KR:ko"
                res = requests.get(url, headers=headers, timeout=5)
                
                if res.status_code == 200:
                    try:
                        root = ET.fromstring(res.content)
                        items = root.findall('.//item')
                        st.write(f"✅ 구글 접속 성공: {len(items)}개 데이터 수신")
                        
                        for item in items:
                            title = item.find('title').text
                            link = item.find('link').text
                            pubDate = item.find('pubDate').text
                            
                            all_news.append({
                                'source': 'Google',
                                'title': title,
                                'link': link,
                                'time': pubDate[17:22], # 시간만 추출
                                'full_text': title.lower()
                            })
                    except Exception as e:
                        st.error(f"❌ 구글 데이터 해석 실패: {e}")
                else:
                    st.warning(f"⚠️ 구글 접속 차단됨 (코드: {res.status_code})")
            except Exception as e:
                st.error(f"❌ 구글 연결 자체 실패: {e}")

            # [B] 네이버 뉴스 (차단 여부 확인용)
            try:
                url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
                res = requests.get(url, headers=headers, timeout=3)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.text, 'html.parser')
                    items = soup.select("div.news_wrap")
                    st.write(f"✅ 네이버 접속 성공: {len(items)}개 발견")
                    
                    for item in items:
                        title = item.select_one("a.news_tit")
                        time_tag = item.select_one("span.info")
                        if title:
                            all_news.append({
                                'source': 'Naver',
                                'title': title.text,
                                'link': title['href'],
                                'time': time_tag.text if time_tag else "최근",
                                'full_text': title.text.lower()
                            })
                else:
                    st.warning(f"⚠️ 네이버가 서버를 차단함 (코드: {res.status_code})")
            except Exception as e:
                st.write(f"❌ 네이버 연결 에러: {e}")

    return all_news

# [3] 메인 화면 실행
keyword = st.text_input("검색어", "삼성전자, 속보")
inc_words = [w.strip() for w in keyword.split(",") if w.strip()]

if st.button("🔍 진단 시작"):
    news_list = fetch_debug_news(inc_words)
    
    st.markdown("---")
    st.subheader(f"📊 최종 수집 결과: {len(news_list)}건")
    
    if news_list:
        for n in news_list:
            color = "blue" if n['source'] == 'Google' else "green"
            st.markdown(f":{color}[[{n['source']}]] **{n['title']}** ({n['time']})")
            st.markdown(f"<small>{n['link']}</small>", unsafe_allow_html=True)
    else:
        st.error("수집된 뉴스가 0건입니다. 위 로그를 확인해주세요.")