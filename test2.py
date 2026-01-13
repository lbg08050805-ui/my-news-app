import streamlit as st
import requests
from bs4 import BeautifulSoup

# 파일명: test.py

st.set_page_config(page_title="출처별 수집 마킹", layout="wide")

# [1] 디자인: 오직 출처와 숫자만 강조
st.markdown("""
    <style>
    .source-box { 
        background-color: #f1f3f5; border: 1px solid #dee2e6; padding: 15px; 
        border-radius: 8px; margin-bottom: 10px; font-family: 'Malgun Gothic', sans-serif;
    }
    .source-name { font-size: 16px; font-weight: bold; color: #333; }
    .source-count { font-size: 20px; font-weight: bold; color: #d9534f; float: right; }
    .total-summary { font-size: 22px; font-weight: bold; color: #007bff; padding: 20px; border-top: 2px solid #007bff; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

def check_each_source(inc_list):
    """사용자 로직: 각 출처를 '각각' 방문하여 중복 없이 수량을 마킹함"""
    headers = {"User-Agent": "Mozilla/5.0"}
    keywords = inc_list if inc_list else ["주식"]
    
    # 12개 출처 명단 (마킹 대상)
    sources = {
        "1. 네이버 증권 뉴스": "https://search.naver.com/search.naver?where=news&query={kw}&sort=1",
        "2. 구글 RSS 피드": "https://news.google.com/rss/search?q={kw}+when:1d&hl=ko&gl=KR",
        "3. 팍스넷 실시간 속보": "http://www.paxnet.co.kr/news/realtime?searchKey=title&searchValue={kw}",
        "4. 다음 증권 뉴스": "https://search.daum.net/search?w=news&q={kw}&sort=recency",
        "5. 연합인포맥스 속보": "https://news.einfomax.co.kr/news/articleList.html?sc_word={kw}",
        "6. 한국경제 실시간": "https://search.naver.com/search.naver?where=news&query={kw}+site:hankyung.com&sort=1",
        "7. 매일경제 실시간": "https://search.naver.com/search.naver?where=news&query={kw}+site:mk.co.kr&sort=1",
        "8. 증권사 리포트 합산": "https://search.naver.com/search.naver?where=news&query={kw}+리포트&sort=1",
        "9. 오전장 특징주(1)": "https://search.naver.com/search.naver?where=news&query={kw}+특징주&sort=1",
        "10. 오후장 특징주(2)": "https://search.naver.com/search.naver?where=news&query={kw}+상승세&sort=1",
        "11. 뉴스핌(Newspim)": "https://www.newspim.com/search/news?q={kw}",
        "12. DART 공시 속보": "https://search.naver.com/search.naver?where=news&query={kw}+공시&sort=1"
    }
    
    report = {}
    total_raw = 0

    for name, url_template in sources.items():
        source_count = 0
        for kw in keywords:
            try:
                url = url_template.format(kw=kw)
                res = requests.get(url, headers=headers, timeout=5)
                # 단순 수량 체크 (HTML 구조에 상관없이 수집된 아이템 개수 파악)
                soup = BeautifulSoup(res.text, 'html.parser')
                items = soup.select(".news_tit, .tit_main, .title a, item")
                source_count += len(items)
            except: pass
        report[name] = source_count
        total_raw += source_count
        
    return report, total_raw

# [실행부]
st.title("📟 12대 출처 수집 마킹 보고서")
include_input = st.sidebar.text_input("검색 키워드", "삼성전자, 수주, 계약")
inc_words = [w.strip() for w in include_input.split(",")]

if st.button("📊 실시간 출처 마킹 시작"):
    report_data, total_sum = check_each_source(inc_words)
    
    # 출처별 결과 출력
    for name, count in report_data.items():
        st.markdown(f"""
            <div class="source-box">
                <span class="source-name">{name}</span>
                <span class="source-count">{count}개 수집됨</span>
            </div>
        """, unsafe_allow_html=True)
        
    st.markdown(f"""
        <div class="total-summary">
            검색된 총 원천 데이터: {total_sum}개
        </div>
    """, unsafe_allow_html=True)
else:
    st.info("왼쪽 사이드바에 키워드를 넣고 '마킹 시작' 버튼을 눌러주세요.")