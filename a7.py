'''
python3 -m venv myenv  # Create a virtual environment
source myenv/bin/activate  # Activate the virtual environment
pip install ccxt  # Install ccxt
pip install pandas
pip install python-telegram-bot
pip uninstall telegram  # Uninstall the incorrect package
pip install python-telegram-bot  # Install the correct package
python3 -m venv myenv
source myenv/bin/activate
pip install ccxt pandas python-telegram-bot
python3 a7.py
'''



import ccxt
import pandas as pd
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import warnings
import urllib3
import requests
warnings.filterwarnings('ignore', category=urllib3.exceptions.NotOpenSSLWarning)

def get_exchange_rate():
    """실시간 USD/KRW 환율 조회"""
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD')
        data = response.json()
        return data['rates']['KRW']
    except Exception as e:
        print(f"환율 조회 실패: {str(e)}, 기본값 1300 사용")
        return 1300

def setup_exchanges():
    korean_exchanges = {
        'upbit': ccxt.upbit({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'bithumb': ccxt.bithumb({
            'timeout': 30000,
            'enableRateLimit': True,
        })
    }
    
    foreign_exchanges = {
        'binance': ccxt.binance({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'kucoin': ccxt.kucoin({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'huobi': ccxt.huobi({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'kraken': ccxt.kraken({
            'timeout': 30000,
            'enableRateLimit': True,
        })
    }
    
    return korean_exchanges, foreign_exchanges

def get_tickers(exchange, name):
    try:
        tickers = exchange.fetch_tickers()
        prices = {}
        for symbol, ticker in tickers.items():
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1] if '/' in symbol else None
            
            if quote_currency in ['USDT', 'KRW'] and ticker['last'] is not None and ticker['last'] > 0:
                # 거래량이 있는 경우만 포함
                if ticker['quoteVolume'] and ticker['quoteVolume'] > 0:
                    prices[base_currency] = {
                        'price': ticker['last'],
                        'volume': ticker['quoteVolume'],
                        'currency': quote_currency
                    }
        return name, prices
    except Exception as e:
        print(f"Error fetching {name}: {str(e)}")
        return name, {}

def find_arbitrage_opportunities():
    exchange_rate = get_exchange_rate()
    print(f"현재 환율: 1 USD = {exchange_rate:.2f} KRW")
    
    korean_exchanges, foreign_exchanges = setup_exchanges()
    all_exchanges = {**korean_exchanges, **foreign_exchanges}
    
    with ThreadPoolExecutor(max_workers=len(all_exchanges)) as executor:
        results = list(executor.map(
            lambda x: get_tickers(x[1], x[0]), 
            all_exchanges.items()
        ))
    
    exchange_prices = dict(results)
    
    # 모든 거래소의 코인 목록 수집
    all_coins = set()
    for prices in exchange_prices.values():
        if prices:
            all_coins.update(prices.keys())
    
    arbitrage_opportunities = []
    
    for coin in all_coins:
        korean_prices = {}
        foreign_prices = {}
        
        # 한국 거래소 가격 수집
        for exchange in korean_exchanges.keys():
            if coin in exchange_prices[exchange]:
                price_data = exchange_prices[exchange][coin]
                if price_data['currency'] == 'KRW':
                    price_usd = price_data['price'] / exchange_rate
                    korean_prices[exchange] = {
                        'price_krw': price_data['price'],
                        'price_usd': price_usd,
                        'volume': price_data['volume']
                    }
        
        # 해외 거래소 가격 수집
        for exchange in foreign_exchanges.keys():
            if coin in exchange_prices[exchange]:
                price_data = exchange_prices[exchange][coin]
                if price_data['currency'] == 'USDT':
                    foreign_prices[exchange] = {
                        'price_usd': price_data['price'],
                        'volume': price_data['volume']
                    }
        
        # 차익 계산
        if korean_prices and foreign_prices:
            for k_exchange, k_data in korean_prices.items():
                for f_exchange, f_data in foreign_prices.items():
                    price_diff = f_data['price_usd'] - k_data['price_usd']
                    price_diff_percent = (price_diff / k_data['price_usd']) * 100
                    
                    # 최소 거래량 확인 (예: 1000 USD 이상)
                    if k_data['volume'] > 1000 * exchange_rate and f_data['volume'] > 1000:
                        arbitrage_opportunities.append({
                            'coin': coin,
                            'korean_exchange': k_exchange,
                            'korean_price_krw': k_data['price_krw'],
                            'korean_price_usd': k_data['price_usd'],
                            'korean_volume_krw': k_data['volume'],
                            'foreign_exchange': f_exchange,
                            'foreign_price_usd': f_data['price_usd'],
                            'foreign_volume_usd': f_data['volume'],
                            'difference_percent': price_diff_percent
                        })
    
    # 차익 비율로 정렬
    arbitrage_opportunities.sort(key=lambda x: x['difference_percent'], reverse=True)
    return arbitrage_opportunities

def format_volume(value, currency):
    if currency == 'KRW':
        return f"{value/1000000:.1f}M KRW"
    else:
        return f"{value/1000:.1f}K USD"

def display_opportunities(opportunities):
    if not opportunities:
        print("현재 차익거래 기회가 없습니다.")
        return
    
    df = pd.DataFrame(opportunities)
    
    # 가격 포맷팅
    df['korean_price_krw'] = df['korean_price_krw'].round(2)
    df['korean_price_usd'] = df['korean_price_usd'].round(3)
    df['foreign_price_usd'] = df['foreign_price_usd'].round(3)
    df['difference_percent'] = df['difference_percent'].round(2)
    
    # 거래량 포맷팅
    df['korean_volume'] = df['korean_volume_krw'].apply(lambda x: format_volume(x, 'KRW'))
    df['foreign_volume'] = df['foreign_volume_usd'].apply(lambda x: format_volume(x, 'USD'))
    
    # 표시할 컬럼 선택 및 이름 변경
    display_df = df[[
        'coin', 'korean_exchange', 'korean_price_krw', 'korean_price_usd',
        'korean_volume', 'foreign_exchange', 'foreign_price_usd', 
        'foreign_volume', 'difference_percent'
    ]]
    
    display_df.columns = [
        '코인', '한국거래소', '한국가격(KRW)', '한국가격(USD)', 
        '한국거래량', '해외거래소', '해외가격(USD)', 
        '해외거래량', '차익(%)'
    ]
    
    print(f"\n차익거래 기회 발견 시각: {datetime.now()}")
    print("\n", display_df.to_string(index=False))

def main():
    print("실시간 차익거래 스캐너 시작...")
    print("종료하려면 Ctrl+C를 누르세요")
    
    try:
        while True:
            print("\n차익거래 기회 검색 중...")
            opportunities = find_arbitrage_opportunities()
            display_opportunities(opportunities)
            print("\n30초 후 다시 검색합니다...")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    except Exception as e:
        print(f"\n오류가 발생했습니다: {str(e)}")
        raise






import asyncio
import warnings
from a2 import find_arbitrage_opportunities

from telegram import Bot

# 텔레그램 알림 클래스
class TelegramNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot = Bot(token=bot_token)
        self.chat_id = chat_id

    async def send_message(self, message):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
            print("✅ 메시지가 텔레그램으로 성공적으로 전송되었습니다.")
        except Exception as e:
            print(f"❌ 메시지 전송 실패: {e}")

# 비동기 실행 루프
async def main():
    # 텔레그램 봇 토큰 및 채널 ID
    bot_token = "7726714702:AAFfI_Pm4saqRIXPdGr2IUz6nMsHRfrCEF0"
    chat_id = "-1002431093363"

    notifier = TelegramNotifier(bot_token, chat_id)

    try:
        while True:
            print("\n🔍 차익거래 기회 검색 중...")
            opportunities = find_arbitrage_opportunities()

            if opportunities:
                # 상위 10개와 하위 10개 선택
                top_10 = opportunities[:10]
                bottom_10 = opportunities[-10:]
                selected_opportunities = top_10 + bottom_10

                # 텔레그램 메시지 포맷팅
                messages = []
                message = ""

                for op in selected_opportunities:
                    entry = (
                        f"💰 *코인*: {op['coin']}\n"
                        f"📍 *한국 거래소*: {op['korean_exchange']} (KRW: {op['korean_price_krw']}, USD: {op['korean_price_usd']})\n"
                        f"📍 *해외 거래소*: {op['foreign_exchange']} (USD: {op['foreign_price_usd']})\n"
                        f"📊 *차익*: {op['difference_percent']:.2f}%\n"
                        f"📈 *한국 거래량*: {op['korean_volume_krw']}\n"
                        f"📉 *해외 거래량*: {op['foreign_volume_usd']}\n\n"
                    )
                    
                    if len(message) + len(entry) > 4096:
                        messages.append(message)
                        message = entry
                    else:
                        message += entry

                if message:
                    messages.append(message)

                for msg in messages:
                    await notifier.send_message(f"✨ *차익거래 기회 발견!* ✨\n\n{msg}")
            else:
                await notifier.send_message("현재 차익거래 기회가 없습니다.")

            print("\n⏳ 30초 후 다시 검색합니다...")
            await asyncio.sleep(30)

    except KeyboardInterrupt:
        print("\n프로그램을 종료합니다...")
    except Exception as e:
        print(f"\n오류 발생: {e}")

if __name__ == "__main__":
    warnings.filterwarnings('ignore')
    asyncio.run(main())
