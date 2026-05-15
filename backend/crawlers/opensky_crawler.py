import requests
import re
import time
import os
import json
from datetime import datetime

# --- CẤU HÌNH VÙNG CHIẾN TRƯỜNG IRAN ---
IRAN_BOUNDS = {"lamin": 20.0, "lomin": 30.0, "lamax": 42.0, "lomax": 65.0}

# --- THÔNG SỐ NGƯỠNG BÁO ĐỘNG ---
THRESHOLD_ELEVATED = 8
THRESHOLD_CRITICAL = 20

# --- DANH SÁCH LỌC DÂN DỤNG (ICAO 3-letter) ---
COMMERCIAL_ICAO = {
    'IRA', 'SVA', 'THY', 'ELY', 'UAE', 'QTR', 'CCA', 'CHH', 
    'MSR', 'MEA', 'RJA', 'KAC', 'PGT', 'AXB', 'FDB'
}

# --- MẪU HEX QUÂN SỰ ---
HEX_RANGES = [
    {"start": "ADF7C8", "end": "AFFFFF", "operator": "usaf"}, # Mỹ
    {"start": "738A00", "end": "738BFF", "operator": "iaf"},  # Israel
    {"start": "43C000", "end": "43CFFF", "operator": "raf"},  # Anh
    {"start": "RFF000", "end": "RFFFFF", "operator": "vks"},  # Nga
]

# --- MẪU CALLSIGN QUÂN SỰ ---
STRICT_MILITARY_PATTERNS = [
    r'^IRIAF', r'^IRGC', r'^RCH\d', r'^REACH', r'^FORTE', r'^NATO', 
    r'^RFF', r'^RSD', r'^RRR', r'^RFR', r'^ASY', r'^ASCOT', r'^LAGR', r'^TARTAN'
]

class IranMilitaryTracker:
    def __init__(self):
        self.session = requests.Session()
        self.prev_count = 0
        self.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../data')
        os.makedirs(self.data_dir, exist_ok=True)

    def detect_mission_type(self, callsign):
        cs = callsign.upper()
        if re.search(r'KC|STRAT|SHELL|TEXACO|PETRO|LAGR|TARTAN|VGY', cs): 
            return 'TANKER'
        if re.search(r'SENTRY|AWACS|MAGIC|HOMER|OLIVE|JAKE|FORTE', cs): 
            return 'RECON'
        if re.search(r'RCH|REACH|ASCOT|C17|C5|C130|CTM|RRR|RFR', cs): 
            return 'TRANSPORT'
        if re.search(r'BOLT|VIPER|F15|F16|F22|F35|STRIKE', cs): 
            return 'FIGHTER'
        return 'MILITARY'

    def is_commercial(self, callsign):
        if not callsign: return False
        if callsign[:3] in COMMERCIAL_ICAO: return True
        if re.search(r'^QR\d|^SV\d|^TK\d|^EK\d|^IR\d', callsign): return True
        return False

    def classify_flight(self, state):
        icao24 = state[0].upper()
        callsign = (state[1] or "").strip().upper()
        country = state[2]
        
        # 1. Kiểm tra Callsign quân sự xác định
        for p in STRICT_MILITARY_PATTERNS:
            if re.search(p, callsign, re.I):
                return True, f"Strict Military Pattern", self.detect_mission_type(callsign)

        # 2. Loại bỏ hàng không dân dụng
        if self.is_commercial(callsign):
            return False, None, None

        # 3. Kiểm tra dải HEX quân sự
        for r in HEX_RANGES:
            if r["start"] <= icao24 <= r["end"]:
                return True, f"Military Hex ({r['operator']})", self.detect_mission_type(callsign)

        # 4. Logic Heuristic Iran (Tài sản không định danh)
        if "Iran" in country:
            if not callsign or len(callsign) < 4 or callsign.startswith("EP"):
                return True, "Iran Asset Heuristic", "UNKNOWN_MIL"

        return False, None, None

    def save_to_json(self, military_flights):
        if not military_flights: return
        
        filename = f"{self.data_dir}/iran_intel_opensky.json"
        
        report = {
            "snapshot_time": datetime.now().isoformat(),
            "count": len(military_flights),
            "flights": military_flights
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
        return filename

    def run(self):
        url = "https://opensky-network.org/api/states/all"
        try:
            resp = self.session.get(url, params=IRAN_BOUNDS, timeout=15)
            if resp.status_code != 200:
                print(f"[!] Lỗi API: {resp.status_code}")
                return

            states = resp.json().get('states', [])
            mil_results = []
            
            for s in states:
                is_mil, reason, m_type = self.classify_flight(s)
                if is_mil:
                    mil_results.append({
                        "callsign": s[1].strip() if s[1] else "UNCALLSIGN",
                        "hex": s[0].upper(),
                        "type": m_type,
                        "reason": reason,
                        "origin": s[2],
                        "alt": f"{int(s[7])}m" if s[7] else "N/A",
                        "lat": s[6],
                        "lon": s[5]
                    })

            self.analyze_and_print(mil_results)
            if mil_results:
                self.save_to_json(mil_results)

        except Exception as e:
            print(f"[!] Lỗi kết nối: {e}")

    def analyze_and_print(self, flights):
        count = len(flights)
        types = [f['type'] for f in flights]
        
        # Posture Level
        posture = "NORMAL"
        if count >= THRESHOLD_CRITICAL: posture = "🔴 CRITICAL"
        elif count >= THRESHOLD_ELEVATED: posture = "🟡 ELEVATED"

        print(f"\n{'='*25} IRAN INTEL SITREP {'='*25}")
        print(f"Thời gian: {datetime.now().strftime('%H:%M:%S')} | Trạng thái: {posture}")
        print(f"Mục tiêu quân sự hiện tại: {count}")

        # Phát hiện Surge
        if count > self.prev_count and self.prev_count > 0:
            print(f"⚠️  CẢNH BÁO SURGE: +{count - self.prev_count} mục tiêu mới!")

        # Phát hiện biên đội (Strike Team)
        if "TANKER" in types and "RECON" in types:
            print("🔥 CẢNH BÁO: Phát hiện biên đội Tiếp dầu & Trinh sát đang hoạt động!")

        if count > 0:
            print("-" * 80)
            print(f"{'CALLSIGN':<12} | {'TYPE':<12} | {'REASON':<22} | {'ALT':<8} | {'HEX'}")
            print("-" * 80)
            for f in flights:
                print(f"{f['callsign']:<12} | {f['type']:<12} | {f['reason']:<22} | {f['alt']:<8} | {f['hex']}")
        
        self.prev_count = count

if __name__ == "__main__":
    tracker = IranMilitaryTracker()
    tracker.run()
