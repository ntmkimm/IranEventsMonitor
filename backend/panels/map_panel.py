import json
import os
from .base_panel import DataPanel

class MapPanel(DataPanel):
    """Panel cho bản đồ 2D hiển thị sự kiện"""
    
    def __init__(self):
        super().__init__('Map', '/api/events', self.load_events)
    
    def load_events(self):
        """Load dữ liệu sự kiện từ file JSON"""
        try:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'iran_protests_clean.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Kiểm tra cấu trúc dữ liệu
                    if isinstance(data, dict) and 'events' in data:
                        return data['events']
                    elif isinstance(data, list):
                        return data
                    return []
            return []
        except Exception as e:
            print(f"Error loading events: {e}")
            return []
    
    def get_summary(self):
        """Lấy thống kê tóm tắt"""
        events = self.get_data()
        return {
            'totalEvents': len(events),
            'eventTypes': self._count_event_types(events),
            'lastUpdate': self._get_last_update(events)
        }
    
    def _count_event_types(self, events):
        """Đếm số lượng từng loại sự kiện"""
        types = {}
        for event in events:
            event_type = event.get('type', 'Unknown')
            types[event_type] = types.get(event_type, 0) + 1
        return types
    
    def _get_last_update(self, events):
        """Lấy thời gian cập nhật mới nhất"""
        if not events:
            return None
        dates = [event.get('date') for event in events if event.get('date')]
        return max(dates) if dates else None


# Tạo instance để dùng trong app.py
map_panel = MapPanel()