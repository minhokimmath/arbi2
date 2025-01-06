import requests
import pandas as pd
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor

class ArbitrageScanner:
    def __init__(self):
        self.exchanges = {
            'binance': 'https://api.binance.com/api/v3/ticker/bookTicker',
            'huobi': 'https://api.huobi.pro/market/tickers',
            'kucoin': 'https://api.kucoin.com/api/v1/market/allTickers'
        }
        
        # 거래소별 수수료 (maker 기준)
        self.fees = {
            'Binance': 0.001,  # 0.1%
            'Huobi': 0.002,    # 0.2%
            'KuCoin': 0.001    # 0.1%
        }
        
        self.common_pairs = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT',
            'SOL/USDT', 'ADA/USDT', 'AVAX/USDT', 'DOT/USDT'
        ]

    def get_binance_data(self):
        try:
            response = requests.get(self.exchanges['binance'])
            data = response.json()
            prices = {}
            for item in data:
                symbol = item['symbol']
                if 'USDT' in symbol:
                    base_symbol = symbol.replace('USDT', '')
                    pair = f"{base_symbol}/USDT"
                    if pair in self.common_pairs:
                        prices[pair] = {
                            'bid': float(item['bidPrice']),
                            'ask': float(item['askPrice']),
                            'bidQty': float(item['bidQty']),
                            'askQty': float(item['askQty'])
                        }
            return prices
        except Exception as e:
            print(f"Binance API 오류: {e}")
            return {}

    def get_huobi_data(self):
        try:
            response = requests.get(self.exchanges['huobi'])
            data = response.json()['data']
            prices = {}
            for item in data:
                symbol = item['symbol'].upper()
                if 'USDT' in symbol:
                    base_symbol = symbol.replace('USDT', '')
                    pair = f"{base_symbol}/USDT"
                    if pair in self.common_pairs:
                        prices[pair] = {
                            'bid': float(item['bid']),
                            'ask': float(item['ask']),
                            'bidQty': float(item['bidSize']),
                            'askQty': float(item['askSize'])
                        }
            return prices
        except Exception as e:
            print(f"Huobi API 오류: {e}")
            return {}

    def get_kucoin_data(self):
        try:
            response = requests.get(self.exchanges['kucoin'])
            data = response.json()['data']['ticker']
            prices = {}
            for item in data:
                symbol = item['symbol']
                if 'USDT' in symbol:
                    pair = symbol.replace('-', '/')
                    if pair in self.common_pairs:
                        bid = item.get('buy')
                        ask = item.get('sell')
                        vol = item.get('vol', '0')
                        
                        if bid is not None and ask is not None:
                            prices[pair] = {
                                'bid': float(bid),
                                'ask': float(ask),
                                'bidQty': float(vol),
                                'askQty': float(vol)
                            }
            return prices
        except Exception as e:
            print(f"KuCoin API 오류: {e}")
            return {}

    def calculate_arbitrage(self):
        with ThreadPoolExecutor() as executor:
            binance_future = executor.submit(self.get_binance_data)
            huobi_future = executor.submit(self.get_huobi_data)
            kucoin_future = executor.submit(self.get_kucoin_data)

        binance_data = binance_future.result()
        huobi_data = huobi_future.result()
        kucoin_data = kucoin_future.result()

        market_data = []

        for pair in self.common_pairs:
            prices = {
                'Binance': binance_data.get(pair, {'bid': None, 'ask': None, 'bidQty': None}),
                'Huobi': huobi_data.get(pair, {'bid': None, 'ask': None, 'bidQty': None}),
                'KuCoin': kucoin_data.get(pair, {'bid': None, 'ask': None, 'bidQty': None})
            }

            valid_prices = {k: v for k, v in prices.items() if v['bid'] is not None and v['ask'] is not None}
            
            if valid_prices:
                min_ask = min(valid_prices.items(), key=lambda x: x[1]['ask'])
                max_bid = max(valid_prices.items(), key=lambda x: x[1]['bid'])
                
                # 수수료를 고려한 실제 수익률 계산
                buy_fee = self.fees[min_ask[0]]
                sell_fee = self.fees[max_bid[0]]
                
                buy_price = min_ask[1]['ask'] * (1 + buy_fee)
                sell_price = max_bid[1]['bid'] * (1 - sell_fee)
                
                profit_percentage = ((sell_price - buy_price) / buy_price) * 100
                
                # 거래 시그널 생성
                if profit_percentage > 0:
                    action = f"매수: {min_ask[0]}에서 {min_ask[1]['ask']} 매수\n매도: {max_bid[0]}에서 {max_bid[1]['bid']} 매도\n" \
                            f"예상 순이익: {profit_percentage:.4f}% (수수료 포함)"
                else:
                    action = "차익거래 기회 없음"
            else:
                min_ask = (None, {'ask': None})
                max_bid = (None, {'bid': None})
                profit_percentage = 0
                action = "데이터 부족"

            market_data.append({
                'Symbol': pair,
                'Binance Bid': prices['Binance']['bid'],
                'Binance Ask': prices['Binance']['ask'],
                'Huobi Bid': prices['Huobi']['bid'],
                'Huobi Ask': prices['Huobi']['ask'],
                'KuCoin Bid': prices['KuCoin']['bid'],
                'KuCoin Ask': prices['KuCoin']['ask'],
                'Best Buy': f"{min_ask[0]} ({min_ask[1]['ask']})" if min_ask[0] else "N/A",
                'Best Sell': f"{max_bid[0]} ({max_bid[1]['bid']})" if max_bid[0] else "N/A",
                'Profit %': round(profit_percentage, 4),
                'Action': action
            })

        return market_data

    def run_scanner(self, interval=5):
        while True:
            print("\n=== 실시간 차익거래 스캐너 ===")
            print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("* 모든 수익률은 거래소 수수료를 포함한 순이익입니다 *")
            
            market_data = self.calculate_arbitrage()
            df = pd.DataFrame(market_data)
            
            # 수익률 기준으로 정렬
            df = df.sort_values('Profit %', ascending=False)
            
            # 출력 설정
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            pd.set_option('display.max_rows', None)
            print(df.to_string(index=False))
            
            time.sleep(interval)

if __name__ == "__main__":
    scanner = ArbitrageScanner()
    scanner.run_scanner()
