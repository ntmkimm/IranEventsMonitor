import json
import os
from datetime import datetime
from .base_panel import DataPanel

class TelegramPanel(DataPanel):
    """Panel cho dữ liệu tin tức từ Telegram Channels"""
    
    def __init__(self):
        # Tên panel, endpoint API giả định, và hàm load dữ liệu
        super().__init__('Telegram Feed', '/api/telegram', self.load_telegram)
    
    def load_telegram(self):
        """Load dữ liệu từ file JSON do Telegram crawler tạo ra"""
        try:
            # Đường dẫn tới file telegram_results.json trong thư mục data
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'telegram_results.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            return {'posts': [], 'total_posts': 0, 'updatedAt': None}
        except Exception as e:
            print(f"Error loading Telegram data: {e}")
            return {'posts': [], 'total_posts': 0, 'updatedAt': None}
    
    def format_time_ago(self, date_str):
        """Tính thời gian đã trôi qua (giống SecurityPanel)"""
        if not date_str:
            return "Unknown"
        try:
            # Xử lý cả định dạng ISO có Z hoặc không có Z
            dt_str = date_str.replace('Z', '+00:00')
            post_date = datetime.fromisoformat(dt_str)
            now = datetime.now(post_date.tzinfo)
            diff = now - post_date
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d ago"
            elif hours > 0:
                return f"{hours}h ago"
            elif minutes > 0:
                return f"{minutes}m ago"
            else:
                return "Just now"
        except:
            return "Recently"

    def get_posts_for_display(self, limit=20):
        """Lấy danh sách post đã format để hiển thị trên UI"""
        data = self.load_telegram()
        posts = data.get('posts', [])
        
        display_posts = []
        for post in posts[:limit]:
            p = post.copy()
            # Thêm thông tin thời gian hiển thị
            p['time_ago'] = self.format_time_ago(post.get('date'))
            
            # Cắt ngắn text nếu quá dài cho preview (tùy chọn)
            content = post.get('text', '')
            if len(content) > 300:
                p['preview_text'] = content[:300] + "..."
            else:
                p['preview_text'] = content
                
            display_posts.append(p)
            
        return display_posts

    def get_posts_by_channel(self, handle):
        """Lọc tin nhắn theo handle của channel (ví dụ: @tanzim_reports)"""
        posts = self.get_posts_for_display(limit=100)
        # Bỏ dấu @ nếu người dùng nhập vào
        clean_handle = handle.replace('@', '').lower()
        return [p for p in posts if p.get('channel_handle', '').lower() == clean_handle]

    def get_posts_by_topic(self, topic):
        """Lọc tin nhắn theo chủ đề (mil, tech, general)"""
        posts = self.get_posts_for_display(limit=100)
        return [p for p in posts if p.get('topic', '').lower() == topic.lower()]

    def search_posts(self, keyword):
        """Tìm kiếm cơ bản trong nội dung tin nhắn"""
        posts = self.get_posts_for_display(limit=200)
        keyword = keyword.lower()
        return [p for p in posts if keyword in p.get('text', '').lower()]

# Tạo instance để sử dụng trong hệ thống
telegram_panel = TelegramPanel()