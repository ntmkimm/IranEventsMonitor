import json
import os
from datetime import datetime, timezone
from .base_panel import DataPanel

class PolymarketPanel(DataPanel):
    """Panel cho dữ liệu dự đoán từ Polymarket"""
    
    def __init__(self):
        # Tên panel, endpoint API giả định, và hàm load dữ liệu
        super().__init__('Polymarket Predictions', '/api/polymarket', self.load_polymarket)
    
    def load_polymarket(self):
        """Load dữ liệu từ file JSON do crawler tạo ra"""
        try:
            # Đường dẫn tới file polymarket-results.json trong thư mục data
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'polymarket-results.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            return {'markets': [], 'stats': {}, 'fetched_at': None}
        except Exception as e:
            print(f"Error loading Polymarket data: {e}")
            return {'markets': [], 'stats': {}, 'fetched_at': None}

    def format_volume(self, volume):
        """Định dạng số volume (VD: 1200000 -> 1.2M)"""
        try:
            vol = float(volume)
            if vol >= 1_000_000:
                return f"${vol/1_000_000:.1f}M"
            elif vol >= 1_000:
                return f"${vol/1_000:.1f}K"
            return f"${vol:.0f}"
        except:
            return "$0"

    def get_markets_for_display(self, limit=10):
        """Lấy danh sách các thị trường đã được định dạng để hiển thị"""
        data = self.load_polymarket()
        markets = data.get('markets', [])
        
        display_list = []
        for m in markets[:limit]:
            # Thêm các field hỗ trợ hiển thị UI
            formatted_market = m.copy()
            formatted_market['display_volume'] = self.format_volume(m.get('volume', 0))
            formatted_market['probability'] = f"{m.get('yes_price', 0)}%"
            
            # Xác định mức độ quan trọng dựa trên xác suất (Xanh nếu cao, Đỏ nếu thấp)
            prob = m.get('yes_price', 50)
            if prob >= 70 or prob <= 30:
                formatted_market['status_color'] = 'warning'  # Biến động mạnh/Khả năng cao
            else:
                formatted_market['status_color'] = 'info'
                
            display_list.append(formatted_market)
            
        return display_list

    def get_summary_stats(self):
        """Lấy thông tin tổng hợp cho Dashboard"""
        data = self.load_polymarket()
        markets = data.get('markets', [])
        
        # Tìm thị trường có volume lớn nhất
        top_market = None
        if markets:
            top_market = max(markets, key=lambda x: x.get('volume', 0))
            
        return {
            'total_active': len(markets),
            'top_event': top_market.get('title') if top_market else "N/A",
            'last_update': data.get('fetched_at')
        }

    def get_high_conviction_markets(self):
        """Lọc ra các thị trường có xác suất 'Yes' rất cao (>80%) hoặc rất thấp (<20%)"""
        markets = self.get_markets_for_display(limit=100)
        return [m for m in markets if m.get('yes_price', 50) >= 80 or m.get('yes_price', 50) <= 20]

# Tạo instance để export
polymarket_panel = PolymarketPanel()