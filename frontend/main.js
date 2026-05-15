
// frontend/main.js - Frontend logic for World Monitor Dashboard
const API_URL = 'http://localhost:3000/api/events';
const REFRESH_URL = 'http://localhost:3000/api/refresh';

let myMap2D;
let globalEventData = [];

function groupEventsByLocation(data) {
    const grouped = {};
    data.forEach(event => {
        const lat = parseFloat(event.lat);
        const lng = parseFloat(event.lng);
        if (isNaN(lat) || isNaN(lng)) return;

        const key = `${lat},${lng}`;
        if (!grouped[key]) {
            grouped[key] = { lat, lng, location: event.location, events: [] };
        }
        grouped[key].events.push(event);
    });

    return Object.values(grouped).map(group => {
        group.events.sort((a, b) => new Date(b.date) - new Date(a.date));
        return group;
    });
}

async function initDashboard() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        globalEventData = data.sort((a, b) => new Date(b.date) - new Date(a.date));

        const loadingEl = document.getElementById('loading-status');
        if(loadingEl) loadingEl.style.display = 'none';

        if (myMap2D) {
            myMap2D.eachLayer((layer) => {
                if (layer instanceof L.CircleMarker) myMap2D.removeLayer(layer);
            });
            drawMarkers2D(globalEventData);
        } else {
            renderMap2D(globalEventData); 
        }
    } catch (error) {
        console.error("LỖI LOGIC TẢI BẢN ĐỒ:", error);
    }
}

function renderMap2D(eventData) {
    myMap2D = L.map('map-2d').setView([32.42, 53.68], 5);

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap & CartoDB'
    }).addTo(myMap2D);

    drawMarkers2D(eventData);

    setTimeout(() => {
        myMap2D.invalidateSize();
    }, 500);
}

function drawMarkers2D(eventData) {
    const groupedData = groupEventsByLocation(eventData);

    groupedData.forEach(group => {
        const radiusSize = Math.min(5 + (group.events.length * 0.5), 15);

        const marker = L.circleMarker([group.lat, group.lng], {
            radius: radiusSize, 
            fillColor: "#ff4444", 
            color: "#ff0000", 
            weight: 1, 
            opacity: 1, 
            fillOpacity: 0.8
        }).addTo(myMap2D);

        let eventsHtml = group.events.map(e => `
            <div style="border-bottom: 1px dotted #555; padding-bottom: 8px; margin-bottom: 8px;">
                <strong style="font-size: 12px; color: #ffaa00;">▶ ${e.date}</strong><br>
                <span style="font-size: 13px; color: #000; line-height: 1.4;">${e.notes || 'Không có mô tả.'}</span>
            </div>
        `).join('');

        const popupHTML = `
            <div style="color: #fff; min-width: 250px; max-width: 320px; font-family: sans-serif;">
                <h4 style="margin: 0 0 10px 0; color: #ff4444; font-size: 15px; border-bottom: 1px solid #ff4444; padding-bottom: 5px;">
                    📍 ${group.location || 'Khu vực không xác định'} 
                    <span style="font-size:12px; color:#aaa">(${group.events.length})</span>
                </h4>
                <div class="event-scroll-list" style="max-height: 250px; overflow-y: auto; padding-right: 8px;">
                    ${eventsHtml}
                </div>
            </div>
        `;
        
        marker.bindPopup(popupHTML);
    });
}

async function fetchOilData() {
    try {
        const response = await fetch('http://localhost:3000/api/oil');
        const oilData = await response.json();
        const tickerEl = document.getElementById('oil-ticker');
        
        if (oilData.length === 0) {
            tickerEl.innerHTML = '<span style="color:gray;">Chưa có dữ liệu (Hãy bấm SYNC OIL)</span>';
            return;
        }

        tickerEl.innerHTML = ''; 
        oilData.forEach(oil => {
            const isUp = oil.change_pct >= 0;
            const color = isUp ? '#00ff00' : '#ff4444';
            const arrow = isUp ? '▲' : '▼';
            const span = document.createElement('span');
            span.innerHTML = `<strong style="color: #ccc;">${oil.name}</strong> <span style="color: ${color};">${oil.price} ${arrow} ${Math.abs(oil.change_pct)}%</span>&nbsp;&nbsp;&nbsp;&nbsp;`;
            tickerEl.appendChild(span);
        });
    } catch (error) {
        console.error("Lỗi lấy giá dầu:", error);
    }
}

function setupRefreshButtons() {
    const btnAcled = document.getElementById('btn-refresh-acled');
    const btnOil = document.getElementById('btn-refresh-oil');

    async function handleSync(btnElement, url, type) {
        const originalText = btnElement.innerText;
        const originalColor = btnElement.style.color;
        
        btnElement.innerText = '⏳ SYNCING...';
        btnElement.style.backgroundColor = 'rgba(255,255,255,0.1)';
        btnElement.disabled = true;

        try {
            const response = await fetch(url, { method: 'POST' });
            if (!response.ok) throw new Error("API lỗi");
            
            if (type === 'acled') await initDashboard(); 
            if (type === 'oil') await fetchOilData(); 

            btnElement.innerText = '✅ SUCCESS';
            setTimeout(() => {
                btnElement.innerText = originalText;
                btnElement.style.backgroundColor = 'transparent';
                btnElement.disabled = false;
            }, 2000);
        } catch (error) {
            console.error(`Lỗi Sync ${type}:`, error);
            btnElement.innerText = '❌ FAIL';
            btnElement.style.color = '#ff4444';
            setTimeout(() => {
                btnElement.innerText = originalText;
                btnElement.style.color = originalColor;
                btnElement.disabled = false;
            }, 2000);
        }
    }

    btnAcled.addEventListener('click', () => handleSync(btnAcled, 'http://localhost:3000/api/refresh/acled', 'acled'));
    btnOil.addEventListener('click', () => handleSync(btnOil, 'http://localhost:3000/api/refresh/oil', 'oil'));
}

