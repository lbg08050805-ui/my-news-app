import os
import sys

# 현재 이 파일이 있는 폴더의 절대 경로를 알아내서 작업 폴더로 변경
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# 파일명: test.py

# [1] 화면 디자인 (HTS 명칭 제거 및 출처 스타일 설정)
st.set_page_config(page_title="기사검색", layout="wide")
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    .news-row { display: flex; font-size: 13px; line-height: 1.1; margin-bottom: 2px; border-bottom: 1px solid #f2f2f2; }
    .time { color: #d9534f; font-weight: bold; min-width: 45px; margin-right: 10px; }
    .title { color: #333; text-decoration: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .title:hover { color: #007bff; text-decoration: underline; }
    .source-footer { font-size: 11px; color: #888; margin-top: 20px; border-top: 1px solid #eee; padding-top: 10px; }
    </style>
    """, unsafe_allow_html=True)

# [2] 각각 불러와서 합치는 엔진 (수집 단계)
def fetch_news_data(inc_list):
    all_news = []
    
    # [수정된 부분] 봇 차단 방지용 강력한 헤더 (네이버/구글 공용)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 컴마로 분리된 단어들을 하나씩 꺼내어 '각각' 호출합니다.
    search_keywords = inc_list if inc_list else ["주식"]
    
    for kw in search_keywords:
        # A. 네이버 뉴스 수집
        naver_url = f"https://search.naver.com/search.naver?where=news&query={kw}&sort=1"
        try:
            # 헤더 포함해서 요청
            res = requests.get(naver_url, headers=headers, timeout=5)
            soup = BeautifulSoup(res.text, 'html.parser')
            for item in soup.select(".news_wrap"):
                t_tag = item.select_one(".news_tit")
                tm_tag = item.select_one(".info_group span.info")
                if t_tag:
                    all_news.append({
                        'title': t_tag.text,
                        'link': t_tag['href'],
                        'time': tm_tag.text if tm_tag else "최근",
                        'full_text': t_tag.text.lower()
                    })
        except Exception as e:
            print(f"네이버 에러: {e}")
            pass

        # B. 구글 RSS 수집
        google_url = f"https://news.google.com/rss/search?q={kw}+when:1d&hl=ko&gl=KR&ceid=KR:ko"
        try:
            # [수정] 구글에도 headers를 반드시 넣어야 차단 안 당함
            res = requests.get(google_url, headers=headers, timeout=5)
            # [참고] lxml이 설치 안 되어 있을 수 있으니 기본 파서 사용
            soup = BeautifulSoup(res.text, 'html.parser') 
            for i in soup.find_all('item'):
                all_news.append({
                    'title': i.title.text,
                    'link': i.link.text,
                    'time': "RSS",
                    'full_text': i.title.text.lower()
                })
        except Exception as e:
            print(f"구글 에러: {e}")
            pass
    
    # 중복 제거 (병합 결과 정리)
    unique = {n['link']: n for n in all_news}.values()
    return list(unique)

# [3] 사이드바: 컴마(,) 인식 및 분리 로직 (1번 단계)
st.sidebar.title("🔍 검색 설정")
include_input = st.sidebar.text_input("포함 단어 (OR 조건: A, B)", "삼성전자, 수주, 계약")
exclude_input = st.sidebar.text_input("제외 단어 (OR 조건: R, S)", "광고, 스팸")

# 컴마(,)를 기준으로 검색어를 각각의 단어로 쪼개어 리스트화합니다.
inc_words = [w.strip().lower() for w in include_input.split(",") if w.strip()]
exc_words = [w.strip().lower() for w in exclude_input.split(",") if w.strip()]

# [4] 메인 화면: 제목 "기사검색"으로 수정
st.title("📟 기사검색")

# 로직 실행: 수집(각각 호출) -> 병합 -> 필터링(OR)
raw_pool = fetch_news_data(inc_words)
final_list = []

for n in raw_pool:
    # 포함: 단어 중 하나라도(OR) 기사에 들어있으면 통과
    pass_inc = True if not inc_words else any(word in n['full_text'] for word in inc_words)
    # 제외: 단어 중 하나라도(OR) 기사에 들어있으면 삭제
    pass_exc = not any(word in n['full_text'] for word in exc_words)
    
    if pass_inc and pass_exc:
        final_list.append(n)

if st.button("🔄 실시간 동기화"):
    st.rerun()

st.write(f"시장 전체 수집: {len(raw_pool)}개 | 필터 통과: {len(final_list)}개")

if final_list:
    for n in final_list:
        st.markdown(f"""
            <div class="news-row">
                <span class="time">{n['time']}</span>
                <a href="{n['link']}" target="_blank" class="title">{n['title']}</a>
            </div>
        """, unsafe_allow_html=True)
else:
    st.warning("검색 결과가 없습니다. (단어 필터를 확인하거나 잠시 후 다시 시도하세요)")

# [5] 하단 출처 표시
st.markdown('<div class="source-footer">출처: 네이버 증권 뉴스, Google News RSS</div>', unsafe_allow_html=True)