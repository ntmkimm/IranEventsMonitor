import json
import os
from datetime import datetime
from .base_panel import DataPanel

class LiveuamapPanel(DataPanel):
    """Panel xử lý dữ liệu events từ Liveuamap"""
    
    def __init__(self):
        super().__init__('Liveuamap Events', '/api/liveuamap', self.load_events)
    
    def load_events(self):
        """Load dữ liệu từ file JSON"""
        try:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'iran-events-latest.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Tương thích ngược nếu file chỉ là List (format cũ)
                    if isinstance(data, list):
                        return {
                            'events': data,
                            'totalCount': len(data),
                            'fetchedAt': datetime.now().isoformat()
                        }
                    
                    # Trả về nguyên bản format chuẩn Object mới
                    return data
                    
            return {'events':[], 'totalCount': 0}
        except Exception as e:
            print(f"Error loading liveuamap data: {e}")
            return {'events':[], 'totalCount': 0}
            
    def get_events_for_display(self):
        """Lấy danh sách các sự kiện"""
        data = self.load_events()
        events = data.get('events',[])
        return events
        
    def get_events_with_coordinates(self):
        """Lấy các sự kiện có thông tin tọa độ (Latitude/Longitude) rõ ràng"""
        events = self.get_events_for_display()
        
        valid_events =[]
        for e in events:
            coords = e.get('coordinates', {})
            if coords.get('lat') is not None and coords.get('lon') is not None:
                valid_events.append(e)
                
        return valid_events
        
    def get_latest_events(self, limit=10):
        """Lấy N sự kiện gần nhất (dựa trên mảng trả về từ json)"""
        events = self.get_events_for_display()
        return events[:limit]

# Tạo instance để gọi tương tự như security_panel
liveuamap_panel = LiveuamapPanel()