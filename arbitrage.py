import logging
import time
import hmac
import hashlib
import json
import requests
import threading
from datetime import datetime, timedelta
from config import BYBIT_TEST_API_KEY, BYBIT_TEST_API_SECRET, TESTNET, TRADE_SETTINGS
import numpy as np
import urllib.parse

class BybitArbitrage:
    def __init__(self):
        # 로거 설정
        self.logger = logging.getLogger('BybitArbitrage')
        self.logger.setLevel(logging.INFO)
        
        # 파일 핸들러 추가
        file_handler = logging.FileHandler('trading.log')
        file_handler.setLevel(logging.INFO)
        
        # 콘솔 핸들러 추가
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 포맷터 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 핸들러 추가
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.api_key = 'aNui4F0MxltwPpDtUV'  # Demo API 키
        self.api_secret = 'SNeDw9q5C7vd12NlhKEoG9mUzbqzqPYtMHtv'  # Demo API Secret
        self.base_url = "https://api-demo.bybit.com"  # Demo Trading API URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
        self.running = False
        self.trade_thread = None
        self.last_prices = {'spot': None, 'futures': None}
        self.trade_stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'total_profit': 0.0,
            'best_trade': 0.0,
            'worst_trade': 0.0
        }
        self.price_history = {
            'spot': [],
            'futures': [],
            'spreads': [],
            'timestamps': []
        }
        self.trade_history = []
        self.market_stats = {
            'volatility': 0,
            'trend': 'neutral',
            'avg_spread': 0,
            'max_spread': 0,
            'min_spread': 0
        }
        self.risk_level = 'low'
        self.last_analysis_time = None

    def _get_signature(self, params):
        """API 서명 생성"""
        try:
            timestamp = str(int(time.time() * 1000))
            
            # 1. 파라미터 준비
            if params is None:
                params = {}
            
            # 2. 필수 파라미터 추가
            params.update({
                'api_key': self.api_key,
                'timestamp': timestamp,
                'recv_window': '5000'
            })
            
            # 3. 파라미터 정렬
            sorted_params = dict(sorted(params.items()))
            
            # 4. 쿼리 문자열 생성
            param_str = '&'.join([f"{key}={sorted_params[key]}" for key in sorted_params])
            
            # 5. HMAC SHA256 서명 생성
            signature = hmac.new(
                bytes(self.api_secret, 'utf-8'),
                param_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            # 6. 서명 추가
            params['sign'] = signature
            
            return timestamp, signature, params
            
        except Exception as e:
            self.logger.error(f"Signature generation error: {str(e)}")
            return None, None, None

    def _request(self, method, endpoint, params=None):
        """API 요청 처리"""
        try:
            timestamp, signature, params = self._get_signature(params)
            if not signature:
                return None
            
            # API 요청 헤더
            headers = {
                'Content-Type': 'application/json'
            }
            
            # URL 생성
            url = f"{self.base_url}{endpoint}"
            
            # GET 요청
            if method.upper() == "GET":
                response = requests.get(url, params=params, headers=headers)
            # POST 요청
            else:
                response = requests.post(url, json=params, headers=headers)
            
            # 응답 확인
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0:
                    return data
                else:
                    self.logger.error(f"API Error: {data.get('retMsg')}")
                    return None
            else:
                self.logger.error(f"HTTP Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Request error: {str(e)}")
            return None

    def test_connection(self):
        """API 연결 테스트"""
        try:
            params = {'accountType': 'UNIFIED'}
            response = self._request("GET", "/v5/account/wallet-balance", params)
            return response is not None
            
        except Exception as e:
            self.logger.error(f"Connection test error: {str(e)}")
            return False

    def get_wallet_balance(self):
        """지갑 잔고 조회"""
        try:
            params = {
                'accountType': 'UNIFIED'  # coin 파라미터 제거
            }
            
            response = self._request("GET", "/v5/account/wallet-balance", params)
            
            if response and 'result' in response:
                balance_data = response['result']
                if 'list' in balance_data and len(balance_data['list']) > 0:
                    wallet = balance_data['list'][0]  # UNIFIED 계정 정보
                    
                    # 전체 USDT 잔고 계산
                    total_balance = float(wallet.get('totalWalletBalance', '0'))
                    # 거래 가능 금액은 전체 잔고의 1%로 설정
                    available_for_trade = total_balance * 0.01
                    
                    return {
                        'total': total_balance,
                        'available': available_for_trade,
                        'leverage': 1  # 레버리지 1배 설정
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Balance check error: {str(e)}")
            return None

    def get_trading_fee(self):
        """거래 수수료 조회"""
        try:
            # 현물 수수료 조회
            spot_params = {
                'category': 'spot',
                'symbol': 'BTCUSDT'
            }
            spot_fee = self._request("GET", "/v5/account/fee-rate", spot_params)
            
            # 선물 수수료 조회
            futures_params = {
                'category': 'linear',
                'symbol': 'BTCUSDT'
            }
            futures_fee = self._request("GET", "/v5/account/fee-rate", futures_params)
            
            if spot_fee and futures_fee:
                return {
                    'spot': {
                        'maker': float(spot_fee['result']['list'][0]['makerFeeRate']),
                        'taker': float(spot_fee['result']['list'][0]['takerFeeRate'])
                    },
                    'futures': {
                        'maker': float(futures_fee['result']['list'][0]['makerFeeRate']),
                        'taker': float(futures_fee['result']['list'][0]['takerFeeRate'])
                    }
                }
            return None
        except Exception as e:
            self.logger.error(f"Fee check error: {str(e)}")
            return None

    def calculate_arbitrage(self, spot_price, futures_price):
        """차익거래 기회 계산"""
        try:
            if not spot_price or not futures_price:
                return None
            
            spread = (futures_price - spot_price) / spot_price * 100
            
            # 거래량 데이터 가져오기
            spot_ticker = self._request("GET", "/v5/market/tickers", {'category': 'spot', 'symbol': 'BTCUSDT'})
            futures_ticker = self._request("GET", "/v5/market/tickers", {'category': 'linear', 'symbol': 'BTCUSDT'})
            
            spot_volume = float(spot_ticker['result']['list'][0]['volume24h']) if spot_ticker else 0
            futures_volume = float(futures_ticker['result']['list'][0]['volume24h']) if futures_ticker else 0
            
            return {
                'spread': spread,
                'spot_price': spot_price,
                'futures_price': futures_price,
                'spot_volume': spot_volume,
                'futures_volume': futures_volume,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            self.logger.error(f"Arbitrage calculation error: {str(e)}")
            return None

    def execute_trade(self, symbol, spot_price, futures_price, amount):
        """실제 거래 실행"""
        try:
            start_time = datetime.now()
            self.logger.info(f"=== Starting Trade Execution ===")
            
            # 스프레드에 따라 거래 방향 결정
            spread = (futures_price - spot_price) / spot_price * 100
            
            # 정확한 수량을 위해 소수점 자릿수 조정
            if symbol == "BTCUSDT":
                amount = round(amount, 3)  # BTC는 3자리
            elif symbol == "ETHUSDT":
                amount = round(amount, 2)  # ETH는 2자리
            else:
                amount = round(amount, 1)  # 기타 코인
            
            self.logger.info(f"Trading {symbol} - Amount: {amount}, Spread: {spread:.3f}%")
            
            if spread > 0:  # 선물이 더 비쌈 -> 현물 매수, 선물 매도
                spot_side = "Buy"
                futures_side = "Sell"
            else:  # 현물이 더 비쌈 -> 현물 매도, 선물 매수
                spot_side = "Sell"
                futures_side = "Buy"
            
            # 현물 주문
            spot_order = self._place_order(
                category="spot",
                symbol=symbol,
                side=spot_side,
                orderType="Market",
                qty=str(amount)
            )
            
            self.logger.info(f"Spot {spot_side} order result: {spot_order}")
            
            # 선물 주문
            futures_order = self._place_order(
                category="linear",
                symbol=symbol,
                side=futures_side,
                orderType="Market",
                qty=str(amount)
            )
            
            self.logger.info(f"Futures {futures_side} order result: {futures_order}")
            
            if spot_order and futures_order:
                trade_result = {
                    'timestamp': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'type': f'{spot_side}-{futures_side}',
                    'amount': amount,
                    'spot_price': spot_price,
                    'futures_price': futures_price,
                    'spread': spread,
                    'profit': 0,  # 실제 수익은 나중에 계산
                    'spot_order_id': spot_order.get('orderId'),
                    'futures_order_id': futures_order.get('orderId')
                }
                
                self.logger.info(f"Trade completed: {trade_result}")
                return trade_result
                
            return None
            
        except Exception as e:
            self.logger.error(f"Trade execution error: {str(e)}")
            return None

    def _place_order(self, category, symbol, side, orderType, qty):
        """주문 실행"""
        try:
            params = {
                'category': category,
                'symbol': symbol,
                'side': side,
                'orderType': orderType,
                'qty': qty
            }
            
            self.logger.info(f"Placing order with params: {params}")
            response = self._request("POST", "/v5/order/create", params)
            self.logger.info(f"Order response: {response}")
            
            if response:
                return response.get('result', {})
            return None
            
        except Exception as e:
            self.logger.error(f"Order placement error: {str(e)}")
            return None

    def _save_trade_history(self, trade_result):
        """거래 기록 저장"""
        try:
            filename = 'trade_history.json'
            
            # 기존 기록 읽기
            try:
                with open(filename, 'r') as f:
                    history = json.load(f)
            except FileNotFoundError:
                history = []
            
            # 새로운 거래 기록 추가
            history.append(trade_result)
            
            # 최근 1000개 거래만 유지
            if len(history) > 1000:
                history = history[-1000:]
            
            # 파일 저장
            with open(filename, 'w') as f:
                json.dump(history, f, indent=2)
            
        except Exception as e:
            self.logger.error(f"Failed to save trade history: {str(e)}")

    def start_trading(self):
        """거래 시작"""
        if self.running:
            return False
            
        self.running = True
        self.trade_thread = threading.Thread(target=self._trading_loop)
        self.trade_thread.start()
        return True

    def _trading_loop(self):
        """거래 루프"""
        while self.running:
            try:
                # 잔고 확인
                balance = self.get_wallet_balance()
                if balance:
                    self.logger.info(f"현재 잔고: {balance['total']} USDT")

                # 가격 정보 수집
                spot_price = self.get_market_price("BTCUSDT", "spot")
                futures_price = self.get_market_price("BTCUSDT", "linear")
                
                # 차익거래 기회 분석
                if spot_price and futures_price:
                    arb_data = self.calculate_arbitrage(spot_price, futures_price)
                    if arb_data:
                        self.logger.info(f"스프레드: {arb_data['spread']:.2f}%")
                        if abs(arb_data['spread']) > TRADE_SETTINGS['min_spread']:
                            self.execute_trade("BTCUSDT", spot_price, futures_price, arb_data['spot_volume'])

                time.sleep(TRADE_SETTINGS['interval'])
                
            except Exception as e:
                self.logger.error(f"거래 중 오류: {str(e)}")
                time.sleep(1)

    def stop_trading(self):
        """거래 중지"""
        self.running = False
        if self.trade_thread:
            self.trade_thread.join()
        self.logger.info("거래 중지")
        self.logger.info(f"거래 통계: {json.dumps(self.trade_stats, indent=2)}")

    def analyze_market(self):
        """시장 분석"""
        try:
            if len(self.price_history['spreads']) > 10:
                spreads = np.array(self.price_history['spreads'])
                
                # 변동성 계산
                volatility = np.std(spreads)
                
                # 추세 분석
                ma5 = np.mean(spreads[-5:])
                ma10 = np.mean(spreads[-10:])
                trend = 'up' if ma5 > ma10 else 'down'
                
                # 거래량 분석
                spot_volume = self.price_history.get('spot_volume', [])
                futures_volume = self.price_history.get('futures_volume', [])
                
                volume_trend = 'increasing' if (len(spot_volume) > 1 and 
                    spot_volume[-1] > spot_volume[-2]) else 'decreasing'
                
                return {
                    'volatility': volatility,
                    'trend': trend,
                    'volume_trend': volume_trend,
                    'avg_spread': np.mean(spreads),
                    'max_spread': np.max(spreads),
                    'min_spread': np.min(spreads),
                    'current_risk': self.calculate_risk_level(volatility)
                }
            return None
        except Exception as e:
            self.logger.error(f"Market analysis error: {str(e)}")
            return None

    def calculate_risk_level(self, volatility):
        """리스크 레벨 계산"""
        if volatility > 0.5:
            return 'high'
        elif volatility > 0.2:
            return 'medium'
        return 'low'

    def calculate_optimal_amount(self, spread):
        """최적 거래 수량 계산"""
        try:
            base_amount = float(TRADE_SETTINGS['trade_amount'])
            
            # 리스크 레벨에 따른 조정
            risk_multiplier = {
                'low': 1.0,
                'medium': 0.7,
                'high': 0.5
            }.get(self.risk_level, 0.5)
            
            # 스프레드 크기에 따른 조정
            spread_multiplier = min(abs(spread) / TRADE_SETTINGS['min_spread'], 2.0)
            
            return base_amount * risk_multiplier * spread_multiplier
        except Exception as e:
            self.logger.error(f"거래 수량 계산 오류: {str(e)}")
            return base_amount

    def update_price_history(self, spot_price, futures_price, spread):
        """가격 히스토리 업데이트"""
        try:
            now = datetime.now()
            self.price_history['spot'].append(spot_price)
            self.price_history['futures'].append(futures_price)
            self.price_history['spreads'].append(spread)
            self.price_history['timestamps'].append(now)
            
            # 24시간 데이터만 유지
            cutoff_time = now - timedelta(hours=24)
            while self.price_history['timestamps'] and self.price_history['timestamps'][0] < cutoff_time:
                for key in self.price_history:
                    if self.price_history[key]:
                        self.price_history[key].pop(0)
                        
            # 주기적 시장 분석
            if (not self.last_analysis_time or 
                now - self.last_analysis_time > timedelta(minutes=5)):
                self.analyze_market()
                self.last_analysis_time = now
                
        except Exception as e:
            self.logger.error(f"가격 히스토리 업데이트 오류: {str(e)}")

    def add_trade_history(self, trade_data):
        """거래 히스토리 추가"""
        try:
            self.trade_history.append({
                'timestamp': datetime.now(),
                'type': trade_data['type'],
                'amount': trade_data['amount'],
                'spot_price': trade_data['spot_price'],
                'futures_price': trade_data['futures_price'],
                'spread': trade_data['spread'],
                'profit': trade_data['profit'],
                'risk_level': self.risk_level
            })
            
            # 최근 100개 거래만 유지
            if len(self.trade_history) > 100:
                self.trade_history.pop(0)
                
        except Exception as e:
            self.logger.error(f"거래 히스토리 추가 오류: {str(e)}")

    def get_trading_summary(self):
        """거래 요약 정보"""
        try:
            if not self.trade_history:
                return None
                
            recent_trades = self.trade_history[-20:]  # 최근 20개 거래
            
            return {
                'total_profit': sum(t['profit'] for t in recent_trades),
                'avg_spread': np.mean([t['spread'] for t in recent_trades]),
                'win_rate': len([t for t in recent_trades if t['profit'] > 0]) / len(recent_trades),
                'risk_level': self.risk_level,
                'market_trend': self.market_stats['trend'],
                'volatility': self.market_stats['volatility']
            }
            
        except Exception as e:
            self.logger.error(f"거래 요약 생성 오류: {str(e)}")
            return None

    def get_market_price(self, symbol, category):
        """현재 시장 가격 조회"""
        try:
            params = {
                'category': category,
                'symbol': symbol
            }
            
            response = self._request("GET", "/v5/market/tickers", params)
            if response and 'result' in response and 'list' in response['result']:
                ticker = response['result']['list'][0]
                return float(ticker['lastPrice'])
                
            return None
            
        except Exception as e:
            self.logger.error(f"Price check error: {str(e)}")
            return None

    def update_trade_stats(self, trade_result):
        """거래 통계 업데이트"""
        try:
            self.trade_stats['total_trades'] += 1
            if trade_result['profit'] > 0:
                self.trade_stats['successful_trades'] += 1
            
            self.trade_stats['total_profit'] += trade_result['profit']
            self.trade_stats['best_trade'] = max(self.trade_stats['best_trade'], 
                                               trade_result['profit'])
            self.trade_stats['worst_trade'] = min(self.trade_stats['worst_trade'], 
                                                trade_result['profit'])
            
            # 거래 기록 저장
            self.trade_history.append({
                'timestamp': datetime.now(),
                'type': trade_result['type'],
                'spread': trade_result['spread'],
                'profit': trade_result['profit'],
                'risk_level': self.risk_level
            })
            
            # 최근 100개 거래만 유지
            if len(self.trade_history) > 100:
                self.trade_history.pop(0)
                
        except Exception as e:
            self.logger.error(f"Trade stats update error: {str(e)}")

if __name__ == "__main__":
    try:
        # BybitArbitrage 인스턴스 생성
        arbitrage_bot = BybitArbitrage()
        
        # 거래 시작
        arbitrage_bot.start_trading()
        
        # 프로그램이 계속 실행되도록 유지
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n프로그램 종료 중...")
        if arbitrage_bot:
            arbitrage_bot.stop_trading()
        print("프로그램이 종료되었습니다.")