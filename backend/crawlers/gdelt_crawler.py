import requests
import json
import os
import sys
import time

# --- CẤU HÌNH ---
GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def crawl_gdelt_iran_us():
    print("Đang bắt đầu crawl dữ liệu Iran-US (Conflict & Energy) từ GDELT...")

    # Lọc thêm điều kiện chỉ lấy báo tiếng Anh (English)
    query = 'Iran "United States" (Conflict OR Energy OR Oil) sourcelang:eng'
    
    params = {
        "query": query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": "20",
        "timespan": "1week",
        "sort": "date"
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://blog.gdeltproject.org/"
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(GDELT_API_URL, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # KIỂM TRA XEM CÓ PHẢI JSON KHÔNG TRƯỚC KHI PARSE
                try:
                    raw_data = response.json()
                except ValueError:
                    print(f"⚠️ GDELT trả về dữ liệu không hợp lệ (không phải JSON).")
                    print("Nội dung thực tế trả về (500 ký tự đầu):")
                    print("--------------------------------------------------")
                    print(response.text[:500])
                    print("--------------------------------------------------")
                    return

                articles = raw_data.get('articles', [])
                
                if articles:
                    clean_articles = []
                    seen_titles = set()  # Bộ nhớ lưu các tiêu đề đã gặp

                    for art in articles:
                        raw_title = art.get("title")
                        
                        if raw_title:
                            # Chuẩn hóa tiêu đề: viết thường và xóa khoảng trắng dư thừa ở hai đầu
                            normalized_title = raw_title.strip().lower()
                            
                            # Kiểm tra xem tiêu đề này đã từng xuất hiện chưa
                            if normalized_title not in seen_titles:
                                seen_titles.add(normalized_title) # Lưu vào bộ nhớ
                                
                                clean_articles.append({
                                    "title": raw_title, # Vẫn giữ lại tiêu đề gốc (có viết hoa) để lưu file
                                    "date": art.get("seendate"),
                                    "url": art.get("url"),
                                    "source": art.get("sourcecountry"),
                                    "location_context": "Iran/US",
                                    "summary_snippet": art.get("segtok"),
                                    "themes": ["Conflict", "Energy"]
                                })

                    
                    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    save_path = os.path.join(backend_dir, 'data', 'gdelt_iran_us_energy.json')
                    os.makedirs(os.path.dirname(save_path), exist_ok=True)

                    with open(save_path, 'w', encoding='utf-8') as f:
                        json.dump(clean_articles, f, ensure_ascii=False, indent=4)
                    
                    print(f"✅ THÀNH CÔNG! Đã lưu {len(clean_articles)} bài báo vào: {save_path}")
                    return 
                else:
                    print("⚠️ Không tìm thấy bài báo nào phù hợp với từ khóa.")
                    return
            
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 5 
                print(f"⚠️ Server báo bận (429). Đang đợi {wait_time} giây để thử lại (Lần {attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            else:
                print(f"❌ Lỗi kết nối GDELT: HTTP {response.status_code}")
                return

        except requests.exceptions.RequestException as e:
            print(f"❌ Lỗi mạng hoặc Timeout: {e}")
            return
            
    print("❌ Đã thử lại nhiều lần nhưng vẫn thất bại. Vui lòng thử lại sau.")

if __name__ == "__main__":
    crawl_gdelt_iran_us()