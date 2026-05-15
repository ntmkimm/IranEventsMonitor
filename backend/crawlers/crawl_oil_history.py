import requests
import json
import os
from datetime import datetime, timedelta, timezone

SYMBOLS = {
    "BZ=F": "Brent Crude",
    "CL=F": "WTI Crude",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def fetch_historical_prices(symbol, days=30):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    period1 = int(start_date.timestamp())
    period2 = int(end_date.timestamp())
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d"
    
    print(f"  📡 Fetching: {url[:80]}...")
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        print(f"  📊 HTTP Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"  ❌ Lỗi HTTP {response.status_code}")
            return []
        
        data = response.json()
        
        # Kiểm tra cấu trúc response
        if 'chart' not in data:
            print(f"  ❌ No 'chart' in response")
            return []
        
        result = data.get('chart', {}).get('result', [])
        if not result:
            print(f"  ❌ No result in response")
            return []
        
        timestamps = result[0].get('timestamp', [])
        quotes = result[0].get('indicators', {}).get('quote', [{}])[0]
        closes = quotes.get('close', [])
        
        if not timestamps or not closes:
            print(f"  ❌ No timestamp or close data")
            return []
        
        prices = []
        for ts, close in zip(timestamps, closes):
            if close is not None:
                date = datetime.fromtimestamp(ts, tz=timezone.utc)
                prices.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "price": round(close, 2)
                })
        
        # Sắp xếp từ cũ đến mới
        prices.sort(key=lambda x: x["date"])
        print(f"  ✅ {symbol}: {len(prices)} ngày dữ liệu")
        return prices
        
    except Exception as e:
        print(f"  ❌ Lỗi fetch {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return []

def crawl_oil_history(days=30):
    print(f"🛢️ Crawling {days} days oil history...")
    
    all_data = {}
    for symbol, name in SYMBOLS.items():
        print(f"\n📊 {name} ({symbol})...")
        history = fetch_historical_prices(symbol, days)
        all_data[symbol] = {
            "name": name,
            "symbol": symbol,
            "history": history,
            "current_price": history[-1]["price"] if history else None,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
    
    # Lưu vào đúng thư mục data (cạnh backend, không phải trong crawlers)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)  # Lên thư mục backend
    save_path = os.path.join(backend_dir, 'data', 'oil_history.json')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    result = {
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "data": all_data
    }
    
    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    print(f"\n✅ Đã lưu vào: {save_path}")
    
    # Kiểm tra và in thử dữ liệu
    for symbol in SYMBOLS:
        history_count = len(all_data[symbol]["history"])
        print(f"   {SYMBOLS[symbol]}: {history_count} ngày")
        if history_count > 0:
            first = all_data[symbol]["history"][0]
            last = all_data[symbol]["history"][-1]
            print(f"      Từ {first['date']} → {last['date']}")

if __name__ == "__main__":
    crawl_oil_history(30)