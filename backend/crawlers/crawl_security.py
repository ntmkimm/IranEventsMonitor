import requests
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import email.utils

# Ép UTF-8 cho Terminal
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ============ CẤU HÌNH ============
US_RSS_FEED = "https://travel.state.gov/_res/rss/TAsTWs.xml"

TARGET_COUNTRIES = [
    'iran', 'israel', 'united states', 'usa', 'america',
    'lebanon', 'syria', 'jordan', 'iraq',
    'palestine', 'gaza', 'west bank',
    'yemen', 'saudi arabia', 'egypt', 'united arab emirates'
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def is_target_advisory(title, country, description):
    title_lower = title.lower()
    country_lower = country.lower() if country else ''
    desc_lower = description.lower() if description else ''
    
    for target in TARGET_COUNTRIES:
        if target in country_lower: return True
        if title_lower.startswith(target) or f" {target} " in title_lower: return True
        if f"{target} -" in title_lower or f"{target} travel" in title_lower: return True
    
    keywords = [
        'hezbollah', 'hamas', 'houthi', 'irgc', 'idf',
        'jerusalem', 'tel aviv', 'tehran', 'beirut', 
        'damascus', 'baghdad', 'golan heights'
    ]
    for keyword in keywords:
        if keyword in title_lower or keyword in desc_lower: return True
    return False

def parse_messy_date(date_string):
    """Hàm chuyên trị các định dạng thời gian thiếu thông tin hoặc sai chuẩn"""
    now_utc = datetime.now(timezone.utc)
    if not date_string:
        return now_utc

    date_string = date_string.strip()

    # Cách 1: Thử đọc theo chuẩn Email đầy đủ (Có giờ, có timezone)
    try:
        dt = email.utils.parsedate_to_datetime(date_string)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Cách 2: Thử đọc theo chuẩn cộc lốc của dữ liệu mẫu bạn gửi (Chỉ có Thứ, Ngày Tháng Năm)
    # Ví dụ: "Mon, 04 May 2026"
    try:
        dt = datetime.strptime(date_string, "%a, %d %b %Y")
        # Không có giờ thì mặc định gán cho nó là 00:00:00 UTC
        return dt.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    
    # Nếu bó tay, trả về giờ hiện tại để không bị sập app
    return now_utc

def parse_rss(xml_text):
    advisories = []
    root = ET.fromstring(xml_text)
    items = root.findall('.//item')
    
    print(f"📊 Total items from RSS: {len(items)}")
    
    now_utc = datetime.now(timezone.utc)
    
    for item in items:
        title_elem = item.find('title')
        title = title_elem.text if title_elem is not None else 'Unknown'
        if title and title.startswith('<![CDATA['): title = title[9:-3]
        
        desc_elem = item.find('description')
        description = ''
        if desc_elem is not None and desc_elem.text:
            description = desc_elem.text
            if description.startswith('<![CDATA['): description = description[9:-3]
            import re
            description = re.sub(r'<[^>]+>', ' ', description)
            description = ' '.join(description.split())
        
        link_elem = item.find('link')
        link = link_elem.text if link_elem is not None else '#'
        
        # ==========================================
        # XỬ LÝ THỜI GIAN
        # ==========================================
        pubdate_elem = item.find('pubDate')
        original_date_str = pubdate_elem.text if pubdate_elem is not None else ""
        
        # Gọi hàm chuyên trị ngày tháng ở trên
        pubdate_utc = parse_messy_date(original_date_str)
        
        # Tính toán chữ "ago"
        diff = now_utc - pubdate_utc
        total_seconds = diff.total_seconds()
        
        # Xử lý trường hợp báo ghi năm ở tương lai (như năm 2026)
        if total_seconds < 0:
            time_ago = "Just updated"
        elif total_seconds < 60:
            time_ago = "Just now"
        elif total_seconds < 3600:
            time_ago = f"{int(total_seconds // 60)}m ago"
        elif total_seconds < 86400:
            time_ago = f"{int(total_seconds // 3600)}h ago"
        elif total_seconds < 2592000: # Dưới 30 ngày -> hiển thị số ngày
            time_ago = f"{int(total_seconds // 86400)}d ago"
        elif total_seconds < 31536000: # Dưới 365 ngày -> hiển thị số tháng
            time_ago = f"{int(total_seconds // 2592000)}mo ago"
        else: # Trên 1 năm -> hiển thị số năm
            time_ago = f"{int(total_seconds // 31536000)}y ago"

        level = 'info'
        if 'Level 4' in title or 'Do Not Travel' in title: level = 'do-not-travel'
        elif 'Level 3' in title or 'Reconsider' in title: level = 'reconsider'
        elif 'Level 2' in title or 'Exercise Increased Caution' in title: level = 'caution'
        
        country = ''
        if ' - ' in title: country = title.split(' - ')[0].strip()
        
        if is_target_advisory(title, country, description):
            advisories.append({
                'title': title,
                'description': description[:500] if description else 'No details available',
                'link': link,
                # Xuất ra chuẩn ISO quốc tế, đảm bảo JS đọc 100% không bị NaN
                'pubDate': pubdate_utc.isoformat(), 
                # Chữ hiển thị Ago (bao gồm tháng, năm hoặc just updated nếu lỗi 2026)
                'timeAgo': time_ago,
                'source': 'U.S. Department of State',
                'sourceCountry': 'US',
                'level': level,
                'country': country
            })
    
    return advisories

def crawl_security_advisories():
    print("🛡️ Đang lấy dữ liệu cảnh báo an ninh từ US State Department...")
    try:
        response = requests.get(US_RSS_FEED, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return []
        
        advisories = parse_rss(response.content)
        
        stats = {
            'do-not-travel': sum(1 for a in advisories if a['level'] == 'do-not-travel'),
            'reconsider': sum(1 for a in advisories if a['level'] == 'reconsider'),
            'caution': sum(1 for a in advisories if a['level'] == 'caution')
        }
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        save_path = os.path.join(backend_dir, 'data', 'security_advisories.json')
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        result = {
            'fetchedAt': datetime.now(timezone.utc).isoformat(),
            'totalCount': len(advisories),
            'source': 'U.S. Department of State - Official RSS',
            'summary': stats,
            'advisories': advisories
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Đã lưu {len(advisories)} cảnh báo vào: {save_path}")
        return advisories
        
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        return []

if __name__ == "__main__":
    crawl_security_advisories()