import requests
import pandas as pd
import numpy as np
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor

class CryptoTradingSystem:
    def __init__(self, total_capital=10000):  # USDT 기준
        self.total_capital = total_capital
        
        # 거래소 API 엔드포인트
        self.exchanges = {
            'binance': 'https://api.binance.com/api/v3/ticker/bookTicker',
            'huobi': 'https://api.huobi.pro/market/tickers',
            'kucoin': 'https://api.kucoin.com/api/v1/market/allTickers'
        }
        
        # 코인별 위험 가중치 설정
        self.risk_weights = {
            'BTC/USDT': 0.3,    # 가장 안정적인 자산
            'ETH/USDT': 0.25,   # 두 번째로 안정적
            'BNB/USDT': 0.15,   # 거래소 토큰
            'SOL/USDT': 0.1,    # 신흥 강자
            'XRP/USDT': 0.05,   # 변동성 높음
            'ADA/USDT': 0.05,   # 변동성 높음
            'AVAX/USDT': 0.05,  # 신규 자산
            'DOT/USDT': 0.05    # 신규 자산
        }
        
        self.common_pairs = list(self.risk_weights.keys())
        self.target_daily_return = 0.10  # 10% 일일 목표 수익률
        self.min_profit_threshold = 0.001  # 0.1% 최소 차익거래 임계값

    def get_binance_data(self):
        """바이낸스 데이터 수집"""
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
        """후오비 데이터 수집"""
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
        """쿠코인 데이터 수집"""
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

    def calculate_market_data(self):
        """시장 데이터 수집 및 분석"""
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
                profit_percentage = ((max_bid[1]['bid'] - min_ask[1]['ask']) / min_ask[1]['ask']) * 100
            else:
                min_ask = (None, {'ask': None})
                max_bid = (None, {'bid': None})
                profit_percentage = 0

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
                'Profit %': round(profit_percentage, 2) if profit_percentage > 0 else 0
            })

        return market_data

    def generate_trading_signals(self, market_data):
        """트레이딩 신호 생성"""
        recommendations = []
        
        for data in market_data:
            pair = data['Symbol']
            
            # 최적의 거래소 선정
            exchanges = ['Binance', 'Huobi', 'KuCoin']
            valid_prices = {
                ex: {'bid': data[f'{ex} Bid'], 'ask': data[f'{ex} Ask']}
                for ex in exchanges
                if data[f'{ex} Bid'] is not None and data[f'{ex} Ask'] is not None
            }

            if not valid_prices:
                continue

            best_buy = min(valid_prices.items(), key=lambda x: x[1]['ask'])
            best_sell = max(valid_prices.items(), key=lambda x: x[1]['bid'])
            
            # 수익성 계산
            profit_potential = (best_sell[1]['bid'] - best_buy[1]['ask']) / best_buy[1]['ask']
            
            # 투자 금액 계산
            allocation = self.total_capital * self.risk_weights[pair]
            
            # 매매 신호 결정
            if profit_potential > self.min_profit_threshold:
                action = 'Arbitrage'
            else:
                # 단순 추세 기반 매매 신호
                avg_price = np.mean([v['bid'] for v in valid_prices.values()])
                action = 'Buy' if best_buy[1]['ask'] < avg_price else 'Sell'
            
            recommendations.append({
                'Symbol': pair,
                'Action': action,
                'Buy_Exchange': best_buy[0],
                'Sell_Exchange': best_sell[0],
                'Buy_Price': round(best_buy[1]['ask'], 4),
                'Sell_Price': round(best_sell[1]['bid'], 4),
                'Allocation_USDT': round(allocation, 2),
                'Allocation_Percentage': f"{self.risk_weights[pair]*100}%",
                'Expected_Profit': f"{profit_potential*100:.2f}%"
            })
        
        return recommendations

    def run_strategy(self, interval=10):
        """전략 실행"""
        while True:
            print(f"\n=== 트레이딩 전략 실행 중... === {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                # 시장 데이터 수집
                market_data = self.calculate_market_data()
                
                # 차익거래 정보 출력
                print("\n=== 시장 데이터 ===")
                market_df = pd.DataFrame(market_data)
                print(market_df.to_string(index=False))
                
                # 트레이딩 추천 생성
                recommendations = self.generate_trading_signals(market_data)
                
                # 추천 정보 출력
                print("\n=== 트레이딩 추천 ===")
                rec_df = pd.DataFrame(recommendations)
                print(rec_df.to_string(index=False))
                
                # 예상 수익률 계산
                total_expected_profit = sum([float(r['Expected_Profit'].strip('%'))/100 for r in recommendations])
                print(f"\n예상 일일 수익률: {total_expected_profit*100:.2f}% (목표: {self.target_daily_return*100}%)")
                
            except Exception as e:
                print(f"오류 발생: {e}")
            
            time.sleep(interval)

if __name__ == "__main__":
    # 초기 자본 10,000 USDT로 시스템 시작
    trading_system = CryptoTradingSystem(total_capital=10000)
    trading_system.run_strategy()
