import ccxt
import pandas as pd
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor
import warnings
import urllib3
warnings.filterwarnings('ignore', category=urllib3.exceptions.NotOpenSSLWarning)

def setup_exchanges():
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
    return exchanges

def get_tickers(exchange, name):
    try:
        tickers = exchange.fetch_tickers()
        prices = {}
        for symbol, ticker in tickers.items():
            if '/USDT' in symbol or '/KRW' in symbol:
                coin = symbol.split('/')[0]
                if ticker['last'] is not None:  # None 값 필터링
                    prices[coin] = ticker['last']
        return name, prices
    except Exception as e:
        print(f"Error fetching {name}: {str(e)}")
        return name, {}

def find_arbitrage_opportunities():
    exchanges = setup_exchanges()
    
    # 병렬로 데이터 수집
    with ThreadPoolExecutor(max_workers=len(exchanges)) as executor:
        results = list(executor.map(
            lambda x: get_tickers(x[1], x[0]), 
            exchanges.items()
        ))
    
    # 결과를 딕셔너리로 변환
    exchange_prices = dict(results)
    
    # 모든 거래소에 공통으로 있는 코인 찾기
    common_coins = set.intersection(*[set(prices.keys()) 
                                    for prices in exchange_prices.values() 
                                    if prices])
    
    arbitrage_opportunities = []
    
    for coin in common_coins:
        prices = {}
        for exchange, price_data in exchange_prices.items():
            if coin in price_data and price_data[coin] > 0:  # 0보다 큰 가격만 포함
                # KRW 가격을 USD로 변환 (예시 환율: 1300원)
                price = price_data[coin]
                if exchange in ['upbit', 'bithumb']:
                    price = price / 1300
                prices[exchange] = price
        
        if len(prices) >= 2:
            min_price = min(prices.values())
            max_price = max(prices.values())
            min_exchange = [k for k, v in prices.items() if v == min_price][0]
            max_exchange = [k for k, v in prices.items() if v == max_price][0]
            
            price_diff = max_price - min_price
            price_diff_percent = (price_diff / min_price) * 100
            
            if price_diff_percent > 0.5:  # 0.5% 이상의 차이만 표시
                arbitrage_opportunities.append({
                    'coin': coin,
                    'buy_exchange': min_exchange,
                    'buy_price': min_price,
                    'sell_exchange': max_exchange,
                    'sell_price': max_price,
                    'difference_usd': price_diff,
                    'difference_percent': price_diff_percent
                })
    
    # 퍼센트 차이로 정렬
    arbitrage_opportunities.sort(key=lambda x: x['difference_percent'], reverse=True)
    return arbitrage_opportunities

def display_opportunities(opportunities):
    if not opportunities:
        print("No significant arbitrage opportunities found.")
        return
    
    df = pd.DataFrame(opportunities)
    df['buy_price'] = df['buy_price'].round(4)
    df['sell_price'] = df['sell_price'].round(4)
    df['difference_usd'] = df['difference_usd'].round(4)
    df['difference_percent'] = df['difference_percent'].round(2)
    
    print(f"\nArbitrage Opportunities Found at {datetime.now()}")
    print("\n", df.to_string(index=False))

def main():
    print("Starting arbitrage scanner...")
    print("Press Ctrl+C to exit")
    
    try:
        while True:
            print("\nScanning for arbitrage opportunities...")
            opportunities = find_arbitrage_opportunities()
            display_opportunities(opportunities)
            print("\nWaiting 60 seconds before next scan...")
            time.sleep(60)  # 1분마다 업데이트
    except KeyboardInterrupt:
        print("\nExiting program...")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
