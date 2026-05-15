import json
import os
from datetime import datetime, timezone
from .base_panel import DataPanel

class GdeltPanel(DataPanel):
    """Panel cho GDELT news (Iran-US Conflict & Energy)"""
    
    def __init__(self):
        super().__init__('GDELT News', '/api/gdelt', self.load_gdelt)
    
    def load_gdelt(self):
        """Load dữ liệu từ file JSON do gdelt_crawler.py tạo ra"""
        try:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'gdelt_iran_us_energy.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Vì crawler lưu trực tiếp 1 list (array), ta bọc lại thành dict
                    # để có cấu trúc tương đồng với SecurityPanel
                    if isinstance(data, list):
                        return {'articles': data, 'totalCount': len(data)}
                    return data
            return {'articles': [], 'totalCount': 0}
        except Exception as e:
            print(f"Error loading GDELT data: {e}")
            return {'articles': [], 'totalCount': 0}

    def parse_gdelt_date(self, date_str):
        """Hỗ trợ parse định dạng seendate của GDELT (YYYYMMDDHHMMSSZ) sang datetime"""
        if not date_str:
            return datetime.now(timezone.utc)
            
        try:
            # Nếu chuỗi có chuẩn ISO (có chữ T)
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                
            # Định dạng GDELT (VD: 20240115083000Z)
            clean_str = date_str.replace('Z', '')
            if len(clean_str) == 14: 
                dt = datetime.strptime(clean_str, '%Y%m%d%H%M%S')
                return dt.replace(tzinfo=timezone.utc)
            
            # Nếu không match bất kỳ chuẩn nào, trả về hiện tại
            return datetime.now(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
            
    def format_time_ago(self, date_str):
        """Tính thời gian đã trôi qua từ seendate"""
        try:
            pubdate = self.parse_gdelt_date(date_str)
            now = datetime.now(timezone.utc)
            diff = now - pubdate
            
            days = diff.days
            hours = diff.seconds // 3600
            minutes = (diff.seconds % 3600) // 60
            
            if days > 0:
                return f"{days} days ago"
            elif hours > 0:
                return f"{hours} hours ago"
            elif minutes > 0:
                return f"{minutes} minutes ago"
            else:
                return "Just now"
        except Exception as e:
            return "Unknown"
    
    def get_articles_for_display(self):
        """Lấy danh sách bài báo đã format cho hiển thị"""
        data = self.load_gdelt()
        articles = data.get('articles', [])
        
        # Format lại thời gian cho mỗi bài báo
        for art in articles:
            art['time_ago'] = self.format_time_ago(art.get('date', ''))
        
        return articles
    
    def get_articles_by_theme(self, theme):
        """Lọc bài báo theo theme (VD: 'Conflict', 'Energy')"""
        articles = self.get_articles_for_display()
        return [a for a in articles if theme.lower() in [t.lower() for t in a.get('themes', [])]]
    
    def get_articles_by_source_country(self, country_code):
        """Lọc bài báo theo quốc gia nguồn (source)"""
        articles = self.get_articles_for_display()
        return [a for a in articles if a.get('source', '').lower() == country_code.lower()]


# Tạo instance để có thể import và sử dụng (giống security_panel)
gdelt_panel = GdeltPanel()