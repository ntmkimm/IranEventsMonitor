import json
import os
from abc import ABC, abstractmethod
from datetime import datetime

class BaseCrawler(ABC):
    """Base class cho tất cả crawler"""
    
    def __init__(self, name, data_dir='backend/data'):
        self.name = name
        self.data_dir = data_dir
        self.logs = []
        
    def log(self, message, type='INFO'):
        timestamp = datetime.now().isoformat()
        log_line = f"[{timestamp}] [{type}] [{self.name}] {message}"
        self.logs.append(log_line)
        print(log_line)
    
    def save_json(self, data, filename):
        """Lưu dữ liệu vào file JSON"""
        os.makedirs(self.data_dir, exist_ok=True)
        filepath = os.path.join(self.data_dir, filename)
        
        # Thêm metadata
        output = {
            'fetchedAt': datetime.now().isoformat(),
            'source': self.name,
            'data': data
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
        
        self.log(f"Saved to {filepath}")
        return filepath
    
    @abstractmethod
    def crawl(self):
        """Phương thức crawl chính - phải được override"""
        pass