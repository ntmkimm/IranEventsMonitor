import requests
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
import email.utils as email_utils

# Ép UTF-8 cho Terminal
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# ============ CẤU HÌNH ============
US_RSS_FEED = "https://travel.state.gov/_res/rss/TAsTWs.xml"

# CHỈ GIỮ 16 NƯỚC NÀY (chữ thường để so sánh)
TARGET_COUNTRIES = [
    'iran', 'israel', 'united states', 'usa', 'america',
    'lebanon', 'syria', 'jordan', 'iraq',
    'palestine', 'gaza', 'west bank',
    'yemen', 'saudi arabia', 'egypt', 'united arab emirates'
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def parse_rfc2822_date(date_string):
    """Parse RFC 2822 date format"""
    try:
        timestamp = email_utils.mktime_tz(email_utils.parsedate_tz(date_string))
        return datetime.fromtimestamp(timestamp)
    except:
        try:
            return datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %Z')
        except:
            try:
                return datetime.strptime(date_string, '%a, %d %b %Y %H:%M:%S %z')
            except:
                return datetime.now()

def is_target_advisory(title, country, description):
    """Kiểm tra xem cảnh báo có thuộc 16 nước mục tiêu không"""
    title_lower = title.lower()
    country_lower = country.lower() if country else ''
    desc_lower = description.lower() if description else ''
    
    # Kiểm tra trực tiếp trong danh sách target
    for target in TARGET_COUNTRIES:
        # Kiểm tra trong country field
        if target in country_lower:
            return True
        # Kiểm tra trong title (thường có dạng "Iran - Level 4...")
        if title_lower.startswith(target) or f" {target} " in title_lower:
            return True
        # Kiểm tra tên nước trong title
        if f"{target} -" in title_lower or f"{target} travel" in title_lower:
            return True
    
    # Từ khóa bổ sung (không dùng để thêm nước mới, chỉ để bắt đúng khu vực)
    keywords = [
        'hezbollah', 'hamas', 'houthi', 'irgc', 'idf',
        'jerusalem', 'tel aviv', 'tehran', 'beirut', 
        'damascus', 'baghdad', 'golan heights'
    ]
    
    for keyword in keywords:
        if keyword in title_lower or keyword in desc_lower:
            return True
    
    return False

def parse_rss(xml_text):
    """Parse RSS feed và trích xuất advisories"""
    advisories = []
    root = ET.fromstring(xml_text)
    items = root.findall('.//item')
    
    print(f"📊 Total items from RSS: {len(items)}")
    
    for item in items:
        # Lấy title
        title_elem = item.find('title')
        title = title_elem.text if title_elem is not None else 'Unknown'
        if title and title.startswith('<![CDATA['):
            title = title[9:-3]
        
        # Lấy description
        desc_elem = item.find('description')
        description = ''
        if desc_elem is not None and desc_elem.text:
            description = desc_elem.text
            if description.startswith('<![CDATA['):
                description = description[9:-3]
            import re
            description = re.sub(r'<[^>]+>', ' ', description)
            description = ' '.join(description.split())
        
        # Lấy link
        link_elem = item.find('link')
        link = link_elem.text if link_elem is not None else '#'
        
        # Lấy pubDate
        pubdate_elem = item.find('pubDate')
        pubdate = datetime.now()
        if pubdate_elem is not None and pubdate_elem.text:
            pubdate = parse_rfc2822_date(pubdate_elem.text)
        
        # Xác định level
        level = 'info'
        if 'Level 4' in title or 'Do Not Travel' in title:
            level = 'do-not-travel'
        elif 'Level 3' in title or 'Reconsider' in title:
            level = 'reconsider'
        elif 'Level 2' in title or 'Exercise Increased Caution' in title:
            level = 'caution'
        
        # Extract country từ title
        country = ''
        if ' - ' in title:
            country = title.split(' - ')[0].strip()
        
        # CHỈ THÊM NẾU THUỘC 16 NƯỚC MỤC TIÊU
        if is_target_advisory(title, country, description):
            # Thêm thông tin thời gian dạng readable
            time_ago = ""
            diff = datetime.now() - pubdate
            if diff.days > 0:
                time_ago = f"{diff.days} days ago"
            elif diff.seconds // 3600 > 0:
                time_ago = f"{diff.seconds // 3600} hours ago"
            elif diff.seconds // 60 > 0:
                time_ago = f"{diff.seconds // 60} minutes ago"
            else:
                time_ago = "Just now"
            
            advisories.append({
                'title': title,
                'description': description[:500] if description else 'No details available',
                'link': link,
                'pubDate': pubdate.isoformat(),
                'timeAgo': time_ago,
                'source': 'U.S. Department of State',
                'sourceCountry': 'US',
                'level': level,
                'country': country
            })
    
    return advisories

def crawl_security_advisories():
    """Crawl và lọc security advisories"""
    print("🛡️ Đang lấy dữ liệu cảnh báo an ninh từ US State Department...")
    
    try:
        response = requests.get(US_RSS_FEED, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return []
        
        advisories = parse_rss(response.content)
        
        # Log chi tiết các nước được giữ lại
        kept_countries = list(set(a['country'] for a in advisories if a['country']))
        print(f"🎯 Đã lọc: {len(advisories)} cảnh báo")
        print(f"📋 Các nước được giữ: {', '.join(kept_countries) if kept_countries else '(không có)'}")
        
        # Thống kê theo level
        stats = {
            'do-not-travel': sum(1 for a in advisories if a['level'] == 'do-not-travel'),
            'reconsider': sum(1 for a in advisories if a['level'] == 'reconsider'),
            'caution': sum(1 for a in advisories if a['level'] == 'caution')
        }
        print(f"📊 Thống kê: DNT={stats['do-not-travel']}, Reconsider={stats['reconsider']}, Caution={stats['caution']}")
        
        # Lưu vào JSON - đặt đúng đường dẫn
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Đi lên 1 cấp để vào thư mục backend, rồi vào data
        backend_dir = os.path.dirname(current_dir)
        save_path = os.path.join(backend_dir, 'data', 'security_advisories.json')
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        result = {
            'fetchedAt': datetime.now().isoformat(),
            'totalCount': len(advisories),
            'source': 'U.S. Department of State - Official RSS',
            'targetCountries': TARGET_COUNTRIES,
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
    print("=" * 60)
    print("🛡️ SECURITY ADVISORIES CRAWLER")
    print("=" * 60)
    crawl_security_advisories()
    print("=" * 60)