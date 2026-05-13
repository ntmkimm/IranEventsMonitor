from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess
import json
import os
import sys
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from apscheduler.schedulers.background import BackgroundScheduler
from panels.webcam_panel import webcam_panel
from panels.map_panel import map_panel
from panels.security_panel import security_panel
import threading

app = Flask(__name__)
CORS(app)

# ============ CRAWLER FUNCTIONS ============

def run_acled_crawl():
    """Chạy crawl ACLED events"""
    print("⚡ Running ACLED crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'iran_crawl_acled.py')
    result = subprocess.run(['python', script_path], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ ACLED crawl completed")
    else:
        print(f"❌ ACLED crawl failed: {result.stderr}")

def run_oil_crawl():
    """Chạy crawl oil prices"""
    print("🛢️ Running oil prices crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawl_oil_prices.py')
    result = subprocess.run(['python', script_path], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Oil prices crawl completed")
    else:
        print(f"❌ Oil crawl failed: {result.stderr}")

def run_security_crawl():
    """Chạy crawl security advisories"""
    print("🛡️ Running security crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawl_security.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Security crawl completed")
        else:
            print(f"❌ Security crawl failed: {result.stderr}")
    else:
        print("⚠️ crawl_security.py not found, using fallback")
        # Fallback: gọi trực tiếp hàm crawl trong file mới
        try:
            from crawlers.security_crawler import SecurityCrawler
            crawler = SecurityCrawler()
            crawler.crawl()
        except:
            pass

# ============ API ENDPOINTS CŨ ============

@app.route('/api/events', methods=['GET'])
def get_events():
    """Lấy dữ liệu sự kiện từ ACLED"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'iran_protests_clean.json')
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        return jsonify([])
    except Exception as e:
        print(f"Error reading events: {e}")
        return jsonify([])

@app.route('/api/oil', methods=['GET'])
def get_oil():
    """Lấy dữ liệu giá dầu"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'oil_prices.json')
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Kiểm tra cấu trúc dữ liệu
            if isinstance(data, dict) and 'data' in data:
                return jsonify(data['data'])
            return jsonify(data)
        return jsonify([])
    except Exception as e:
        print(f"Error reading oil data: {e}")
        return jsonify([])

@app.route('/api/security', methods=['GET'])
def get_security():
    """Lấy dữ liệu cảnh báo an ninh"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'security_advisories.json')
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Trả về đúng cấu trúc frontend mong đợi
            if 'data' in data:
                return jsonify(data['data'])
            return jsonify(data)
        return jsonify({'advisories': [], 'totalCount': 0})
    except Exception as e:
        print(f"Error reading security data: {e}")
        return jsonify({'advisories': [], 'totalCount': 0})

# ============ REFRESH API ============

@app.route('/api/refresh/acled', methods=['POST'])
def refresh_acled():
    """Kích hoạt crawl ACLED thủ công"""
    thread = threading.Thread(target=run_acled_crawl)
    thread.start()
    return jsonify({'message': 'ACLED crawl started'})

@app.route('/api/refresh/oil', methods=['POST'])
def refresh_oil():
    """Kích hoạt crawl oil thủ công"""
    thread = threading.Thread(target=run_oil_crawl)
    thread.start()
    return jsonify({'message': 'Oil crawl started'})

@app.route('/api/refresh/security', methods=['POST'])
def refresh_security():
    """Kích hoạt crawl security thủ công"""
    thread = threading.Thread(target=run_security_crawl)
    thread.start()
    return jsonify({'message': 'Security crawl started'})

# ============ API CHO WEBCAM ============

@app.route('/api/webcams', methods=['GET'])
def get_webcams():
    """Lấy danh sách webcam"""
    region = request.args.get('region', 'all')
    if region == 'all':
        data = webcam_panel.get_webcams()
    else:
        webcams = webcam_panel.get_webcams_by_region(region)
        data = {'webcams': webcams, 'totalCount': len(webcams)}
    return jsonify(data)

@app.route('/api/webcams/<webcam_id>', methods=['GET'])
def get_webcam_by_id(webcam_id):
    """Lấy thông tin webcam theo ID"""
    webcam = webcam_panel.get_webcam_by_id(webcam_id)
    if webcam:
        return jsonify(webcam)
    return jsonify({'error': 'Webcam not found'}), 404

@app.route('/api/webcams/embed/<video_id>', methods=['GET'])
def get_embed_url(video_id):
    """Tạo URL embed YouTube"""
    autoplay = request.args.get('autoplay', 'true').lower() == 'true'
    mute = request.args.get('mute', 'true').lower() == 'true'
    url = webcam_panel.get_embed_url(video_id, autoplay, mute)
    return jsonify({'embedUrl': url})

# ============ HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """Kiểm tra trạng thái các service"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'acled': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'iran_protests_clean.json')),
            'oil': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'oil_prices.json')),
            'security': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'security_advisories.json'))
        }
    })

# ============ SCHEDULER ============

scheduler = BackgroundScheduler()
# Chỉ schedule security crawl tự động (5 phút/lần)
scheduler.add_job(run_security_crawl, 'interval', minutes=5)
scheduler.start()

# Chạy các crawl lần đầu khi khởi động
print("🔄 Running initial crawls...")
run_acled_crawl()
run_oil_crawl()
run_security_crawl()

# ============ MAIN ============

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 US-IRAN CRISIS MONITOR BACKEND")
    print("=" * 50)
    print(f"📡 API available at: http://localhost:3000")
    print(f"   - GET  /api/events     (ACLED events)")
    print(f"   - GET  /api/oil        (Oil prices)")
    print(f"   - GET  /api/security   (Security advisories)")
    print(f"   - POST /api/refresh/acled")
    print(f"   - POST /api/refresh/oil")
    print(f"   - POST /api/refresh/security")
    print(f"   - GET  /api/health     (Health check)")
    print("=" * 50)
    app.run(host='0.0.0.0', port=3000, debug=True)