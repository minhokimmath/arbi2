import ccxt
import pandas as pd
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import warnings
import urllib3
import requests
warnings.filterwarnings('ignore', category=urllib3.exceptions.NotOpenSSLWarning)

def setup_exchanges():
    """해외 거래소 설정"""
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
        }),
        'bitfinex': ccxt.bitfinex({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'okx': ccxt.okx({
            'timeout': 30000,
            'enableRateLimit': True,
        })
    }
    return foreign_exchanges

def get_tickers(exchange, name):
    """거래소의 모든 티커 정보 가져오기"""
    try:
        tickers = exchange.fetch_tickers()
        prices = {}
        for symbol, ticker in tickers.items():
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1] if '/' in symbol else None

            if quote_currency == 'USDT' and ticker['last'] is not None and ticker['last'] > 0:
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
    """해외 거래소 간 차익 거래 기회 탐색"""
    foreign_exchanges = setup_exchanges()

    with ThreadPoolExecutor(max_workers=len(foreign_exchanges)) as executor:
        results = list(executor.map(
            lambda x: get_tickers(x[1], x[0]), 
            foreign_exchanges.items()
        ))

    exchange_prices = dict(results)

    # 모든 거래소의 코인 목록 수집
    all_coins = set()
    for prices in exchange_prices.values():
        if prices:
            all_coins.update(prices.keys())

    arbitrage_opportunities = []

    for coin in all_coins:
        exchange_data = {}

        # 거래소 가격 수집
        for exchange, prices in exchange_prices.items():
            if coin in prices:
                price_data = prices[coin]
                if price_data['currency'] == 'USDT':
                    exchange_data[exchange] = {
                        'price_usd': price_data['price'],
                        'volume': price_data['volume']
                    }

        # 차익 계산
        exchanges = list(exchange_data.keys())
        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                ex1, ex2 = exchanges[i], exchanges[j]
                data1, data2 = exchange_data[ex1], exchange_data[ex2]

                price_diff = abs(data1['price_usd'] - data2['price_usd'])
                price_diff_percent = (price_diff / min(data1['price_usd'], data2['price_usd'])) * 100

                # 최소 거래량 확인 (예: 1000 USDT 이상)
                if data1['volume'] > 1000 and data2['volume'] > 1000:
                    arbitrage_opportunities.append({
                        'coin': coin,
                        'exchange_1': ex1,
                        'price_1': data1['price_usd'],
                        'volume_1': data1['volume'],
                        'exchange_2': ex2,
                        'price_2': data2['price_usd'],
                        'volume_2': data2['volume'],
                        'difference_percent': price_diff_percent
                    })

    # 차익 비율로 정렬
    arbitrage_opportunities.sort(key=lambda x: x['difference_percent'], reverse=True)
    return arbitrage_opportunities

def format_volume(value):
    return f"{value/1000:.1f}K USDT"

def display_opportunities(opportunities):
    """차익 거래 기회 출력"""
    if not opportunities:
        print("현재 차익거래 기회가 없습니다.")
        return

    df = pd.DataFrame(opportunities)

    # 가격 포맷팅
    df['price_1'] = df['price_1'].round(3)
    df['price_2'] = df['price_2'].round(3)
    df['difference_percent'] = df['difference_percent'].round(2)

    # 거래량 포맷팅
    df['volume_1'] = df['volume_1'].apply(format_volume)
    df['volume_2'] = df['volume_2'].apply(format_volume)

    # 표시할 컬럼 선택 및 이름 변경
    display_df = df[[
        'coin', 'exchange_1', 'price_1', 'volume_1',
        'exchange_2', 'price_2', 'volume_2', 'difference_percent'
    ]]

    display_df.columns = [
        '코인', '거래소 1', '가격 1 (USD)', '거래량 1',
        '거래소 2', '가격 2 (USD)', '거래량 2', '차익 (%)'
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
                # 텔레그램 메시지 포맷팅
                message = "\n\n".join([
                    f"💰 *코인*: {op['coin']}\n"
                    f"📍 *한국 거래소*: {op['korean_exchange']} (KRW: {op['korean_price_krw']}, USD: {op['korean_price_usd']})\n"
                    f"📍 *해외 거래소*: {op['foreign_exchange']} (USD: {op['foreign_price_usd']})\n"
                    f"📊 *차익*: {op['difference_percent']:.2f}%\n"
                    f"📈 *한국 거래량*: {op['korean_volume_krw']}\n"
                    f"📉 *해외 거래량*: {op['foreign_volume_usd']}"
                    for op in opportunities[:5]  # 상위 5개만 전송
                ])

                await notifier.send_message(f"✨ *차익거래 기회 발견!* ✨\n\n{message}")
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