// Webcam data
const WEBCAM_FEEDS = [
    { id: 'tehran', city: 'Tehran', country: 'Iran', region: 'iran', videoId: 'gmtlJ_m2r5A' },
    { id: 'israel-cam', city: 'Tel Aviv', country: 'Israel', region: 'iran', videoId: 'fIurYTprwzg' },
    { id: 'jerusalem', city: 'Jerusalem', country: 'Israel', region: 'middle-east', videoId: 'e34xb-Fbl0U' },
    { id: 'beirut', city: 'Beirut', country: 'Lebanon', region: 'middle-east', videoId: 'djF-Lkgfp6k' },
    { id: 'washington', city: 'Washington DC', country: 'USA', region: 'americas', videoId: '1wV9lLe14aU' },
    { id: 'new-york', city: 'New York', country: 'USA', region: 'americas', videoId: '4qyZLflp-sI' }
];

let webcamViewMode = 'grid';
let activeWebcamFeed = WEBCAM_FEEDS[0];
let securityAdvisories = [];
let securityFilter = 'all';

// Render Webcams
function renderWebcams() {
    const container = document.getElementById('webcam-content');
    if (!container) return;
    
    if (webcamViewMode === 'grid') {
        const grid = document.createElement('div');
        grid.className = 'webcam-grid';
        
        WEBCAM_FEEDS.slice(0, 4).forEach(feed => {
            const cell = document.createElement('div');
            cell.className = 'webcam-cell';
            cell.innerHTML = `
                <div class="webcam-cell-label">🔴 LIVE ${feed.city}</div>
                <iframe class="webcam-iframe" 
                    src="https://www.youtube.com/embed/${feed.videoId}?autoplay=1&mute=1&controls=0&modestbranding=1&playsinline=1"
                    allow="autoplay; encrypted-media"
                    frameborder="0"></iframe>
            `;
            grid.appendChild(cell);
        });
        container.innerHTML = '';
        container.appendChild(grid);
    } else {
        container.innerHTML = `
            <div class="webcam-single">
                <iframe class="webcam-iframe" 
                    src="https://www.youtube.com/embed/${activeWebcamFeed.videoId}?autoplay=1&mute=1&controls=0&modestbranding=1&playsinline=1"
                    allow="autoplay; encrypted-media"
                    frameborder="0"></iframe>
            </div>
            <div class="webcam-switcher" id="webcam-switcher"></div>
        `;
        
        const switcher = document.getElementById('webcam-switcher');
        if (switcher) {
            WEBCAM_FEEDS.forEach(feed => {
                const btn = document.createElement('button');
                btn.className = `webcam-feed-btn${feed.id === activeWebcamFeed.id ? ' active' : ''}`;
                btn.textContent = feed.city;
                btn.onclick = () => {
                    activeWebcamFeed = feed;
                    renderWebcams();
                };
                switcher.appendChild(btn);
            });
        }
    }
}

// Load Security Advisories từ API
async function loadSecurityAdvisories() {
    try {
        const response = await fetch('http://localhost:3000/api/security');
        const data = await response.json();
        securityAdvisories = data.advisories || [];
        renderSecurityAdvisories();
    } catch (error) {
        console.error('Error loading security advisories:', error);
        document.getElementById('security-content').innerHTML = '<div class="sec-empty">⚠️ Failed to load security data</div>';
    }
}

