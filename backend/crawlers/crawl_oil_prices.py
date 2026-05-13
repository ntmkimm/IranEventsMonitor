import requests
import json
import os
import sys
from datetime import datetime, timezone

# Ép UTF-8 cho Terminal Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

SYMBOLS = {
    "BZ=F": "Brent Crude",
    "CL=F": "WTI Crude",
}

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://finance.yahoo.com",
}

def crawl_oil_prices():
    print("🛢️ Đang lấy dữ liệu giá dầu từ Yahoo Finance...")
    results = []

    for symbol, name in SYMBOLS.items():
        try:
            url = YAHOO_URL.format(symbol=symbol)
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            if response.status_code == 200:
                body = response.json()
                meta = body["chart"]["result"][0]["meta"]
                
                price = meta["regularMarketPrice"]
                prev_close = meta.get("previousClose") or meta.get("chartPreviousClose") or price
                change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0.0

                results.append({
                    "symbol": symbol,
                    "name": name,
                    "price": round(price, 2),
                    "change_pct": round(change_pct, 3),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                print(f"  ➣ {name}: ${round(price, 2)} ({round(change_pct, 3)}%)")
            else:
                print(f"❌ Lỗi lấy {symbol}, HTTP Status: {response.status_code}")

        except Exception as e:
            print(f"❌ Lỗi kết nối [{symbol}]: {e}")

    # Đường dẫn lưu file thông minh (chung thư mục data với ACLED)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Đi lên 1 cấp để vào thư mục backend, rồi vào data
    backend_dir = os.path.dirname(current_dir)
    save_path = os.path.join(backend_dir, 'data', 'oil_prices.json')
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    
    print(f"✅ THÀNH CÔNG! Đã lưu giá dầu vào: {save_path}")

if __name__ == "__main__":
    crawl_oil_prices()