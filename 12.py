import ccxt
import pandas as pd
from datetime import datetime
import time
import requests
from statistics import mean
import warnings
warnings.filterwarnings('ignore')

class CryptoArbitrage:
    def __init__(self):
        self.exchanges = self.setup_exchanges()
        
    def setup_exchanges(self):
        """거래소 설정"""
        exchanges = {}
        try:
            exchanges = {
                'upbit': ccxt.upbit({
                    'timeout': 30000,
                    'enableRateLimit': True,
                }),
                'bithumb': ccxt.bithumb({
                    'timeout': 30000,
                    'enableRateLimit': True,
                }),
                'binance': ccxt.binance({
                    'timeout': 30000,
                    'enableRateLimit': True,
                }),
                'kucoin': ccxt.kucoin({
                    'timeout': 30000,
                    'enableRateLimit': True,
                })
            }
            
            # 각 거래소 기본 설정
            for exchange in exchanges.values():
                exchange.load_markets()
                
        except Exception as e:
            print(f"거래소 초기화 중 오류 발생: {str(e)}")
        
        return exchanges

    def get_exchange_rate(self):
        """실시간 환율 조회"""
        try:
            url = "https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD"
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            rate = data[0]['basePrice'] * 1.005  # 매수 환율 적용
            return rate
        except Exception as e:
            print(f"환율 조회 오류: {str(e)}")
            return 1350  # 기본 환율
    
    def get_ticker_price(self, exchange_name, exchange):
        """각 거래소의 티커 가격 조회"""
        try:
            tickers = exchange.fetch_tickers()
            prices = {}
            
            for symbol, ticker in tickers.items():
                if '/USDT' in symbol or '/KRW' in symbol:
                    coin = symbol.split('/')[0]
                    if ticker['last'] and ticker['last'] > 0:
                        prices[coin] = ticker['last']
                        
            return exchange_name, prices
            
        except Exception as e:
            print(f"{exchange_name} 거래소 조회 오류: {str(e)}")
            return exchange_name, {}

    def find_arbitrage(self):
        """차익거래 기회 탐색"""
        try:
            # 환율 조회
            exchange_rate = self.get_exchange_rate()
            print(f"\n현재 환율: {exchange_rate:,.2f} KRW/USD (매수 기준)")
            print("-" * 100)
            
            # 가격 데이터 수집
            exchange_prices = {}
            for name, exchange in self.exchanges.items():
                name, prices = self.get_ticker_price(name, exchange)
                if prices:  # 빈 딕셔너리가 아닐 경우에만 추가
                    exchange_prices[name] = prices
                    
            if len(exchange_prices) < 2:
                print("충분한 거래소 데이터를 가져오지 못했습니다.")
                return []
            
            # 공통 코인 찾기
            common_coins = set.intersection(*[set(prices.keys()) 
                                           for prices in exchange_prices.values()])
            
            opportunities = []
            
            for coin in common_coins:
                prices = {}
                for exchange, price_data in exchange_prices.items():
                    if coin in price_data:
                        price = price_data[coin]
                        # 해외 거래소의 USDT 가격을 KRW로 변환
                        if exchange not in ['upbit', 'bithumb']:
                            price = price * exchange_rate
                        prices[exchange] = price
                
                if len(prices) >= 2:
                    min_price = min(prices.values())
                    max_price = max(prices.values())
                    min_exchange = [k for k, v in prices.items() if v == min_price][0]
                    max_exchange = [k for k, v in prices.items() if v == max_price][0]
                    
                    price_diff = max_price - min_price
                    price_diff_percent = (price_diff / min_price) * 100
                    
                    if price_diff_percent > 1.0:  # 1% 이상 차이나는 경우만 표시
                        opportunities.append({
                            'coin': coin,
                            'buy_exchange': min_exchange,
                            'buy_price': min_price,
                            'sell_exchange': max_exchange,
                            'sell_price': max_price,
                            'difference_krw': price_diff,
                            'difference_percent': price_diff_percent
                        })
            
            opportunities.sort(key=lambda x: x['difference_percent'], reverse=True)
            return opportunities
            
        except Exception as e:
            print(f"차익거래 분석 중 오류 발생: {str(e)}")
            return []

    def display_opportunities(self, opportunities):
        """차익거래 기회 출력"""
        if not opportunities:
            print("현재 유의미한 차익거래 기회가 없습니다.")
            return
        
        df = pd.DataFrame(opportunities)
        
        # 가격 포맷팅
        for col in ['buy_price', 'sell_price', 'difference_krw']:
            df[col] = df[col].apply(lambda x: f"{x:,.0f}")
        df['difference_percent'] = df['difference_percent'].round(2)
        
        # 컬럼명 한글화
        df.columns = ['코인', '매수거래소', '매수가(KRW)', '매도거래소', '매도가(KRW)', 
                     '차익(KRW)', '차익(%)']
        
        print(f"\n차익거래 기회 발견 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n", df.to_string(index=False))

def main():
    print("암호화폐 차익거래 스캐너를 시작합니다...")
    print("종료하려면 Ctrl+C를 누르세요")
    
    scanner = CryptoArbitrage()
    
    try:
        while True:
            print("\n시장 분석 중...")
            opportunities = scanner.find_arbitrage()
            scanner.display_opportunities(opportunities)
            print("\n60초 후 다시 스캔합니다...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    except Exception as e:
        print(f"\n예상치 못한 오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()
