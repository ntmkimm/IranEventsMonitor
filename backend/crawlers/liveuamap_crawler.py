import json
import time
import re
import os
import sys
from datetime import datetime
import urllib.request
import urllib.parse
from playwright.sync_api import sync_playwright

# Ép UTF-8 cho Terminal (giống security_crawlers)
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

def clean_time_str(raw):
    """Loại bỏ chữ 'source' bị dính vào cuối time string, và bỏ text tọa độ."""
    raw = re.sub(r'\s*source\s*$', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*-\s*\d+°\d+['’′][NS]\s+\d+°\d+['’′][EW]", '', raw)
    return raw.strip()

def extract_dms_coordinates(text):
    """Trích xuất tọa độ dạng độ-phút (VD: 35°41'N 51°22'E)."""
    match = re.search(r"(\d+)°(\d+)['’′]([NS])\s+(\d+)°(\d+)['’′]([EW])", text)
    if match:
        lat_d, lat_m, lat_dir, lon_d, lon_m, lon_dir = match.groups()
        lat = float(lat_d) + float(lat_m)/60.0
        if lat_dir == 'S': lat = -lat
        lon = float(lon_d) + float(lon_m)/60.0
        if lon_dir == 'W': lon = -lon
        return round(lat, 6), round(lon, 6)
    return None, None

def _extract_coords_from_json(data, coords_dict):
    """Recursively extract coordinate data from API JSON responses."""
    if isinstance(data, dict):
        lat = data.get('lat') or data.get('latitude')
        lon = (data.get('lon') or data.get('lng') or data.get('longitude'))
        eid = str(data.get('id') or data.get('nid') or data.get('event_id') or '')
        if lat is not None and lon is not None and eid:
            try:
                coords_dict[eid] = {"lat": float(lat), "lng": float(lon)}
            except (ValueError, TypeError):
                pass
        # Check nested GeoJSON
        if data.get('type') == 'Feature' and isinstance(data.get('geometry'), dict):
            geom = data['geometry']
            if (geom.get('type') == 'Point'
                    and isinstance(geom.get('coordinates'), list)
                    and len(geom['coordinates']) >= 2):
                props = data.get('properties', {})
                fid = str(props.get('id') or data.get('id') or '')
                if fid:
                    coords_dict[fid] = {
                        "lat": float(geom['coordinates'][1]),
                        "lng": float(geom['coordinates'][0])
                    }
        for v in data.values():
            if isinstance(v, (dict, list)):
                _extract_coords_from_json(v, coords_dict)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                _extract_coords_from_json(item, coords_dict)

def crawl_liveuamap(url):
    print(f"🌍 Bắt đầu crawl dữ liệu từ: {url}")
    events_data =[]
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = context.new_page()

        # Intercept API responses to capture coordinate data
        api_coords = {}

        def handle_response(response):
            try:
                ct = response.headers.get('content-type', '')
                resp_url = response.url
                if response.ok and ('json' in ct or 'javascript' in ct or 'text' in ct or 'html' in ct):
                    if any(kw in resp_url for kw in ['/ajax', '/api', 'event', 'news', 'marker', 'popup']):
                        body = response.text()
                        
                        id_from_url = None
                        id_match = re.search(r'[?&]id=(\d+)', resp_url)
                        if id_match:
                            id_from_url = id_match.group(1)

                        # Try JSON parsing
                        try:
                            data = json.loads(body)
                            _extract_coords_from_json(data, api_coords)
                            if id_from_url and isinstance(data, dict):
                                lat = data.get('lat') or data.get('latitude')
                                lon = data.get('lon') or data.get('lng') or data.get('longitude')
                                if lat is not None and lon is not None:
                                    api_coords[id_from_url] = {"lat": float(lat), "lng": float(lon)}
                        except (json.JSONDecodeError, ValueError):
                            pass
                            
                        # Try to find data-lat and data-lon in HTML response
                        lat_lng_match = re.search(r'data-lat=["\']([0-9.-]+)["\']\s+data-l(?:on|ng)=["\']([0-9.-]+)["\']', body)
                        if lat_lng_match:
                            extracted_id = id_from_url
                            if not extracted_id:
                                body_id_match = re.search(r'data-id=["\'](\d+)["\']', body)
                                if body_id_match:
                                    extracted_id = body_id_match.group(1)
                            if extracted_id:
                                api_coords[extracted_id] = {
                                    "lat": float(lat_lng_match.group(1)), "lng": float(lat_lng_match.group(2))
                                }

                        # Try DMS from raw text
                        dms_lat, dms_lon = extract_dms_coordinates(body)
                        if dms_lat is not None:
                            extracted_id = id_from_url
                            if not extracted_id:
                                body_id_match = re.search(r'"id"\s*:\s*"?(\d+)', body) or re.search(r'data-id=["\'](\d+)["\']', body)
                                if body_id_match:
                                    extracted_id = body_id_match.group(1)
                            if extracted_id:
                                api_coords[extracted_id] = {
                                    "lat": dms_lat, "lng": dms_lon
                                }
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            print("⏳ Đã tải trang, chờ feed hiển thị...")

            try:
                page.wait_for_selector("#feedler, .feedler, .event-list", timeout=30000)
            except Exception:
                print("⚠️ Không tìm thấy #feedler, chờ networkidle...")
                page.wait_for_load_state("networkidle", timeout=30000)

            # Cuộn để kích hoạt lazy-load
            for _ in range(5):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(2)
                page.evaluate("""
                    var f = document.getElementById('feedler');
                    if (f) f.scrollTop = f.scrollHeight;
                """)
                time.sleep(1)

            # === Parse DOM events ===
            dom_events = page.evaluate("""() => {
                var results =[];
                var items = document.querySelectorAll('.sourcees, .event, [data-id]');
                items.forEach(function(el) {
                    var id = el.getAttribute('data-id') || '';
                    var titleEl = el.querySelector('.title, .event-title, h3, h4');
                    var title = titleEl ? titleEl.textContent.trim() : '';
                    var timeEl = el.querySelector('.date_add, .time, time, .event-time');
                    var timeStr = timeEl ? timeEl.textContent.trim() : '';
                    var linkEl = el.querySelector('a.source-link, a[href]');
                    var source = linkEl ? linkEl.getAttribute('href') : '';
                    
                    var lat = el.getAttribute('data-lat') || el.getAttribute('data-latitude') || '';
                    var lon = el.getAttribute('data-lon') || el.getAttribute('data-lng') || el.getAttribute('data-longitude') || '';

                    if (title && id) {
                        results.push({
                            id: id, title: title,
                            time: timeStr, source: source || '',
                            lat: lat, lon: lon
                        });
                    }
                });
                return results;
            }""")
            print(f"📊 DOM: {len(dom_events)} events")

            # === Scan HTML content for hidden JSON coordinates ===
            try:
                html_content = page.content()
                for m in re.finditer(r'\{[^\}]*"id"\s*:\s*"?(\d+)"?[^\}]*"lat(?:itude)?"\s*:\s*([0-9.-]+)[^\}]*"l(?:on|ng)(?:gitude)?"\s*:\s*([0-9.-]+)[^\}]*\}', html_content, re.IGNORECASE):
                    api_coords[m.group(1)] = {"lat": float(m.group(2)), "lng": float(m.group(3))}
                for m in re.finditer(r'\{[^\}]*"lat(?:itude)?"\s*:\s*([0-9.-]+)[^\}]*"l(?:on|ng)(?:gitude)?"\s*:\s*([0-9.-]+)[^\}]*"id"\s*:\s*"?(\d+)"?[^\}]*\}', html_content, re.IGNORECASE):
                    api_coords[m.group(3)] = {"lat": float(m.group(1)), "lng": float(m.group(2))}
                for m in re.finditer(r'data-id=["\'](\d+)["\'].*?data-lat=["\']([0-9.-]+)["\'].*?data-l(?:on|ng)=["\']([0-9.-]+)["\']', html_content, re.IGNORECASE | re.DOTALL):
                    api_coords[m.group(1)] = {"lat": float(m.group(2)), "lng": float(m.group(3))}
                for m in re.finditer(r'"type"\s*:\s*"Feature".*?"coordinates"\s*:\s*\[([0-9.-]+)\s*,\s*([0-9.-]+)\].*?"id"\s*:\s*"?(\d+)"?', html_content, re.IGNORECASE | re.DOTALL):
                    api_coords[m.group(3)] = {"lat": float(m.group(2)), "lng": float(m.group(1))}
            except Exception:
                pass

            # === Probe map: tim Leaflet instance + debug marker properties ===
            map_info = page.evaluate("""() => {
                var info = {found: false, type: '', markers:[]};
                var mapObj = null;
                var containers = document.querySelectorAll('.leaflet-container, #map, #mapid, [id*=map]');
                for (var i = 0; i < containers.length; i++) {
                    var el = containers[i];
                    for (var key in el) {
                        try {
                            if ((key.indexOf('leaflet') >= 0 || key.indexOf('_map') >= 0) && el[key] && el[key]._layers) {
                                mapObj = el[key]; info.type = 'leaflet-dom-' + key; break;
                            }
                        } catch(e) {}
                    }
                    if (mapObj) break;
                }
                if (!mapObj) {
                    for (var wk in window) {
                        try {
                            var wv = window[wk];
                            if (wv && typeof wv === 'object' && wv._layers && typeof wv.getCenter === 'function') {
                                mapObj = wv; info.type = 'window-' + wk; break;
                            }
                        } catch(e) {}
                    }
                }
                if (!mapObj) return info;
                info.found = true;

                for (var lid in mapObj._layers) {
                    var layer = mapObj._layers[lid];
                    if (layer && layer._latlng) {
                        var mid = '';
                        try { mid = String(layer.options.id || layer.feature.properties.id || layer.feature.id || layer._eventId || layer.options.data_id || ''); } catch(e) {}
                        if (!mid && layer._icon) {
                            mid = layer._icon.getAttribute('data-id') || '';
                        }
                        var popup = '';
                        try { if (layer._popup) popup = layer._popup._content || ''; } catch(e) {}
                        info.markers.push({ id: mid, lat: layer._latlng.lat, lng: layer._latlng.lng, popup: String(popup).substring(0, 300) });
                    }
                }
                return info;
            }""")

            print(f"🗺️ Map probe: found={map_info['found']}, markers={len(map_info.get('markers',[]))}")

            # === Click-to-locate ===
            click_coords = {}
            click_dms_coords = {}
            
            # === Ghép nối dữ liệu ===
            marker_by_id = {str(m["id"]): m for m in map_info.get("markers",[]) if m.get("id")}
            unmatched_markers = [m for m in map_info.get("markers", []) if not m.get("id")]

            for ev in dom_events:
                eid = str(ev.get("id", ""))
                if not eid or eid in seen_ids:
                    continue
                seen_ids.add(eid)

                lat, lon = None, None
                title = ev.get("title", "")
                raw_time = ev.get("time", "")

                if ev.get("lat") and ev.get("lon"):
                    try:
                        lat, lon = float(ev.get("lat")), float(ev.get("lon"))
                    except ValueError:
                        pass

                if lat is None:
                    dms_lat, dms_lon = extract_dms_coordinates(raw_time)
                    if dms_lat is not None:
                        lat, lon = dms_lat, dms_lon

                time_str = clean_time_str(raw_time)

                if lat is None and eid not in marker_by_id and title:
                    title_clean = re.sub(r'<[^>]+>', '', title)
                    title_clean = re.sub(r'\s+', ' ', title_clean).strip()
                    if len(title_clean) > 15:
                        search_str = title_clean[:30].lower()
                        for m in unmatched_markers:
                            popup_clean = re.sub(r'<[^>]+>', '', m.get("popup", ""))
                            popup_clean = re.sub(r'\s+', ' ', popup_clean).strip().lower()
                            if search_str in popup_clean:
                                marker_by_id[eid] = m
                                break

                if lat is None and eid in marker_by_id:
                    lat = marker_by_id[eid].get("lat")
                    lon = marker_by_id[eid].get("lng")

                if lat is None and eid in api_coords:
                    lat = api_coords[eid].get("lat")
                    lon = api_coords[eid].get("lng")

                events_data.append({
                    "id": eid,
                    "title": title,
                    "time": time_str,
                    "source": ev.get("source", ""),
                    "coordinates": {
                        "lat": float(lat) if lat is not None else None,
                        "lon": float(lon) if lon is not None else None
                    }
                })

            has_coords = sum(1 for e in events_data if e["coordinates"]["lat"] is not None)
            print(f"🎯 Có tọa độ: {has_coords}/{len(events_data)}")

        except Exception as e:
            print(f"❌ Lỗi trong quá trình crawl: {e}")
        finally:
            browser.close()

    # Lọc bỏ events không có title
    events_data = [e for e in events_data if e.get("title")]
    has_coords = sum(1 for e in events_data if e["coordinates"]["lat"] is not None)
    
    print(f"✅ Kết quả cuối: {len(events_data)} events, {has_coords} có tọa độ")

    # ========= ĐỊNH TUYẾN ĐƯỜNG DẪN VÀ LƯU FILE =========
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Lùi về 1 cấp thư mục để vào /backend, sau đó tới /data
    backend_dir = os.path.dirname(current_dir)
    save_path = os.path.join(backend_dir, 'data', 'iran-events-latest.json')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # Bọc dữ liệu thành 1 Object giống format của file Security Advisories 
    result = {
        'fetchedAt': datetime.now().isoformat(),
        'totalCount': len(events_data),
        'source': url,
        'events': events_data
    }

    with open(save_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
        
    print(f"💾 Đã lưu vào: {save_path}")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 LIVEUAMAP EVENTS CRAWLER")
    print("=" * 60)
    TARGET_URL = "https://iran.liveuamap.com/"
    crawl_liveuamap(TARGET_URL)
    print("=" * 60)