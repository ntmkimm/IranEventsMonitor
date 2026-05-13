import json
import os
from datetime import datetime
from .base_panel import DataPanel

class SecurityPanel(DataPanel):
    """Panel cho security advisories"""
    
    def __init__(self):
        super().__init__('Security Advisories', '/api/security', self.load_security)
    
    def load_security(self):
        """Load dữ liệu từ file JSON"""
        try:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'security_advisories.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            return {'advisories': [], 'totalCount': 0}
        except Exception as e:
            print(f"Error loading security data: {e}")
            return {'advisories': [], 'totalCount': 0}
    
    def format_time_ago(self, pubdate_str):
        """Tính thời gian đã trôi qua từ pubDate"""
        try:
            pubdate = datetime.fromisoformat(pubdate_str.replace('Z', '+00:00'))
            now = datetime.now(pubdate.tzinfo)
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
        except:
            return "Unknown"
    
    def get_advisories_for_display(self):
        """Lấy danh sách advisory đã format cho hiển thị"""
        data = self.load_security()
        advisories = data.get('advisories', [])
        
        # Format lại thời gian cho mỗi advisory
        for adv in advisories:
            adv['time_ago'] = self.format_time_ago(adv.get('pubDate', datetime.now().isoformat()))
        
        return advisories
    
    def get_critical_advisories(self):
        """Lấy các cảnh báo mức critical"""
        advisories = self.get_advisories_for_display()
        return [a for a in advisories if a.get('level') in ['do-not-travel', 'reconsider']]
    
    def get_advisories_by_country(self, country):
        """Lọc cảnh báo theo quốc gia"""
        advisories = self.get_advisories_for_display()
        return [a for a in advisories if a.get('country', '').lower() == country.lower()]


# Tạo instance
security_panel = SecurityPanel()