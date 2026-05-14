import json
import time
import re
import urllib.request
import urllib.parse
from playwright.sync_api import sync_playwright
import os



def clean_time_str(raw):
    """Loai bo chu 'source' bi dinh vao cuoi time string, va bo text toa do."""
    raw = re.sub(r'\s*source\s*$', '', raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*-\s*\d+°\d+['’′][NS]\s+\d+°\d+['’′][EW]", '', raw)
    return raw.strip()

def extract_dms_coordinates(text):
    """Trich xuat toa do dang do-phut (VD: 35°41'N 51°22'E)."""
    match = re.search(r"(\d+)°(\d+)['’′]([NS])\s+(\d+)°(\d+)['’′]([EW])", text)
    if match:
        lat_d, lat_m, lat_dir, lon_d, lon_m, lon_dir = match.groups()
        lat = float(lat_d) + float(lat_m)/60.0
        if lat_dir == 'S': lat = -lat
        lon = float(lon_d) + float(lon_m)/60.0
        if lon_dir == 'W': lon = -lon
        return round(lat, 6), round(lon, 6)
    return None, None


def crawl_liveuamap(url, output_file):
    print(f"Bat dau crawl du lieu tu: {url}")
    events_data = []
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
            print("Da tai trang, cho feed hien thi...")

            try:
                page.wait_for_selector(
                    "#feedler, .feedler, .event-list", timeout=30000
                )
            except Exception:
                print("Khong tim thay #feedler, cho networkidle...")
                page.wait_for_load_state("networkidle", timeout=30000)

            # Cuon de kich hoat lazy-load
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
                var results = [];
                var items = document.querySelectorAll(
                    '.sourcees, .event, [data-id]'
                );
                items.forEach(function(el) {
                    var id = el.getAttribute('data-id') || '';
                    var titleEl = el.querySelector(
                        '.title, .event-title, h3, h4'
                    );
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
            print(f"  DOM: {len(dom_events)} events")

            # === Scan HTML content for hidden JSON coordinates ===
            try:
                html_content = page.content()
                # Pattern 1: {"id":123, "lat": 1.2, "lng": 3.4}
                for m in re.finditer(r'\{[^\}]*"id"\s*:\s*"?(\d+)"?[^\}]*"lat(?:itude)?"\s*:\s*([0-9.-]+)[^\}]*"l(?:on|ng)(?:gitude)?"\s*:\s*([0-9.-]+)[^\}]*\}', html_content, re.IGNORECASE):
                    api_coords[m.group(1)] = {"lat": float(m.group(2)), "lng": float(m.group(3))}
                for m in re.finditer(r'\{[^\}]*"lat(?:itude)?"\s*:\s*([0-9.-]+)[^\}]*"l(?:on|ng)(?:gitude)?"\s*:\s*([0-9.-]+)[^\}]*"id"\s*:\s*"?(\d+)"?[^\}]*\}', html_content, re.IGNORECASE):
                    api_coords[m.group(3)] = {"lat": float(m.group(1)), "lng": float(m.group(2))}
                # Pattern 2: data-id="..." data-lat="..." data-lng="..."
                for m in re.finditer(r'data-id=["\'](\d+)["\'].*?data-lat=["\']([0-9.-]+)["\'].*?data-l(?:on|ng)=["\']([0-9.-]+)["\']', html_content, re.IGNORECASE | re.DOTALL):
                    api_coords[m.group(1)] = {"lat": float(m.group(2)), "lng": float(m.group(3))}
                # Pattern 3: GeoJSON features
                for m in re.finditer(r'"type"\s*:\s*"Feature".*?"coordinates"\s*:\s*\[([0-9.-]+)\s*,\s*([0-9.-]+)\].*?"id"\s*:\s*"?(\d+)"?', html_content, re.IGNORECASE | re.DOTALL):
                    api_coords[m.group(3)] = {"lat": float(m.group(2)), "lng": float(m.group(1))}
            except Exception as e:
                pass

            # === Probe map: tim Leaflet instance + debug marker properties ===
            map_info = page.evaluate("""() => {
                var info = {found: false, type: '', markers: [], debug_sample: null};
                var mapObj = null;
                // Tim qua container element
                var containers = document.querySelectorAll(
                    '.leaflet-container, #map, #mapid, [id*=map]'
                );
                for (var i = 0; i < containers.length; i++) {
                    var el = containers[i];
                    for (var key in el) {
                        try {
                            if (key.indexOf('leaflet') >= 0 || key.indexOf('_map') >= 0) {
                                var val = el[key];
                                if (val && typeof val === 'object' && val._layers) {
                                    mapObj = val;
                                    info.type = 'leaflet-dom-' + key;
                                    break;
                                }
                            }
                        } catch(e) {}
                    }
                    if (mapObj) break;
                }
                // Tim qua global variables
                if (!mapObj) {
                    var names = [
                        'map','lmap','lmaps','myMap','mainMap',
                        'mapInstance','leafletMap','_map'
                    ];
                    for (var n = 0; n < names.length; n++) {
                        try {
                            var obj = eval(names[n]);
                            if (obj && obj._layers) {
                                mapObj = obj;
                                info.type = 'global-' + names[n];
                                break;
                            }
                            if (obj && typeof obj === 'object') {
                                for (var k in obj) {
                                    if (obj[k] && obj[k]._layers) {
                                        mapObj = obj[k];
                                        info.type = 'global-' + names[n] + '.' + k;
                                        break;
                                    }
                                }
                            }
                        } catch(e) {}
                        if (mapObj) break;
                    }
                }
                // Scan window cho bat ky Leaflet map nao
                if (!mapObj) {
                    for (var wk in window) {
                        try {
                            var wv = window[wk];
                            if (wv && typeof wv === 'object'
                                && wv._layers && wv._zoom !== undefined
                                && typeof wv.getCenter === 'function') {
                                mapObj = wv;
                                info.type = 'window-' + wk;
                                break;
                            }
                        } catch(e) {}
                    }
                }
                if (!mapObj) return info;
                info.found = true;

                var firstDumped = false;
                // Lay tat ca markers
                for (var lid in mapObj._layers) {
                    var layer = mapObj._layers[lid];
                    if (layer && layer._latlng) {
                        // Debug: dump first marker's properties
                        if (!firstDumped) {
                            var props = {};
                            try {
                                var optKeys = Object.keys(layer.options || {});
                                props.option_keys = optKeys;
                                props.options_sample = {};
                                optKeys.forEach(function(ok) {
                                    try {
                                        var v = layer.options[ok];
                                        if (typeof v !== 'function' && typeof v !== 'object') {
                                            props.options_sample[ok] = String(v);
                                        }
                                    } catch(e) {}
                                });
                            } catch(e) {}
                            try {
                                var layerKeys = Object.keys(layer);
                                props.layer_keys = layerKeys.filter(function(k) {
                                    return k.charAt(0) !== '_' || k === '_eventId' || k === '_id';
                                });
                                props.all_underscore_keys = layerKeys.filter(function(k) {
                                    return k.charAt(0) === '_';
                                });
                            } catch(e) {}
                            try {
                                if (layer._icon) {
                                    props.icon_class = layer._icon.className || '';
                                    props.icon_data_attrs = {};
                                    var attrs = layer._icon.attributes;
                                    for (var a = 0; a < attrs.length; a++) {
                                        if (attrs[a].name.indexOf('data-') === 0) {
                                            props.icon_data_attrs[attrs[a].name] = attrs[a].value;
                                        }
                                    }
                                }
                            } catch(e) {}
                            info.debug_sample = props;
                            firstDumped = true;
                        }

                        // Try many ID paths
                        var mid = '';
                        try { mid = String(layer.options.id || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.feature.properties.id || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.feature.id || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer._eventId || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.options.data_id || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.options.eventId || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.options.newsId || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.options.event || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.options.nid || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer._id || ''); } catch(e) {}
                        if (!mid) try { mid = String(layer.options.name || ''); } catch(e) {}
                        // Try extracting from icon element data attributes
                        if (!mid) try {
                            if (layer._icon) {
                                mid = layer._icon.getAttribute('data-id') || '';
                                if (!mid) mid = layer._icon.getAttribute('data-event-id') || '';
                                if (!mid) mid = layer._icon.getAttribute('data-nid') || '';
                            }
                        } catch(e) {}
                        // Try Leaflet internal ID
                        if (!mid) try { mid = String(layer._leaflet_id || ''); } catch(e) {}

                        var popup = '';
                        try {
                            if (layer._popup) popup = layer._popup._content || '';
                        } catch(e) {}
                        info.markers.push({
                            id: mid,
                            lat: layer._latlng.lat,
                            lng: layer._latlng.lng,
                            popup: String(popup).substring(0, 300)
                        });
                    }
                }
                return info;
            }""")

            print(f"  Map probe: found={map_info['found']}, "
                  f"type={map_info.get('type','')}, "
                  f"markers={len(map_info.get('markers', []))}")

            # Print debug info about marker properties
            if map_info.get('debug_sample'):
                ds = map_info['debug_sample']
                print(f"  [DEBUG] Marker option keys: {ds.get('option_keys', [])}")
                print(f"  [DEBUG] Options sample: {ds.get('options_sample', {})}")
                print(f"  [DEBUG] Layer keys: {ds.get('layer_keys', [])}")
                print(f"  [DEBUG] Underscore keys: {ds.get('all_underscore_keys', [])}")
                if ds.get('icon_data_attrs'):
                    print(f"  [DEBUG] Icon data-attrs: {ds.get('icon_data_attrs', {})}")
                if ds.get('icon_class'):
                    print(f"  [DEBUG] Icon class: {ds.get('icon_class','')}")

            # Print first 3 marker IDs to check matching
            for i, m in enumerate(map_info.get('markers', [])[:3]):
                print(f"  [DEBUG] Marker {i}: id='{m['id']}' lat={m['lat']} "
                      f"lng={m['lng']} popup='{m['popup'][:80]}...'")

            # === Click-to-locate ===
            click_coords = {}
            click_dms_coords = {}
            if dom_events:
                print("  Click-to-locate: trying...")
                click_errors = 0
                click_ok = 0

                # Close any initial overlay/popup/cookie banner and prevent link navigations
                page.evaluate("""() => {
                    var closeBtns = document.querySelectorAll(
                        '.close, .btn-close, [class*="close"], .leaflet-popup-close-button, button[aria-label="Close"]'
                    );
                    closeBtns.forEach(function(b) { try { b.click(); } catch(e) {} });
                    // Close cookie/ad banners
                    var banners = document.querySelectorAll(
                        '[class*="cookie"], [class*="consent"], [class*="banner"], [class*="advertising"]'
                    );
                    banners.forEach(function(b) {
                        try { b.style.display = 'none'; } catch(e) {}
                    });
                    // Prevent link navigations during click-to-locate
                    window.addEventListener('click', function(e) {
                        var a = e.target.closest('a');
                        if (a && a.href && !a.href.includes('javascript:')) {
                            e.preventDefault();
                        }
                    }, true);
                }""")
                time.sleep(0.5)

                for idx, ev in enumerate(dom_events[:30]):
                    eid = ev.get("id", "")
                    if not eid:
                        continue
                    try:
                        sel = f'[data-id="{eid}"]'
                        el = page.query_selector(sel)
                        if not el:
                            continue

                        # Scroll element into view with a small timeout
                        try:
                            el.scroll_into_view_if_needed(timeout=1000)
                        except Exception:
                            pass
                        time.sleep(0.1)

                        # Record pre-click map center
                        pre_center = page.evaluate("""() => {
                            try {
                                var c = map.getCenter();
                                return {lat: c.lat, lng: c.lng};
                            } catch(e) { return null; }
                        }""")

                        # Click with force to bypass overlays
                        try:
                            el.click(force=True, timeout=1000)
                        except Exception:
                            try:
                                el.evaluate("node => node.click()")
                            except Exception:
                                pass
                        time.sleep(1)
                        click_ok += 1

                        # Method 1: Read DMS from page content after click
                        popup_text = page.evaluate(r"""() => {
                            var dmsRe = /\d+[°]\d+[''\u2019\u2032][NS]\s+\d+[°]\d+[''\u2019\u2032][EW]/;
                            // Check all text nodes for DMS pattern
                            var body = document.body ? (document.body.innerText || document.body.textContent || '') : '';
                            if (dmsRe.test(body)) {
                                // Find smallest element containing DMS
                                var all = document.querySelectorAll('*');
                                for (var j = all.length - 1; j >= 0; j--) {
                                    try {
                                        var t = all[j].innerText || all[j].textContent || '';
                                        if (dmsRe.test(t) && t.length < 500) return t;
                                    } catch(e) {}
                                }
                                return body.substring(0, 3000);
                            }
                            return '';
                        }""")
                        if popup_text:
                            dms_lat, dms_lon = extract_dms_coordinates(popup_text)
                            if dms_lat is not None:
                                click_dms_coords[eid] = {"lat": dms_lat, "lng": dms_lon}
                                if idx < 3:
                                    print(f"    [DEBUG] DMS found for {eid}: "
                                          f"{dms_lat}, {dms_lon}")

                        # Method 2: Check if map center changed, popup opened, or item became active (same location)
                        if eid not in click_dms_coords:
                            post_center = el.evaluate("""(node) => {
                                try {
                                    var c = map.getCenter();
                                    var popup = document.querySelector('.leaflet-popup');
                                    var isActive = node.classList.contains('active') || node.classList.contains('selected');
                                    return {lat: c.lat, lng: c.lng, has_popup: !!popup, is_active: isActive};
                                } catch(e) { return null; }
                            }""")
                            if post_center and pre_center:
                                center_changed = (abs(post_center['lat'] - pre_center['lat']) > 0.00001
                                                  or abs(post_center['lng'] - pre_center['lng']) > 0.00001)
                                if center_changed or post_center.get('has_popup') or post_center.get('is_active'):
                                    click_coords[eid] = post_center

                        # Method 3: Check API intercepted coords
                        if eid not in click_dms_coords and eid in api_coords:
                            click_dms_coords[eid] = api_coords[eid]

                        # Close popup/overlay before next click
                        page.evaluate("""() => {
                            // Gracefully close Leaflet popup
                            try { if (typeof map !== 'undefined' && map.closePopup) map.closePopup(); } catch(e) {}
                            
                            var closeBtn = document.querySelector(
                                '.close, .btn-close, .leaflet-popup-close-button, '
                                + '[class*="close"], button[aria-label="Close"]'
                            );
                            if (closeBtn) closeBtn.click();
                            // Force remove popups
                            var popups = document.querySelectorAll('.leaflet-popup');
                            popups.forEach(p => p.remove());
                            // Press Escape
                            document.dispatchEvent(
                                new KeyboardEvent('keydown', {key: 'Escape', keyCode: 27})
                            );
                        }""")
                        time.sleep(0.3)

                    except Exception as e:
                        click_errors += 1
                        if click_errors <= 3:
                            print(f"    [ERROR] Click failed for {eid}: {e}")

                print(f"  Click-to-locate: {click_ok} clicks OK, "
                      f"{click_errors} errors, "
                      f"{len(click_dms_coords)} DMS coords, "
                      f"{len(click_coords)} center coords")
                print(f"  API intercepted coords: {len(api_coords)}")

            # === Ghep noi du lieu ===
            marker_by_id = {}
            unmatched_markers = []
            for m in map_info.get("markers", []):
                if m.get("id"):
                    marker_by_id[str(m["id"])] = m
                else:
                    unmatched_markers.append(m)

            print(f"  Marker matching: {len(marker_by_id)} with ID, "
                  f"{len(unmatched_markers)} without ID")

            for ev in dom_events:
                eid = str(ev.get("id", ""))
                if not eid or eid in seen_ids:
                    continue
                seen_ids.add(eid)

                lat, lon = None, None
                title = ev.get("title", "")
                raw_time = ev.get("time", "")

                # Uu tien tu DOM attributes
                dom_lat = ev.get("lat")
                dom_lon = ev.get("lon")
                if dom_lat and dom_lon:
                    try:
                        lat, lon = float(dom_lat), float(dom_lon)
                    except ValueError:
                        pass

                # Check DMS in time string
                if lat is None:
                    dms_lat, dms_lon = extract_dms_coordinates(raw_time)
                    if dms_lat is not None:
                        lat, lon = dms_lat, dms_lon

                time_str = clean_time_str(raw_time)

                # Thu match marker by title neu khong co ID
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

                # Uu tien 1: marker match by id or title
                if lat is None and eid in marker_by_id:
                    lat = marker_by_id[eid].get("lat")
                    lon = marker_by_id[eid].get("lng")

                    # Extract DMS from popup as a fallback
                    if lat is None:
                        dms_p_lat, dms_p_lon = extract_dms_coordinates(
                            marker_by_id[eid].get("popup", "")
                        )
                        if dms_p_lat is not None:
                            lat, lon = dms_p_lat, dms_p_lon

                # Uu tien 2: API intercepted coords
                if lat is None and eid in api_coords:
                    lat = api_coords[eid].get("lat")
                    lon = api_coords[eid].get("lng")

                # Uu tien 3: DMS from popup (click)
                if lat is None and eid in click_dms_coords:
                    lat = click_dms_coords[eid]["lat"]
                    lon = click_dms_coords[eid]["lng"]

                # Uu tien 4: map center fallback
                if lat is None and eid in click_coords:
                    lat = click_coords[eid]["lat"]
                    lon = click_coords[eid]["lng"]

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

            print(f"\nTruoc geocoding: {len(events_data)} events")
            has_coords = sum(
                1 for e in events_data if e["coordinates"]["lat"] is not None
            )
            print(f"  Co toa do: {has_coords}, Thieu: {len(events_data) - has_coords}")

        except Exception as e:
            print(f"Loi trong qua trinh crawl: {e}")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()



    # Loc bo events khong co title
    events_data = [e for e in events_data if e.get("title")]

    has_coords = sum(
        1 for e in events_data if e["coordinates"]["lat"] is not None
    )
    print(f"\nKet qua cuoi: {len(events_data)} events, "
          f"{has_coords} co toa do")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events_data, f, ensure_ascii=False, indent=2)
    print(f"Da luu vao: {output_file}")


def _extract_coords_from_json(data, coords_dict):
    """Recursively extract coordinate data from API JSON responses."""
    if isinstance(data, dict):
        lat = data.get('lat') or data.get('latitude')
        lon = (data.get('lon') or data.get('lng')
               or data.get('longitude'))
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


def extract_from_xhr(data, events_list, seen_ids):
    """Trich xuat events tu XHR JSON (GeoJSON/flat list)."""
    if isinstance(data, list):
        for item in data:
            extract_from_xhr(item, events_list, seen_ids)
    elif isinstance(data, dict):
        if data.get('type') == 'Feature' and isinstance(data.get('geometry'), dict):
            geom = data['geometry']
            props = data.get('properties', {})
            if (geom.get('type') == 'Point'
                    and isinstance(geom.get('coordinates'), list)
                    and len(geom['coordinates']) >= 2):
                lon, lat = geom['coordinates'][0], geom['coordinates'][1]
                title = props.get('title') or props.get('name') or ""
                eid = str(props.get('id') or data.get('id') or "")
                if title and eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    events_list.append({
                        "id": eid,
                        "title": str(title),
                        "time": str(props.get('time') or props.get('date') or ""),
                        "source": str(props.get('source') or props.get('link') or ""),
                        "coordinates": {"lat": float(lat), "lon": float(lon)}
                    })
        elif data.get('type') == 'FeatureCollection':
            for feat in data.get('features', []):
                extract_from_xhr(feat, events_list, seen_ids)
        for val in data.values():
            if isinstance(val, (list, dict)):
                extract_from_xhr(val, events_list, seen_ids)


if __name__ == "__main__":
    TARGET_URL = "https://iran.liveuamap.com/"
    
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    save_path = os.path.join(backend_dir, 'data', 'iran-events-latest.json')
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    crawl_liveuamap(TARGET_URL, save_path)