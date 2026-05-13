from abc import ABC, abstractmethod

class BasePanel(ABC):
    """Base class cho tất cả panel hiển thị"""
    
    def __init__(self, name, endpoint):
        self.name = name
        self.endpoint = endpoint
        self.data = None
    
    @abstractmethod
    def get_data(self):
        """Lấy dữ liệu cho panel"""
        pass
    
    @abstractmethod
    def render(self):
        """Render HTML cho panel (nếu cần)"""
        pass


class DataPanel(BasePanel):
    """Panel đơn giản chỉ cung cấp dữ liệu qua API"""
    
    def __init__(self, name, endpoint, data_provider):
        super().__init__(name, endpoint)
        self.data_provider = data_provider
    
    def get_data(self):
        self.data = self.data_provider()
        return self.data
    
    def render(self):
        return self.data