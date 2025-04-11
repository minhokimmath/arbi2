import requests
import pandas as pd
from typing import Dict, List
import time

class BybitPriceComparator:
    def __init__(self):
        self.base_url = "https://api.bybit.com"
        
    def get_spot_prices(self) -> Dict[str, float]:
        """현물 시장 가격 조회"""
        endpoint = f"{self.base_url}/v5/market/tickers"
        params = {"category": "spot"}
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            spot_prices = {}
            for item in data["result"]["list"]:
                symbol = item["symbol"]
                price = float(item["lastPrice"])
                spot_prices[symbol] = price
                
            return spot_prices
        except Exception as e:
            print(f"현물 가격 조회 중 오류 발생: {e}")
            return {}

    def get_derivative_prices(self) -> Dict[str, float]:
        """선물 시장 가격 조회"""
        endpoint = f"{self.base_url}/v5/market/tickers"
        params = {"category": "linear"}
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            derivative_prices = {}
            for item in data["result"]["list"]:
                symbol = item["symbol"]
                price = float(item["lastPrice"])
                derivative_prices[symbol] = price
                
            return derivative_prices
        except Exception as e:
            print(f"선물 가격 조회 중 오류 발생: {e}")
            return {}

    def calculate_price_differences(self) -> pd.DataFrame:
        """가격 차이 계산 및 정렬"""
        spot_prices = self.get_spot_prices()
        derivative_prices = self.get_derivative_prices()
        
        price_diffs = []
        
        # 공통 심볼 찾기
        common_symbols = set(spot_prices.keys()) & set(derivative_prices.keys())
        
        for symbol in common_symbols:
            spot_price = spot_prices[symbol]
            derivative_price = derivative_prices[symbol]
            
            # 가격 차이 계산 (퍼센트)
            price_diff_percent = ((derivative_price - spot_price) / spot_price) * 100
            
            price_diffs.append({
                "symbol": symbol,
                "spot_price": spot_price,
                "derivative_price": derivative_price,
                "price_difference": price_diff_percent
            })
        
        # DataFrame 생성 및 정렬
        df = pd.DataFrame(price_diffs)
        df = df.sort_values("price_difference", ascending=False)
        
        return df

def main():
    comparator = BybitPriceComparator()
    
    while True:
        print("\n=== Bybit 현물/선물 가격 차이 비교 ===")
        print("데이터를 가져오는 중...")
        
        df = comparator.calculate_price_differences()
        
        # 상위 10개 결과 출력
        print("\n가격 차이가 큰 순서대로 상위 10개:")
        print(df.head(10).to_string(index=False))
        
        print("\n가격 차이가 작은 순서대로 상위 10개:")
        print(df.tail(10).to_string(index=False))
        
        print("\n60초 후에 다시 업데이트됩니다...")
        time.sleep(60)

if __name__ == "__main__":
    main() 