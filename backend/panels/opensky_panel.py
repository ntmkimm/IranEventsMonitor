import json
import os
from datetime import datetime
from .base_panel import DataPanel

class OpenSkyPanel(DataPanel):
    """Panel cho theo dõi biến động hàng không quân sự tại Iran"""
    
    def __init__(self):
        # Đường dẫn tới file JSON mà tracker OpenSky lưu vào
        super().__init__('OpenSky Military', '/api/opensky', self.load_military_flights)
        self.data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'iran_intel_opensky.json')
    
    def load_military_flights(self):
        """Load dữ liệu máy bay quân sự từ file JSON"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # OpenSky Tracker lưu dưới dạng {"flights": [...]}
                    return data.get('flights', [])
            return []
        except Exception as e:
            print(f"Error loading OpenSky data: {e}")
            return []
    
    def get_summary(self):
        """Lấy thống kê tóm tắt cho hàng không"""
        flights = self.get_data()
        
        # Logic phân loại nhanh
        mission_counts = self._count_mission_types(flights)
        
        # Xác định mức độ cảnh báo (Posture)
        count = len(flights)
        posture = "NORMAL"
        if count >= 20: posture = "CRITICAL"
        elif count >= 8: posture = "ELEVATED"

        return {
            'totalMilitary': count,
            'missionTypes': mission_counts,
            'posture': posture,
            'hasStrikePackage': self._detect_strike_package(mission_counts),
            'lastUpdate': self._get_last_timestamp()
        }
    
    def _count_mission_types(self, flights):
        """Đếm các loại nhiệm vụ (Tanker, Recon, Fighter...)"""
        types = {}
        for f in flights:
            m_type = f.get('type', 'UNKNOWN')
            types[m_type] = types.get(m_type, 0) + 1
        return types

    def _detect_strike_package(self, counts):
        """Kiểm tra nếu có sự kết hợp nguy hiểm (Tiếp dầu + Trinh sát)"""
        return counts.get('TANKER', 0) > 0 and counts.get('RECON', 0) > 0

    def _get_last_timestamp(self):
        """Lấy thời gian snapshot từ file"""
        try:
            if os.path.exists(self.data_path):
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    return data.get('snapshot_time')
        except:
            pass
        return None

# Tạo instance để dùng trong app.py
opensky_panel = OpenSkyPanel()