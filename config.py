# Bybit API 설정
TESTNET = True  # 테스트넷 사용 여부

# API 키 설정 (테스트넷)
BYBIT_TEST_API_KEY = "여기에_테스트넷_API_키"
BYBIT_TEST_API_SECRET = "여기에_테스트넷_시크릿_키"

# API 키 설정 (메인넷)
BYBIT_API_KEY = "여기에_메인넷_API_키"
BYBIT_API_SECRET = "여기에_메인넷_시크릿_키"

# 거래 설정
TRADE_SETTINGS = {
    'symbol': 'BTCUSDT',
    'trade_amount': 0.001,  # BTC
    'min_spread': 0.001,    # 0.1%
    'max_spread': 0.01,     # 1%
    'stop_loss': 0.005,     # 0.5%
    'take_profit': 0.002,   # 0.2%
    'leverage': 1,          # 레버리지
    'interval': 1,          # 모니터링 간격 (초)
    'max_position': 0.005,  # 최대 포지션 크기 (BTC)
    'min_volume': 1000,     # 최소 거래량 (USDT)
    'fee': 0.001,          # 거래 수수료 (0.1%)
}

# 알림 설정
NOTIFICATION = {
    'spread_alert': 0.005,  # 스프레드 알림 기준 (0.5%)
    'volume_alert': 5000,   # 거래량 알림 기준 (USDT)
    'profit_alert': 100,    # 수익 알림 기준 (USDT)
}

# 차트 설정
CHART_SETTINGS = {
    'update_interval': 1,   # 차트 업데이트 간격 (초)
    'max_points': 100,      # 차트에 표시할 최대 데이터 포인트
    'ma_periods': [5, 10, 20],  # 이동평균선 기간
}

# 로깅 설정
LOG_SETTINGS = {
    'filename': 'arbitrage.log',
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
} 