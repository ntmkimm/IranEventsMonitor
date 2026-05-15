import requests
import json
import os
import sys

from dotenv import load_dotenv

# Load cấu hình từ file .env hiện tại
load_dotenv()

# --- CẤU HÌNH ---
ACLED_ACCESS_TOKEN = os.environ.get('ACLED_ACCESS_TOKEN', '')
ACLED_EMAIL = os.environ.get('ACLED_EMAIL', '')

# 2. Ép Python dùng bảng mã UTF-8 khi in log ra màn hình
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def crawl_acled_iran():
    print("Đang bắt đầu crawl dữ liệu Iran từ ACLED (Local)...")
    
    full_url = (
        f"https://acleddata.com/api/acled/read?"
        f"email={ACLED_EMAIL}&"
        f"country=Iran&"
        f"event_date=2025-04-10&"
        f"event_date_where=>=&"
        f"event_type=Protests|Riots&" 
        f"limit=1000"
    )
    
    headers = {
        "Authorization": f"Bearer {ACLED_ACCESS_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        response = requests.get(full_url, headers=headers)
        
        if response.status_code == 200:
            raw_data = response.json()
            events = raw_data.get('data', [])
            
            if events:
                clean_events = []
                for ev in events:
                    clean_events.append({
                        "id": ev.get("event_id_cnty"),
                        "date": ev.get("event_date"),
                        "type": ev.get("event_type"),
                        "location": ev.get("location"),
                        "lat": float(ev.get("latitude")),
                        "lng": float(ev.get("longitude")),
                        "notes": ev.get("notes")
                    })

                # --- ĐƯỜNG DẪN TƯƠNG ĐỐI THÔNG MINH (BẢN CHUẨN) ---
                # 1. Lấy thư mục chứa file Python này đang đứng (tức là thư mục backend/crawlers)
                current_dir = os.path.dirname(os.path.abspath(__file__))
                # Đi lên 1 cấp để vào thư mục backend, rồi vào data
                backend_dir = os.path.dirname(current_dir)
                
                # 2. Đi thẳng vào thư mục data nằm ngay cạnh nó
                save_path = os.path.join(backend_dir, 'data', 'iran_protests_clean.json')
                
                # Đảm bảo thư mục tồn tại trước khi lưu
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(clean_events, f, ensure_ascii=False, indent=4)
                
                print(f"✅ THÀNH CÔNG! Đã lưu {len(clean_events)} sự kiện vào: {save_path}")
            else:
                print("⚠️ Vẫn rỗng. Nội dung server trả về:")
                print(raw_data) 
        else:
            print(f"❌ Lỗi {response.status_code}")

    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    crawl_acled_iran()