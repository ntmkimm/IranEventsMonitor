import requests
import json
import os
import sys

# --- CẤU HÌNH ---
ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImp0aSI6IjBlZWY4N2FmOTFmZDI4YmY1OGU4OGIzN2ZkZWFhNDU5OTE5ODI4MmRmZjFkMjhkNWY0NmJmOTM4MDQyZjQ1ZWFjNmY4MjI5NjRlZDFkZjQ3In0.eyJhdWQiOiJhY2xlZCIsImp0aSI6IjBlZWY4N2FmOTFmZDI4YmY1OGU4OGIzN2ZkZWFhNDU5OTE5ODI4MmRmZjFkMjhkNWY0NmJmOTM4MDQyZjQ1ZWFjNmY4MjI5NjRlZDFkZjQ3IiwiaWF0IjoxNzc4NTkxNzU0LCJuYmYiOjE3Nzg1OTE3NTQsImV4cCI6MTc3ODY3ODE1NC44NTM5MDYsInNjb3BlIjpbImF1dGhlbnRpY2F0ZWQiXSwic3ViIjoiMTk1MjAxIiwiaXNzIjoiaHR0cHM6Ly9hY2xlZGRhdGEuY29tLyJ9.JTmc4l2_TWtnkKG_gwJrktldES8nSd4BhWdu0-REHfgDOtPMZOoo9_ZNgcb7IfUGso-IVSTq-zv64GX4TGc3vJzsN-Yu5UNTpTYY4lLwVjhRTAYFbbgngKlezW1HlVuOx-F_wyT5nCi9Isay3hkLnNlMKxEJ1bHUkt8ZMLnpdg_dbRKFo50dXhDeTvNLnMixXQSU0lUIU18RbVhUQn22bbuaDmu_ijqHce2SHOaIy6g3bfME0P4DIr0lhmHdB_LGUAJSjaJGh_rsqUSvbVAFkmGFhUYWvSOiGY45fnRgglSl5m-cy0jH4U8wHCkq9MR-RQWKBamd2sWGxeDWKPWonA" 
EMAIL = "23122003@student.hcmus.edu.vn"

# 2. Ép Python dùng bảng mã UTF-8 khi in log ra màn hình
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def crawl_acled_iran():
    print("Đang bắt đầu crawl dữ liệu Iran từ ACLED (Local)...")
    
    full_url = (
        f"https://acleddata.com/api/acled/read?"
        f"email={EMAIL}&"
        f"country=Iran&"
        f"event_date=2025-04-10&"
        f"event_date_where=>=&"
        f"event_type=Protests|Riots&" 
        f"limit=1000"
    )
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
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