import asyncio
import warnings
import ccxt
from datetime import datetime
from telegram import Bot
from concurrent.futures import ThreadPoolExecutor

# 1. 거래소 설정 함수

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
        'kraken': ccxt.kraken({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'coinbase': ccxt.coinbase({
            'timeout': 30000,
            'enableRateLimit': True,
        }),
        'kucoin': ccxt.kucoin({
            'timeout': 30000,
            'enableRateLimit': True,
        })
    }
    return korean_exchanges, foreign_exchanges

# 2. 거래소에서 시세 가져오기

def get_tickers(exchange, name):
    try:
        tickers = exchange.fetch_tickers()
        prices = {}
        for symbol, ticker in tickers.items():
            base_currency = symbol.split('/')[0]
            quote_currency = symbol.split('/')[1] if '/' in symbol else None

            if quote_currency in ['USDT', 'KRW'] and ticker['last'] is not None:
                prices[base_currency] = ticker['last']

        return name, prices
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return name, {}

# 3. 차익거래 기회 계산

def find_arbitrage_opportunities():
    korean_exchanges, foreign_exchanges = setup_exchanges()
    all_exchanges = {**korean_exchanges, **foreign_exchanges}

    with ThreadPoolExecutor(max_workers=len(all_exchanges)) as executor:
        results = list(executor.map(
            lambda x: get_tickers(x[1], x[0]),
            all_exchanges.items()
        ))

    exchange_prices = dict(results)
    all_coins = set()
    for prices in exchange_prices.values():
        all_coins.update(prices.keys())

    arbitrage_opportunities = []
    exchange_rate = 1300  # 환율 설정 (예: 1 USD = 1300 KRW)

    for coin in all_coins:
        comparisons = []
        for ex1, prices1 in exchange_prices.items():
            for ex2, prices2 in exchange_prices.items():
                if ex1 != ex2 and coin in prices1 and coin in prices2:
                    price1 = prices1[coin]
                    price2 = prices2[coin]

                    if ex1 in korean_exchanges:
                        price1 /= exchange_rate  # KRW를 USD로 변환
                    if ex2 in korean_exchanges:
                        price2 /= exchange_rate  # KRW를 USD로 변환

                    price_diff = price1 - price2
                    percent_diff = (price_diff / price2) * 100

                    # 비정상적인 차익 제거 (10배 이상의 차익은 무시)
                    if 0 < percent_diff <= 1000:
                        comparisons.append({
                            'coin': coin,
                            'exchange_1': ex1,
                            'price_1': price1,
                            'exchange_2': ex2,
                            'price_2': price2,
                            'difference_percent': percent_diff
                        })

        arbitrage_opportunities.extend(comparisons)

    arbitrage_opportunities.sort(key=lambda x: x['difference_percent'], reverse=True)
    return arbitrage_opportunities[:10] + arbitrage_opportunities[-10:]

# 4. 텔레그램 알림 클래스
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

# 5. 메인 함수
async def main():
    bot_token = "7575520421:AAHRq9OcEa9c1fngS7iBSJ0OIwAAi5leDeA"
    chat_id = "-1002441747357"
    notifier = TelegramNotifier(bot_token, chat_id)

    try:
        while True:
            print("\n🔍 차익거래 기회 검색 중...")
            opportunities = find_arbitrage_opportunities()

            if opportunities:
                message = "\n\n".join([
                    f"💰 *코인*: {op['coin']}\n"
                    f"📍 *거래소 1*: {op['exchange_1']} (가격: {op['price_1']:.2f} USD)\n"
                    f"📍 *거래소 2*: {op['exchange_2']} (가격: {op['price_2']:.2f} USD)\n"
                    f"📊 *차익*: {op['difference_percent']:.2f}%"
                    for op in opportunities
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
