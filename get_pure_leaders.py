# 파일명: D:\090_pgm\pgm\eod_target\get_pure_leaders.py
# 실행파일명: C:\Users\user\AppData\Local\Programs\Python\Python311\python.exe D:\090_pgm\pgm\eod_target\get_pure_leaders.py

import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime
import os

def get_market_leaders_final(top_n=200, min_amount_billion=500):
    try:
        # 1. 시작 시간 기록 및 출력
        start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"시작 시간: {start_time}")
        
        # 2. 데이터 수집
        df = fdr.StockListing('KRX')
        
        # 3. 컬럼명 매핑 (상무님 환경 대응)
        col_map = {
            '등락률': ['ChagesRatio', 'ChangesRatio', 'ChgRate', 'ChangeRate', '등락률'],
            '종목명': ['Name', '종목명'],
            '거래대금': ['Amount', '거래대금'],
            '종목코드': ['Code', 'ISU_CD', '종목코드'],
            '현재가': ['Close', '현재가', '종가']
        }
        
        final_cols = {}
        for key, candidates in col_map.items():
            for cand in candidates:
                if cand in df.columns:
                    final_cols[key] = cand
                    break
        
        # 4. 데이터 전처리 및 엄격한 필터링 (거래대금 500억 이상)
        df['거래대금_억'] = df[final_cols['거래대금']] / 100_000_000
        filtered = df[(df[final_cols['등락률']] > 0) & (df['거래대금_억'] >= min_amount_billion)].copy()
        
        # 등락률 기준 내림차순 정렬
        sorted_df = filtered.sort_values(by=final_cols['등락률'], ascending=False)
        
        # 5. 결과 추출
        leaders = sorted_df[[final_cols['종목코드'], final_cols['종목명'], final_cols['현재가'], final_cols['등락률'], '거래대금_억']].head(top_n)
        leaders.columns = ['종목코드', '종목명', '현재가', '등락률', '거래대금_억']
        
        # 6. 지정된 데이터 디렉토리에 저장
        save_path = r"D:\090_pgm\pgm\eod_target\data"
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
        today_str = datetime.now().strftime('%Y%m%d')
        file_full_path = os.path.join(save_path, f"PureLeaders_{today_str}.csv")
        leaders.to_csv(file_full_path, index=False, encoding='utf-8-sig')
        
        # 7. 종료 시간 기록 및 추출 건수 출력
        end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"종료 시간: {end_time}")
        print(f"{len(leaders)}건 추출 완료")
        
        return leaders

    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        return None

if __name__ == "__main__":
    # 거래대금 500억 필터로 실행
    get_market_leaders_final(top_n=200, min_amount_billion=500)