// Render Security Advisories
function renderSecurityAdvisories() {
    const container = document.getElementById('security-content');
    if (!container) return;
    
    let filtered = securityAdvisories;
    
    if (securityFilter === 'critical') {
        filtered = securityAdvisories.filter(a => a.level === 'do-not-travel' || a.level === 'reconsider');
    } else if (securityFilter === 'US') {
        filtered = securityAdvisories.filter(a => a.sourceCountry === 'US');
    }
    
    if (filtered.length === 0) {
        container.innerHTML = '<div class="sec-empty">No security advisories for selected filter</div>';
        return;
    }
    
    const itemsHtml = filtered.slice(0, 15).map(adv => {
        const levelClass = adv.level === 'do-not-travel' ? 'do-not-travel' : 
                          (adv.level === 'reconsider' ? 'reconsider' : 'caution');
        const levelLabel = adv.level === 'do-not-travel' ? 'DO NOT TRAVEL' :
                          (adv.level === 'reconsider' ? 'RECONSIDER' : 'CAUTION');
        
        // BỎ 2 DÒNG TỰ TÍNH TOÁN CŨ ĐI
        // Chỉ cần lấy thẳng chuỗi timeAgo đã được Python tính toán sẵn từ file JSON
        const timeAgo = adv.timeAgo;
        
        return `
            <div class="sec-item">
                <div class="sec-item-header">
                    <span class="sec-badge ${levelClass}">${levelLabel}</span>
                    <span class="sec-source">🇺🇸 ${adv.source}</span>
                </div>
                <a href="${adv.link}" target="_blank" class="sec-title">${adv.title}</a>
                <div class="sec-description">${(adv.description || 'No details').substring(0, 150)}...</div>
                <div class="sec-time">📅 ${timeAgo}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = itemsHtml;
}

// Setup Webcam controls
function setupWebcamControls() {
    const gridBtn = document.getElementById('webcam-grid-view');
    const singleBtn = document.getElementById('webcam-single-view');
    const fullscreenBtn = document.getElementById('webcam-fullscreen');
    const panel = document.getElementById('webcam-panel');
    
    if (gridBtn) {
        gridBtn.onclick = () => {
            webcamViewMode = 'grid';
            gridBtn.classList.add('active');
            singleBtn.classList.remove('active');
            renderWebcams();
        };
    }
    
    if (singleBtn) {
        singleBtn.onclick = () => {
            webcamViewMode = 'single';
            singleBtn.classList.add('active');
            gridBtn.classList.remove('active');
            renderWebcams();
        };
    }
    
    if (fullscreenBtn && panel) {
        fullscreenBtn.onclick = () => {
            if (panel.requestFullscreen) panel.requestFullscreen();
            else if (panel.webkitRequestFullscreen) panel.webkitRequestFullscreen();
        };
    }
}

// Setup Security filters
function setupSecurityFilters() {
    const filters = document.querySelectorAll('.sec-filter');
    filters.forEach(btn => {
        btn.onclick = () => {
            filters.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            securityFilter = btn.dataset.filter;
            renderSecurityAdvisories();
        };
    });
}

// Refresh security data
async function refreshSecurityData() {
    const btn = document.getElementById('btn-refresh-security');
    const originalText = btn.innerText;
    btn.innerText = '⏳ SYNCING...';
    btn.disabled = true;
    
    try {
        await fetch('http://localhost:3000/api/refresh/security', { method: 'POST' });
        setTimeout(async () => {
            await loadSecurityAdvisories();
            btn.innerText = '✅ SUCCESS';
            setTimeout(() => {
                btn.innerText = originalText;
                btn.disabled = false;
            }, 2000);
        }, 3000);
    } catch (error) {
        btn.innerText = '❌ FAIL';
        setTimeout(() => {
            btn.innerText = originalText;
            btn.disabled = false;
        }, 2000);
    }
}

// Cập nhật setupRefreshButtons để thêm security
function setupAllRefreshButtons() {
    // Existing buttons
    const btnAcled = document.getElementById('btn-refresh-acled');
    const btnOil = document.getElementById('btn-refresh-oil');
    const btnSecurity = document.getElementById('btn-refresh-security');
    
    async function handleSync(btnElement, url, type) {
        const originalText = btnElement.innerText;
        btnElement.innerText = '⏳ SYNCING...';
        btnElement.disabled = true;
        
        try {
            const response = await fetch(url, { method: 'POST' });
            if (!response.ok) throw new Error("API lỗi");
            
            if (type === 'acled') await initDashboard();
            if (type === 'oil') await fetchOilData();
            if (type === 'security') {
                setTimeout(async () => {
                    await loadSecurityAdvisories();
                    btnElement.innerText = '✅ SUCCESS';
                    setTimeout(() => {
                        btnElement.innerText = originalText;
                        btnElement.disabled = false;
                    }, 2000);
                }, 3000);
                return;
            }
            
            btnElement.innerText = '✅ SUCCESS';
            setTimeout(() => {
                btnElement.innerText = originalText;
                btnElement.disabled = false;
            }, 2000);
        } catch (error) {
            btnElement.innerText = '❌ FAIL';
            setTimeout(() => {
                btnElement.innerText = originalText;
                btnElement.disabled = false;
            }, 2000);
        }
    }
    
    if (btnAcled) btnAcled.onclick = () => handleSync(btnAcled, 'http://localhost:3000/api/refresh/acled', 'acled');
    if (btnOil) btnOil.onclick = () => handleSync(btnOil, 'http://localhost:3000/api/refresh/oil', 'oil');
    if (btnSecurity) btnSecurity.onclick = () => handleSync(btnSecurity, 'http://localhost:3000/api/refresh/security', 'security');
}


// Thêm vào đầu file main.js
const API_BASE = 'http://localhost:3000/api';

// 1. TẢI VÀ RENDER LIVEUAMAP (BẢN ĐỒ + DANH SÁCH)
async function loadLiveuamap() {
    try {
        const res = await fetch(`${API_BASE}/liveuamap`);
        const data = await res.json();
        const events = data.events || [];

        // Render Marker lên bản đồ 2D (Nếu đang ở chế độ 2D)
        if (myMap2D) {
            events.forEach(ev => {
                const lat = ev.coordinates?.lat;
                const lon = ev.coordinates?.lon;
                if (lat && lon) {
                    L.circleMarker([lat, lon], {
                        radius: 6,
                        fillColor: "#ffaa00", // Màu cam đặc trưng Liveuamap
                        color: "#fff",
                        weight: 1,
                        fillOpacity: 0.9
                    }).addTo(myMap2D)
                      .bindPopup(`<b>LIVEUAMAP</b><br>${ev.title}<br><small>${ev.time}</small>`);
                }
            });
        }

        // Render List Panel
        const container = document.getElementById('liveua-content');
        container.innerHTML = events.slice(0, 20).map(ev => `
            <div class="liveua-item">
                <div style="color: #ffaa00; font-weight: bold; margin-bottom: 3px;">${ev.time}</div>
                <div>${ev.title}</div>
            </div>
        `).join('');
    } catch (e) { console.error("Liveuamap error:", e); }
}

// 2. TẢI VÀ RENDER TELEGRAM
async function loadTelegram() {
    try {
        const res = await fetch(`${API_BASE}/telegram?limit=15`);
        const data = await res.json();
        const container = document.getElementById('telegram-content');
        
        container.innerHTML = data.posts.map(post => `
            <div class="tg-item">
                <div class="tg-header">
                    <span class="tg-label">@${post.channel_label}</span>
                    <span class="tg-time">${post.time_ago}</span>
                </div>
                <div class="tg-text">${post.preview_text}</div>
                <a href="${post.url}" target="_blank" class="tg-link">View Original Post</a>
            </div>
        `).join('');
    } catch (e) { console.error("Telegram error:", e); }
}

// 3. TẢI VÀ RENDER POLYMARKET
async function loadPolymarket() {
    try {
        const res = await fetch(`${API_BASE}/polymarket`);
        const data = await res.json();
        const container = document.getElementById('polymarket-content');
        
        container.innerHTML = data.markets.map(m => `
            <div class="poly-item">
                <span class="poly-title">${m.title}</span>
                <div class="poly-stats">
                    <span class="poly-vol">${m.display_volume} Vol</span>
                    <div class="poly-bar-container">
                        <div class="poly-bar-fill" style="width: ${m.yes_price}%"></div>
                    </div>
                    <span class="poly-prob">${m.yes_price}%</span>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error("Polymarket error:", e); }
}


// Thêm vào đầu file main.js các biến quản lý OpenSky
let openskyLayerGroup = L.layerGroup();

// Tạo hàm để định nghĩa Icon máy bay
const createPlaneIcon = (color, heading) => {
    return L.divIcon({
        html: `<i class="fas fa-plane" style="color: ${color}; transform: rotate(${heading || 0}deg); font-size: 18px;"></i>`,
        className: 'custom-plane-icon',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });
};

// 1. TẢI VÀ RENDER OPENSKY
async function loadOpenSky() {
    try {
        const res = await fetch(`${API_BASE}/opensky`);
        const data = await res.json();
        const flights = data.flights || [];
        const summary = data.summary || {};

        // Cập nhật Posture Badge
        const postureEl = document.getElementById('opensky-posture');
        postureEl.className = 'posture-badge';
        if (summary.posture === 'CRITICAL') postureEl.classList.add('posture-critical');
        else if (summary.posture === 'ELEVATED') postureEl.classList.add('posture-elevated');
        postureEl.innerText = summary.posture;

        // Render lên bản đồ 2D
        if (myMap2D) {
            openskyLayerGroup.clearLayers();
            
            flights.forEach(f => {
                // Chuyển tọa độ sang số để tránh lỗi nếu API trả về string
                const lat = parseFloat(f.lat);
                const lon = parseFloat(f.lon);

                if (!isNaN(lat) && !isNaN(lon)) {
                    // 1. Chọn màu sắc
                    let color = "#007bff"; 
                    if (f.type === 'TANKER') color = "#d32f2f"; 
                    if (f.type === 'RECON') color = "#f57c00";  

                    // 2. Tạo Marker với Icon có kích thước cố định
                    const planeMarker = L.marker([lat, lon], {
                        icon: L.divIcon({
                            className: 'plane-marker-container', // Class để điều khiển trong CSS
                            html: `
                                <div class="plane-vessel" style="transform: rotate(${(f.heading || 0) - 45}deg);">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="${color}" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M21,16L21,14L13,9L13,3.5A1.5,1.5 0 0,0 11.5,2A1.5,1.5 0 0,0 10,3.5L10,9L2,14L2,16L10,13.5L10,18L8,19.5L8,21L11.5,20L15,21L15,19.5L13,18L13,13.5L21,16Z" />
                                    </svg>
                                </div>`,
                            iconSize: [24, 24],     // Cực kỳ quan trọng: Định nghĩa kích thước icon
                            iconAnchor: [12, 12]    // Đặt tâm icon vào đúng tọa độ
                        }),
                        zIndexOffset: 1000
                    }).addTo(openskyLayerGroup);

                    planeMarker.bindPopup(`
                        <div style="color:#333; min-width:150px;">
                            <b style="color:${color}; font-size:14px;">${f.callsign || 'N/A'}</b> [${f.type}]<br>
                            <hr style="margin:5px 0; border:0; border-top:1px solid #eee;">
                            <b>Alt:</b> ${f.alt} | <b>Base:</b> ${f.origin}
                        </div>
                    `);
                }
            });
            openskyLayerGroup.addTo(myMap2D);
        }

        // Render List Panel
        const container = document.getElementById('opensky-content');
        let html = '';

        // Hiển thị cảnh báo biên đội nếu có
        if (summary.hasStrikePackage) {
            html += `<div class="strike-alert">⚠️ WARNING: STRIKE PACKAGE (TANKER + RECON) DETECTED</div>`;
        }

        html += flights.map(f => `
            <div class="air-item">
                <div>
                    <div class="air-callsign">${f.callsign}</div>
                    <div class="air-type">${f.type} - ${f.origin}</div>
                </div>
                <div class="air-alt">${f.alt}</div>
            </div>
        `).join('');

        container.innerHTML = html || '<div class="placeholder">No military traffic detected</div>';

    } catch (e) {
        console.error("OpenSky error:", e);
    }
}

// 4. TẢI VÀ RENDER GDELT NEWS
async function loadGdelt() {
    try {
        const res = await fetch(`${API_BASE}/gdelt`); // Endpoint này khớp với GdeltPanel ở backend
        const data = await res.json();
        const articles = data.articles || [];
        const container = document.getElementById('gdelt-content');
        
        if (articles.length === 0) {
            container.innerHTML = '<div class="placeholder">No recent news found.</div>';
            return;
        }

        container.innerHTML = articles.slice(0, 15).map(art => `
            <div class="sec-item" style="border-left: 2px solid #58a6ff; background: rgba(88, 166, 255, 0.05); margin-bottom: 8px;">
                <div class="sec-item-header">
                    <span class="sec-source">📰 ${art.source || 'GDELT'}</span>
                    <span class="sec-time">${art.time_ago || 'Recently'}</span>
                </div>
                <a href="${art.url}" target="_blank" class="sec-title" style="color: #58a6ff;">${art.title}</a>
                <div style="display: flex; gap: 5px; margin-top: 5px;">
                    ${(art.themes || []).slice(0, 3).map(t => `<span style="font-size: 9px; background: #222; padding: 2px 5px; border-radius: 3px; color: #888;">#${t}</span>`).join('')}
                </div>
            </div>
        `).join('');
    } catch (e) { 
        console.error("GDELT error:", e); 
        document.getElementById('gdelt-content').innerHTML = '<div class="placeholder">Error loading GDELT.</div>';
    }
}

// 2. CẬP NHẬT HÀM setupNewRefreshButtons (Thêm OpenSky vào danh sách cấu hình)
// Tìm hàm setupNewRefreshButtons hiện tại và thêm vào mảng configs:
function setupNewRefreshButtons() {
    const configs = [
        { id: 'btn-refresh-liveuamap', url: '/refresh/liveuamap', callback: loadLiveuamap },
        { id: 'btn-refresh-telegram', url: '/refresh/telegram', callback: loadTelegram },
        { id: 'btn-refresh-polymarket', url: '/refresh/polymarket', callback: loadPolymarket },
        { id: 'btn-refresh-opensky', url: '/refresh/opensky', callback: loadOpenSky }, // MỚI
        { id: 'btn-refresh-gdelt', url: '/refresh/gdelt', callback: loadGdelt } 
    ];

    configs.forEach(cfg => {
        const btn = document.getElementById(cfg.id);
        if (!btn) return;
        btn.onclick = async () => {
            const originalText = btn.innerText;
            btn.innerText = '⏳...';
            btn.disabled = true;
            try {
                await fetch(`${API_BASE}${cfg.url}`, { method: 'POST' });
                setTimeout(async () => {
                    await cfg.callback();
                    btn.innerText = '✅ OK';
                    setTimeout(() => { 
                        // Trả lại text ban đầu (Ví dụ: ✈️ SYNC AIR INTEL)
                        btn.innerText = originalText; 
                        btn.disabled = false; 
                    }, 2000);
                }, 2000);
            } catch (e) { 
                btn.innerText = '❌'; 
                btn.disabled = false; 
                setTimeout(() => { btn.innerText = originalText; }, 2000);
            }
        };
    });

    const btnInsight = document.getElementById('btn-refresh-insight');
    if (btnInsight) {
        btnInsight.onclick = async () => {
            btnInsight.innerText = '⏳ AI is thinking...';
            btnInsight.disabled = true;
            document.getElementById('insight-content').innerHTML = `
                <div style="text-align:center; padding: 20px; color:#ffaa00; line-height: 1.5;">
                    <i class="fas fa-brain" style="font-size:24px; margin-bottom:10px;"></i><br>
                    AI is analyzing global data...<br>
                    <span style="font-size: 12px; color: #888;">(Please wait, this usually takes 15 - 45 seconds)</span>
                </div>`;
            
            try {
                // await fetch sẽ TỰ ĐỘNG ĐỢI cho đến khi backend (LLM) chạy xong và trả về kết quả
                const response = await fetch(`${API_BASE}/refresh/insight`, { method: 'POST' });
                
                if (!response.ok) throw new Error("API Error");

                // Ngay khi backend chạy xong, lập tức gọi hàm load lại dữ liệu
                await loadInsight();
                
                btnInsight.innerText = '✅ OK';
                setTimeout(() => { 
                    btnInsight.innerText = '🔄 SYNC'; 
                    btnInsight.disabled = false; 
                }, 3000);
                
            } catch (e) {
                console.error("AI Refresh Error:", e);
                btnInsight.innerText = '❌ FAILED';
                btnInsight.disabled = false;
                document.getElementById('insight-content').innerHTML = `
                    <div style="color:#ff4444; text-align:center; padding: 20px;">
                        ⚠️ Failed to generate AI insight. Please try again.
                    </div>`;
            }
        };
    }
}

// TẢI VÀ RENDER AI INSIGHT
async function loadInsight() {
    try {
        const res = await fetch(`${API_BASE}/insight`);
        const data = await res.json();
        const container = document.getElementById('insight-content');
        
        if (data.content && data.content !== "No insight generated yet.") {
            // Dùng thư viện marked.js để render văn bản AI ra HTML xịn xò
            container.innerHTML = marked.parse(data.content);
        } else {
            container.innerHTML = '<div class="placeholder" style="color:#aaa;">No analysis data available. Please click GET INSIGHT.</div>';
        }
    } catch (e) { 
        console.error("Insight error:", e); 
        document.getElementById('insight-content').innerHTML = '<div class="placeholder" style="color:red;">Failed to load AI Insight.</div>';
    }
}

function setupInsightButton() {
    const btnInsight = document.getElementById('btn-refresh-insight');
    if (!btnInsight) return; // Nếu không tìm thấy nút thì bỏ qua để không báo lỗi

    btnInsight.onclick = async () => {
        btnInsight.innerText = '⏳ THINKING ...';
        btnInsight.disabled = true;
        
        // Hiển thị trạng thái chờ trong khung Insight
        document.getElementById('insight-content').innerHTML = `
            <div style="text-align:center; padding: 20px; color:#ffaa00;">
                <i class="fas fa-brain" style="font-size:24px; margin-bottom:10px;"></i><br>
                AI is analyzing...<br>
                (Please wait 45 - 60 seconds)
            </div>`;
        
        try {
            // 1. Gọi API Backend kích hoạt Python chạy LLM
            await fetch(`${API_BASE}/refresh/insight`, { method: 'POST' });
            
            // 2. Đợi 45 giây để LLM làm thơ/phân tích xong
            setTimeout(async () => {
                // 3. Đọc lại file intelligence_insight.json và hiển thị lên màn hình
                await loadInsight();
                
                btnInsight.innerText = '✅ OK';
                setTimeout(() => { 
                    btnInsight.innerText = '🔄 GET INSIGHT'; 
                    btnInsight.disabled = false; 
                }, 3000);
            }, 45000); // 45000ms = 45 giây
            
        } catch (e) {
            btnInsight.innerText = '❌ FAILED';
            btnInsight.disabled = false;
        }
    };
}

function setupSyncAllButton() {
    const btnSyncAll = document.getElementById('btn-sync-all');
    if (!btnSyncAll) return;

    btnSyncAll.onclick = async () => {
        const originalText = btnSyncAll.innerText;
        btnSyncAll.innerText = '⏳ TRIGGERING CRAWLERS...';
        btnSyncAll.disabled = true;

        // Danh sách các API cần kích hoạt đồng thời
        const endpoints = [
            '/refresh/acled',
            '/refresh/liveuamap',
            '/refresh/telegram',
            '/refresh/polymarket',
            '/refresh/opensky',
            '/refresh/gdelt',
            '/refresh/oil',
            '/refresh/security'
        ];

        try {
            // Kích hoạt tất cả crawler chạy ngầm
            await Promise.all(endpoints.map(ep => 
                fetch(`${API_BASE}${ep}`, { method: 'POST' }).catch(err => console.error(`Lỗi: ${ep}`, err))
            ));

            btnSyncAll.innerText = '📡 FETCHING DATA...';
            
            // Chờ khoảng 6-8 giây để Backend cào xong và lưu file, sau đó load lại giao diện
            setTimeout(async () => {
                // Gọi lại các hàm load dữ liệu lên giao diện
                await initDashboard(); 
                fetchOilData();
                await loadSecurityAdvisories();
                await loadLiveuamap();
                await loadTelegram();
                await loadPolymarket();
                await loadOpenSky();
                await loadGdelt();

                btnSyncAll.innerText = '✅ SYSTEM UPDATED';
                setTimeout(() => {
                    btnSyncAll.innerText = originalText;
                    btnSyncAll.disabled = false;
                }, 3000);
            }, 100000); // 100000ms = 100 giây

        } catch (error) {
            btnSyncAll.innerText = '❌ SYNC FAILED';
            btnSyncAll.disabled = false;
        }
    };
}

// ============ OIL CHART MODAL ============
let oilChart = null;
let currentSymbol = 'BZ=F';
let cachedOilData = null;

async function loadOilChartData(symbol = 'BZ=F', forceRefresh = false) {
    if (cachedOilData && !forceRefresh) {
        console.log('Using cached oil data');
        if (symbol === 'both') {
            return {
                brent: cachedOilData['BZ=F'],
                wti: cachedOilData['CL=F']
            };
        }
        return cachedOilData[symbol];
    }
    
    try {
        console.log('Fetching fresh oil data...');
        const response = await fetch('http://localhost:3000/api/oil/history');
        const data = await response.json();
        
        if (data.error || !data.data) {
            console.error('No oil data:', data);
            return null;
        }
        
        cachedOilData = data.data;
        
        if (symbol === 'both') {
            return {
                brent: cachedOilData['BZ=F'],
                wti: cachedOilData['CL=F']
            };
        }
        return cachedOilData[symbol];
    } catch (error) {
        console.error('Failed to load oil data:', error);
        return null;
    }
}

function renderOilChart(oilData) {
    const canvas = document.getElementById('oil-chart-canvas');
    if (!canvas) {
        console.error('Canvas not found');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    
    if (oilChart) {
        oilChart.destroy();
        oilChart = null;
    }
    
    // Compare mode
    if (currentSymbol === 'both' && oilData.brent && oilData.wti) {
        const dates = oilData.brent.history.map(h => h.date.slice(5));
        const brentPrices = oilData.brent.history.map(h => h.price);
        const wtiPrices = oilData.wti.history.map(h => h.price);
        
        const allPrices = [...brentPrices, ...wtiPrices];
        const minPrice = Math.min(...allPrices) - 2;
        const maxPrice = Math.max(...allPrices) + 2;
        
        oilChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Brent Crude (USD)',
                        data: brentPrices,
                        borderColor: '#ffaa00',
                        backgroundColor: 'rgba(255, 170, 0, 0.05)',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointBackgroundColor: '#ffaa00',
                        pointBorderColor: '#fff',
                        fill: false,
                        tension: 0.2
                    },
                    {
                        label: 'WTI Crude (USD)',
                        data: wtiPrices,
                        borderColor: '#00ffaa',
                        backgroundColor: 'rgba(0, 255, 170, 0.05)',
                        borderWidth: 2.5,
                        pointRadius: 3,
                        pointBackgroundColor: '#00ffaa',
                        pointBorderColor: '#fff',
                        fill: false,
                        tension: 0.2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false, // SỬA THÀNH FALSE: Giúp biểu đồ fix cứng theo container, không bị nhảy chiều cao
                animation: {
                    duration: 500, // Rút ngắn thời gian vẽ (hoặc set thành 0 / false để tắt hẳn animation nếu không cần thiết)
                    easing: 'easeOutQuart' // Làm mượt hiệu ứng lúc kết thúc
                },
                layout: {
                    padding: 10 // Thêm khoảng lề cố định để trục X/Y không bị co giãn lúc hiện nhãn
                },
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { labels: { color: '#fff' } },
                    tooltip: { 
                        callbacks: { 
                            label: (ctx) => `${ctx.dataset.label}: $${ctx.raw} USD` 
                        }
                    }
                },
                scales: {
                    x: { 
                        ticks: { color: '#aaa', maxRotation: 45, autoSkip: true, maxTicksLimit: 8 }, 
                        grid: { color: '#222' } 
                    },
                    y: { 
                        ticks: { color: '#aaa', callback: v => '$' + v }, 
                        min: minPrice, 
                        max: maxPrice, 
                        grid: { color: '#222' } 
                    }
                }
            }
        });
        
        updateCompareStats(oilData.brent, oilData.wti);
        return;
    }
    
    // Single mode
    if (!oilData || !oilData.history || oilData.history.length === 0) {
        console.error('No history data');
        return;
    }
    
    const dates = oilData.history.map(h => h.date.slice(5));
    const prices = oilData.history.map(h => h.price);
    
    const minPrice = Math.min(...prices) - 2;
    const maxPrice = Math.max(...prices) + 2;
    
    const gradient = ctx.createLinearGradient(0, 0, 0, 350);
    gradient.addColorStop(0, 'rgba(255, 170, 0, 0.3)');
    gradient.addColorStop(1, 'rgba(255, 170, 0, 0.01)');
    
    oilChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: `${oilData.name} - Closing Price (USD)`,
                data: prices,
                borderColor: '#ffaa00',
                backgroundColor: gradient,
                borderWidth: 2.5,
                pointRadius: 3,
                pointBackgroundColor: '#ffaa00',
                pointBorderColor: '#fff',
                fill: true,
                tension: 0.2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false, // SỬA THÀNH FALSE: Giúp biểu đồ fix cứng theo container, không bị nhảy chiều cao
            animation: {
                duration: 500, // Rút ngắn thời gian vẽ (hoặc set thành 0 / false để tắt hẳn animation nếu không cần thiết)
                easing: 'easeOutQuart' // Làm mượt hiệu ứng lúc kết thúc
            },
            layout: {
                padding: 10 // Thêm khoảng lề cố định để trục X/Y không bị co giãn lúc hiện nhãn
            },
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: { labels: { color: '#fff' } },
                tooltip: { 
                    callbacks: { 
                        label: (ctx) => `${ctx.dataset.label}: $${ctx.raw} USD` 
                    }
                }
            },
            scales: {
                x: { 
                    ticks: { color: '#aaa', maxRotation: 45, autoSkip: true, maxTicksLimit: 8 }, 
                    grid: { color: '#222' } 
                },
                y: { 
                    ticks: { color: '#aaa', callback: v => '$' + v }, 
                    min: minPrice, 
                    max: maxPrice, 
                    grid: { color: '#222' } 
                }
            }
        }
    });
    
    updateSingleStats(oilData);
}

function updateSingleStats(oilData) {
    const prices = oilData.history.map(h => h.price);
    const current = prices[prices.length - 1];
    const weekAgo = prices[prices.length - 8] || prices[0];
    const monthAgo = prices[0];
    const avg = (prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(2);
    const max = Math.max(...prices);
    const min = Math.min(...prices);
    const weekChange = ((current - weekAgo) / weekAgo * 100).toFixed(2);
    const monthChange = ((current - monthAgo) / monthAgo * 100).toFixed(2);
    
    const statsHtml = `
        <div class="oil-stat-card">
            <div class="oil-stat-label">Current</div>
            <div class="oil-stat-value">$${current.toFixed(2)}</div>
        </div>
        <div class="oil-stat-card">
            <div class="oil-stat-label">7d Change</div>
            <div class="oil-stat-value ${weekChange >= 0 ? 'oil-stat-change-up' : 'oil-stat-change-down'}">
                ${weekChange >= 0 ? '▲' : '▼'} ${Math.abs(weekChange)}%
            </div>
        </div>
        <div class="oil-stat-card">
            <div class="oil-stat-label">30d Change</div>
            <div class="oil-stat-value ${monthChange >= 0 ? 'oil-stat-change-up' : 'oil-stat-change-down'}">
                ${monthChange >= 0 ? '▲' : '▼'} ${Math.abs(monthChange)}%
            </div>
        </div>
        <div class="oil-stat-card">
            <div class="oil-stat-label">30d Avg</div>
            <div class="oil-stat-value">$${avg}</div>
        </div>
        <div class="oil-stat-card">
            <div class="oil-stat-label">30d Range</div>
            <div class="oil-stat-value">$${min} - $${max}</div>
        </div>
    `;
    
    const statsDiv = document.getElementById('oil-chart-stats');
    if (statsDiv) statsDiv.innerHTML = statsHtml;
}

function updateCompareStats(brent, wti) {
    const brentPrices = brent.history.map(h => h.price);
    const wtiPrices = wti.history.map(h => h.price);
    const brentCurrent = brentPrices[brentPrices.length - 1];
    const wtiCurrent = wtiPrices[wtiPrices.length - 1];
    const brentChange = ((brentCurrent - brentPrices[0]) / brentPrices[0] * 100).toFixed(2);
    const wtiChange = ((wtiCurrent - wtiPrices[0]) / wtiPrices[0] * 100).toFixed(2);
    
    const statsHtml = `
        <div class="oil-stat-card">
            <div class="oil-stat-label">Brent Current</div>
            <div class="oil-stat-value">$${brentCurrent.toFixed(2)}</div>
            <div class="${brentChange >= 0 ? 'oil-stat-change-up' : 'oil-stat-change-down'}">
                ${brentChange >= 0 ? '▲' : '▼'} ${Math.abs(brentChange)}% (30d)
            </div>
        </div>
        <div class="oil-stat-card">
            <div class="oil-stat-label">WTI Current</div>
            <div class="oil-stat-value">$${wtiCurrent.toFixed(2)}</div>
            <div class="${wtiChange >= 0 ? 'oil-stat-change-up' : 'oil-stat-change-down'}">
                ${wtiChange >= 0 ? '▲' : '▼'} ${Math.abs(wtiChange)}% (30d)
            </div>
        </div>
        <div class="oil-stat-card">
            <div class="oil-stat-label">Spread</div>
            <div class="oil-stat-value">$${(brentCurrent - wtiCurrent).toFixed(2)}</div>
            <div class="oil-stat-label">Brent - WTI</div>
        </div>
    `;
    
    const statsDiv = document.getElementById('oil-chart-stats');
    if (statsDiv) statsDiv.innerHTML = statsHtml;
}

async function showOilChartModal() {
    const modal = document.getElementById('oil-chart-modal');
    if (!modal) return;
    
    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    // Show loading
    const statsDiv = document.getElementById('oil-chart-stats');
    if (statsDiv) statsDiv.innerHTML = '<div class="oil-stat-card">📡 Loading oil price data...</div>';
    
    const oilData = await loadOilChartData(currentSymbol);
    if (oilData) {
        renderOilChart(oilData);
    } else {
        // Show error if no data
        const canvas = document.getElementById('oil-chart-canvas');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#ff4444';
            ctx.font = '14px Arial';
            ctx.fillText('⚠️ No oil price data available. Please check API.', 50, 100);
        }
        if (statsDiv) statsDiv.innerHTML = '<div class="oil-stat-card">❌ Failed to load data</div>';
    }
}

function closeOilChartModal() {
    const modal = document.getElementById('oil-chart-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
}

async function refreshOilChart() {
    cachedOilData = null;
    const statsDiv = document.getElementById('oil-chart-stats');
    if (statsDiv) statsDiv.innerHTML = '<div class="oil-stat-card">🔄 Refreshing...</div>';
    
    const oilData = await loadOilChartData(currentSymbol, true);
    if (oilData) {
        renderOilChart(oilData);
    }
}

function setupOilChartModal() {
    const btn = document.getElementById('btn-oil-chart');
    const closeBtn = document.getElementById('oil-modal-close-btn');
    const modal = document.getElementById('oil-chart-modal');
    const tabBtns = document.querySelectorAll('.oil-tab-btn');
    
    if (btn) {
        btn.onclick = showOilChartModal;
    }
    
    if (closeBtn) {
        closeBtn.onclick = closeOilChartModal;
    }
    
    // Close on outside click
    window.onclick = (e) => {
        if (e.target === modal) {
            closeOilChartModal();
        }
    };
    
    // ESC key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal && modal.style.display === 'block') {
            closeOilChartModal();
        }
    });
    
    // Tab switching
    tabBtns.forEach(btn => {
        btn.onclick = async () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSymbol = btn.dataset.symbol;
            
            const statsDiv = document.getElementById('oil-chart-stats');
            if (statsDiv) statsDiv.innerHTML = '<div class="oil-stat-card">📡 Loading...</div>';
            
            const oilData = await loadOilChartData(currentSymbol);
            if (oilData) renderOilChart(oilData);
        };
    });
    
    // Add refresh button if not exists
    const header = document.querySelector('.oil-modal-header');
    if (header && !document.getElementById('oil-refresh-btn')) {
        const refreshBtn = document.createElement('button');
        refreshBtn.id = 'oil-refresh-btn';
        refreshBtn.innerHTML = '⟳ Refresh';
        refreshBtn.style.cssText = `
            background: #1a1a2e;
            border: 1px solid #ffaa00;
            color: #ffaa00;
            padding: 6px 15px;
            border-radius: 6px;
            cursor: pointer;
            margin-right: 15px;
            font-size: 13px;
        `;
        refreshBtn.onclick = refreshOilChart;
        
        const closeBtnEl = document.getElementById('oil-modal-close-btn');
        if (closeBtnEl) {
            header.insertBefore(refreshBtn, closeBtnEl);
        }
    }
    
    // Preload data
    loadOilChartData('BZ=F');
}

// Initialize
if (typeof Chart !== 'undefined') {
    setupOilChartModal();
} else {
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
    script.onload = setupOilChartModal;
    document.head.appendChild(script);
}

// Khởi tạo tất cả
async function init() {
    // Init existing dashboard
    await initDashboard();
    fetchOilData();
    setupSyncAllButton();
    setupInsightButton()
    
    // Init new features
    renderWebcams();
    setupWebcamControls();
    setupSecurityFilters();
    await loadSecurityAdvisories();

    await loadLiveuamap();
    await loadTelegram();
    await loadPolymarket();
    await loadGdelt();
    await loadInsight();
    await loadOpenSky();

    setInterval(async () => {
        console.log("🔄 Đang tự động quét lại dữ liệu JSON mới...");
        
        await initDashboard();
        fetchOilData();
        await loadSecurityAdvisories();
        await loadLiveuamap();
        await loadTelegram();
        await loadPolymarket();
        await loadGdelt();
        await loadOpenSky();
        await loadInsight();
        
    }, 60000); // 60000 mili-giây = 1 phút

    // // Auto refresh security every 5 minutes
    // setInterval(loadSecurityAdvisories, 300000);
    // setInterval(loadOpenSky, 120000);
}

// Run initialization
init();