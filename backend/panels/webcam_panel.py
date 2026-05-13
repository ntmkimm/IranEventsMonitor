import json
import os
from .base_panel import DataPanel

class WebcamPanel(DataPanel):
    """Panel cho live webcams từ YouTube"""
    
    def __init__(self):
        super().__init__('Webcams', '/api/webcams', self.get_webcams)
        # Danh sách webcam cố định
        self.webcams = [
            {
                "id": "tehran",
                "city": "Tehran",
                "country": "Iran",
                "region": "iran",
                "videoId": "gmtlJ_m2r5A",
                "channel": "@IranLiveCam",
                "thumbnail": "https://img.youtube.com/vi/gmtlJ_m2r5A/hqdefault.jpg"
            },
            {
                "id": "tel-aviv",
                "city": "Tel Aviv",
                "country": "Israel",
                "region": "middle-east",
                "videoId": "fIurYTprwzg",
                "channel": "@IsraelLiveCam",
                "thumbnail": "https://img.youtube.com/vi/fIurYTprwzg/hqdefault.jpg"
            },
            {
                "id": "jerusalem",
                "city": "Jerusalem",
                "country": "Israel",
                "region": "middle-east",
                "videoId": "e34xb-Fbl0U",
                "channel": "@JerusalemLive",
                "thumbnail": "https://img.youtube.com/vi/e34xb-Fbl0U/hqdefault.jpg"
            },
            {
                "id": "beirut",
                "city": "Beirut",
                "country": "Lebanon",
                "region": "middle-east",
                "videoId": "djF-Lkgfp6k",
                "channel": "@MTVLebanonNews",
                "thumbnail": "https://img.youtube.com/vi/djF-Lkgfp6k/hqdefault.jpg"
            },
            {
                "id": "washington",
                "city": "Washington DC",
                "country": "USA",
                "region": "americas",
                "videoId": "1wV9lLe14aU",
                "channel": "@AxisCommunications",
                "thumbnail": "https://img.youtube.com/vi/1wV9lLe14aU/hqdefault.jpg"
            },
            {
                "id": "new-york",
                "city": "New York",
                "country": "USA",
                "region": "americas",
                "videoId": "4qyZLflp-sI",
                "channel": "@EarthCam",
                "thumbnail": "https://img.youtube.com/vi/4qyZLflp-sI/hqdefault.jpg"
            }
        ]
    
    def get_webcams(self):
        """Lấy danh sách webcam"""
        return {
            'webcams': self.webcams,
            'totalCount': len(self.webcams),
            'regions': ['iran', 'middle-east', 'americas']
        }
    
    def get_webcam_by_id(self, webcam_id):
        """Lấy webcam theo ID"""
        for webcam in self.webcams:
            if webcam['id'] == webcam_id:
                return webcam
        return None
    
    def get_webcams_by_region(self, region):
        """Lấy webcam theo khu vực"""
        return [w for w in self.webcams if w.get('region') == region]
    
    def get_embed_url(self, video_id, autoplay=True, mute=True):
        """Tạo URL embed YouTube"""
        params = []
        if autoplay:
            params.append("autoplay=1")
        if mute:
            params.append("mute=1")
        params.append("controls=0")
        params.append("modestbranding=1")
        params.append("playsinline=1")
        params.append("rel=0")
        
        param_str = "&".join(params)
        return f"https://www.youtube.com/embed/{video_id}?{param_str}"


# Tạo instance để dùng trong app.py
webcam_panel = WebcamPanel()