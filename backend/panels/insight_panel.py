import json
import os
from .base_panel import DataPanel

class InsightPanel(DataPanel):
    def __init__(self):
        super().__init__('Intelligence Insight', '/api/insight', self.load_insight)
    
    def load_insight(self):
        try:
            data_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'intelligence_insight.json')
            if os.path.exists(data_path):
                with open(data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"content": "No insight generated yet.", "updated_at": None}
        except Exception as e:
            print(f"Error loading insight: {e}")
            return {"content": "Error loading insight.", "updated_at": None}

insight_panel = InsightPanel()