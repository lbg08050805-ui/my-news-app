import streamlit as st
import requests
from bs4 import BeautifulSoup

# 1. 페이지 설정 (브라우저 탭에 표시될 이름)
st.set_page_config(page_title="나만의 뉴스 피드", layout="wide")

# 2. 메인 제목 수정
st.title("🗞️ 실시간 뉴스")

def get_google_news(keyword):
    url = f"https://news.google.com/rss/search?q={keyword}&hl=ko&gl=KR&ceid=KR:ko"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'lxml-xml')
    return soup.find_all('item')[:15] # 키워드당 15개로 확대

# 3. 사이드바 설정
st.sidebar.header("설정")
keywords = st.sidebar.text_input("관심 키워드 (쉼표로 구분)", "인공지능, 삼성전자, 테슬라")
keyword_list = [k.strip() for k in keywords.split(",")]

# 4. 뉴스 출력 본문
for kw in keyword_list:
    st.markdown(f"### 📍 {kw}") # 키워드 표시
    items = get_google_news(kw)
    
    for item in items:
        # 뉴스 제목과 시간만 간결하게 표시
        col1, col2 = st.columns([8.5, 1.5])
        with col1:
            # 주식 등 불필요한 수식어 없이 기사 제목만 출력
            st.markdown(f"• [{item.title.text}]({item.link.text})")
        with col2:
            # 발행 시간 표시 (예: 12 Jan 2026)
            st.caption(item.pubDate.text[5:16])
    st.divider() # 키워드별 구분선