import os
import sys

# 기본 경로 설정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import requests
from bs4 import BeautifulSoup

# [1] 설정
st.set_page_config(page_title="연결 테스트", layout="wide")
st.title("⚡ 네이버 / 다음 연결 상태 확인 (구글 제외)")

# [2] 카운트 함수 (기사 갯수만 체크)
def check_connection_count():
    results = {}
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # -----------------------------------------------------------
    # 1. 네이버 (Naver) 체크
    # -----------------------------------------------------------
    try:
        url = "https://search.naver.com/search.naver?where=news&query=삼성전자&sort=1"
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # 뉴스 덩어리 갯수 세기
            items = soup.select("div.news_wrap")
            results['Naver'] = {'status': '접속 성공', 'count': len(items), 'code': 200}
        else:
            results['Naver'] = {'status': '접속 차단', 'count': 0, 'code': res.status_code}
            
    except Exception as e:
        results['Naver'] = {'status': f'에러: {str(e)}', 'count': 0, 'code': -1}

    # -----------------------------------------------------------
    # 2. 다음 (Daum) 체크
    # -----------------------------------------------------------
    try:
        url = "https://search.daum.net/search?w=news&q=삼성전자&sort=recency"
        res = requests.get(url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, 'html.parser')
            # 뉴스 리스트 갯수 세기
            items = soup.select("ul.list_news > li")
            results['Daum'] = {'status': '접속 성공', 'count': len(items), 'code': 200}
        else:
            results['Daum'] = {'status': '접속 차단', 'count': 0, 'code': res.status_code}
            
    except Exception as e:
        results['Daum'] = {'status': f'에러: {str(e)}', 'count': 0, 'code': -1}

    return results

# [3] 실행 버튼
if st.button("연결 확인 (Click)"):
    with st.spinner('네이버와 다음 서버를 찌르는 중입니다...'):
        data = check_connection_count()
        
        st.write("### 🔍 진단 결과")
        
        # 네이버 결과 출력
        n_res = data['Naver']
        if n_res['count'] > 0:
            st.success(f"✅ [네이버] 정상 (기사 {n_res['count']}개 감지)")
        else:
            st.error(f"❌ [네이버] 실패 (기사 0개) - 상태: {n_res['status']} (코드: {n_res['code']})")
            
        # 다음 결과 출력
        d_res = data['Daum']
        if d_res['count'] > 0:
            st.success(f"✅ [다음] 정상 (기사 {d_res['count']}개 감지)")
        else:
            st.error(f"❌ [다음] 실패 (기사 0개) - 상태: {d_res['status']} (코드: {d_res['code']})")

        st.info("※ 결과가 0개면 서버 IP가 차단된 것이므로, 프로그램 문제보다는 환경 문제입니다.")