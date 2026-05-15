# backend/app.py
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
import threading

# Import Panels
from panels.webcam_panel import webcam_panel
from panels.map_panel import map_panel
from panels.security_panel import security_panel
from panels.liveuamap_panel import liveuamap_panel
from panels.telegram_panel import telegram_panel      
from panels.polymarket_panel import polymarket_panel  
from panels.opensky_panel import opensky_panel
from panels.gdelt_panel import gdelt_panel            # MỚI

app = Flask(__name__)
CORS(app)

# ============ CRAWLER FUNCTIONS ============

def run_acled_crawl():
    """Chạy crawl ACLED events"""
    print("⚡ Running ACLED crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'iran_crawl_acled.py')
    result = subprocess.run(['python', script_path], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ ACLED crawl completed")
    else:
        print(f"❌ ACLED crawl failed: {result.stderr}")

def run_oil_crawl():
    """Chạy crawl oil prices"""
    print("🛢️ Running oil prices crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'crawl_oil_prices.py')
    result = subprocess.run(['python', script_path], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Oil prices crawl completed")
    else:
        print(f"❌ Oil crawl failed: {result.stderr}")

def run_security_crawl():
    """Chạy crawl security advisories"""
    print("🛡️ Running security crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'crawl_security.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Security crawl completed")
        else:
            print(f"❌ Security crawl failed: {result.stderr}")

def run_liveuamap_crawl():
    """Chạy crawl Liveuamap events"""
    print("🗺️ Running Liveuamap crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'liveuamap_crawler.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Liveuamap crawl completed")
        else:
            print(f"❌ Liveuamap crawl failed: {result.stderr}")

def run_telegram_crawl():
    """Chạy crawl Telegram channels"""
    print("📢 Running Telegram crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'telegram_crawler.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Telegram crawl completed")
        else:
            print(f"❌ Telegram crawl failed: {result.stderr}")

def run_polymarket_crawl():
    """Chạy crawl Polymarket predictions"""
    print("📊 Running Polymarket crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'polymarket_crawler.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Polymarket crawl completed")
        else:
            print(f"❌ Polymarket crawl failed: {result.stderr}")

def run_opensky_crawl():
    """Chạy crawl OpenSky Military Tracker"""
    print("✈️ Running OpenSky crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'iran_opensky_crawler.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ OpenSky crawl completed")
        else:
            print(f"❌ OpenSky crawl failed: {result.stderr}")

def run_gdelt_crawl(): # MỚI
    """Chạy crawl GDELT News"""
    print("📰 Running GDELT crawl...")
    script_path = os.path.join(os.path.dirname(__file__), 'crawlers', 'gdelt_crawler.py')
    if os.path.exists(script_path):
        result = subprocess.run(['python', script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GDELT crawl completed")
        else:
            print(f"❌ GDELT crawl failed: {result.stderr}")

# ============ API ENDPOINTS ============

@app.route('/api/events', methods=['GET'])
def get_events():
    """ACLED data"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'iran_protests_clean.json')
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        return jsonify([])
    except Exception as e:
        return jsonify([])

@app.route('/api/oil', methods=['GET'])
def get_oil():
    """Oil prices"""
    try:
        data_path = os.path.join(os.path.dirname(__file__), 'data', 'oil_prices.json')
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict) and 'data' in data:
                return jsonify(data['data'])
            return jsonify(data)
        return jsonify([])
    except:
        return jsonify([])

@app.route('/api/security', methods=['GET'])
def get_security():
    """Security advisories"""
    try:
        data = security_panel.load_security()
        return jsonify(data)
    except:
        return jsonify({'advisories':[], 'totalCount': 0})

@app.route('/api/liveuamap', methods=['GET'])
def get_liveuamap():
    """Liveuamap events"""
    try:
        data = liveuamap_panel.load_events()
        return jsonify(data)
    except Exception as e:
        print(f"Error reading liveuamap data: {e}")
        return jsonify({'events':[], 'totalCount': 0})

@app.route('/api/telegram', methods=['GET'])
def get_telegram():
    """Telegram feed data"""
    try:
        limit = request.args.get('limit', default=20, type=int)
        data = telegram_panel.get_posts_for_display(limit=limit)
        meta = telegram_panel.load_telegram()
        return jsonify({
            'posts': data,
            'totalCount': meta.get('total_posts', 0),
            'updatedAt': meta.get('updatedAt')
        })
    except Exception as e:
        print(f"Error reading telegram data: {e}")
        return jsonify({'posts': [], 'totalCount': 0})

@app.route('/api/polymarket', methods=['GET'])
def get_polymarket():
    """Polymarket predictions"""
    try:
        data = polymarket_panel.get_markets_for_display()
        meta = polymarket_panel.load_polymarket()
        return jsonify({
            'markets': data,
            'stats': meta.get('stats', {}),
            'fetchedAt': meta.get('fetched_at')
        })
    except Exception as e:
        print(f"Error reading polymarket data: {e}")
        return jsonify({'markets': [], 'stats': {}})

@app.route('/api/opensky', methods=['GET'])
def get_opensky():
    """OpenSky military flight data"""
    try:
        flights = opensky_panel.load_military_flights()
        summary = opensky_panel.get_summary()
        return jsonify({
            'flights': flights,
            'summary': summary
        })
    except Exception as e:
        print(f"Error reading opensky data: {e}")
        return jsonify({'flights': [], 'summary': {}})

@app.route('/api/gdelt', methods=['GET']) # MỚI
def get_gdelt():
    """GDELT News data"""
    try:
        articles = gdelt_panel.get_articles_for_display()
        return jsonify({
            'articles': articles,
            'totalCount': len(articles)
        })
    except Exception as e:
        print(f"Error reading GDELT data: {e}")
        return jsonify({'articles': [], 'totalCount': 0})

# ============ REFRESH API ============

@app.route('/api/refresh/acled', methods=['POST'])
def refresh_acled():
    threading.Thread(target=run_acled_crawl).start()
    return jsonify({'message': 'ACLED crawl started'})

@app.route('/api/refresh/oil', methods=['POST'])
def refresh_oil():
    threading.Thread(target=run_oil_crawl).start()
    return jsonify({'message': 'Oil crawl started'})

@app.route('/api/refresh/security', methods=['POST'])
def refresh_security():
    threading.Thread(target=run_security_crawl).start()
    return jsonify({'message': 'Security crawl started'})

@app.route('/api/refresh/liveuamap', methods=['POST'])
def refresh_liveuamap():
    threading.Thread(target=run_liveuamap_crawl).start()
    return jsonify({'message': 'Liveuamap crawl started'})

@app.route('/api/refresh/telegram', methods=['POST'])
def refresh_telegram():
    threading.Thread(target=run_telegram_crawl).start()
    return jsonify({'message': 'Telegram crawl started'})

@app.route('/api/refresh/polymarket', methods=['POST'])
def refresh_polymarket():
    threading.Thread(target=run_polymarket_crawl).start()
    return jsonify({'message': 'Polymarket crawl started'})

@app.route('/api/refresh/opensky', methods=['POST'])
def refresh_opensky():
    threading.Thread(target=run_opensky_crawl).start()
    return jsonify({'message': 'OpenSky crawl started'})

@app.route('/api/refresh/gdelt', methods=['POST']) # MỚI
def refresh_gdelt():
    threading.Thread(target=run_gdelt_crawl).start()
    return jsonify({'message': 'GDELT crawl started'})

# ============ WEBCAM API ============

@app.route('/api/webcams', methods=['GET'])
def get_webcams():
    region = request.args.get('region', 'all')
    if region == 'all':
        data = webcam_panel.get_webcams()
    else:
        webcams = webcam_panel.get_webcams_by_region(region)
        data = {'webcams': webcams, 'totalCount': len(webcams)}
    return jsonify(data)

@app.route('/api/webcams/<webcam_id>', methods=['GET'])
def get_webcam_by_id(webcam_id):
    webcam = webcam_panel.get_webcam_by_id(webcam_id)
    return jsonify(webcam) if webcam else (jsonify({'error': 'Webcam not found'}), 404)

# ============ HEALTH CHECK ============

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'acled': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'iran_protests_clean.json')),
            'oil': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'oil_prices.json')),
            'security': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'security_advisories.json')),
            'liveuamap': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'iran-events-latest.json')),
            'telegram': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'telegram_results.json')),
            'polymarket': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'polymarket-results.json')),
            'opensky': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'iran_intel_opensky.json')),
            'gdelt': os.path.exists(os.path.join(os.path.dirname(__file__), 'data', 'gdelt_iran_us_energy.json')) # MỚI
        }
    })

# ============ SCHEDULER ============

scheduler = BackgroundScheduler()
scheduler.add_job(run_security_crawl, 'interval', minutes=10)
scheduler.add_job(run_liveuamap_crawl, 'interval', minutes=15)
scheduler.add_job(run_telegram_crawl, 'interval', minutes=20)
scheduler.add_job(run_polymarket_crawl, 'interval', minutes=25)
scheduler.add_job(run_oil_crawl, 'interval', minutes=15)
scheduler.add_job(run_opensky_crawl, 'interval', minutes=5)
scheduler.add_job(run_gdelt_crawl, 'interval', minutes=30) # MỚI: Update GDELT mỗi 30 phút
scheduler.add_job(run_acled_crawl, 'interval', minutes=240)
scheduler.start()

# Chạy lần đầu khi khởi động
# print("🔄 Running initial crawls...")
# run_oil_crawl()
# run_security_crawl()
# run_liveuamap_crawl()
# run_telegram_crawl()
# run_polymarket_crawl()
# run_opensky_crawl()
# run_gdelt_crawl() # MỚI: Chạy GDELT lần đầu

# ============ MAIN ============

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 US-IRAN CRISIS MONITOR BACKEND")
    print("=" * 50)
    print(f"📡 API available at: http://localhost:3000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=3000, debug=True)