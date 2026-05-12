
const API_URL = 'http://localhost:3000/api/events';
const REFRESH_URL = 'http://localhost:3000/api/refresh';

let myGlobe;
let myMap2D;
let globalEventData = [];
let currentMode = '2D'; 

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

        if (myGlobe) {
            myGlobe.hexBinPointsData(globalEventData);
        } else {
            renderGlobe(globalEventData);
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
                <span style="font-size: 13px; color: #ddd; line-height: 1.4;">${e.notes || 'Không có mô tả.'}</span>
            </div>
        `).join('');

        const popupHTML = `
            <div style="color: #fff; min-width: 250px; max-width: 320px; font-family: sans-serif;">
                <h4 style="margin: 0 0 10px 0; color: #ff4444; font-size: 15px; border-bottom: 1px solid #ff4444; padding-bottom: 5px;">
                    📍 ${group.location || 'Khu vực không xác định'} 
                    <span style="font-size:12px; color:#aaa">(${group.events.length} vụ)</span>
                </h4>
                <div class="event-scroll-list" style="max-height: 250px; overflow-y: auto; padding-right: 8px;">
                    ${eventsHtml}
                </div>
            </div>
        `;
        
        marker.bindPopup(popupHTML);
    });
}

function renderGlobe(eventData) {
    const container = document.getElementById('map-container');
    myGlobe = Globe()
        (document.getElementById('globe-viz'))
        .width(container.clientWidth)
        .height(container.clientHeight)
        .globeImageUrl('//unpkg.com/three-globe/example/img/earth-dark.jpg')
        .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
        .hexBinPointLat(d => parseFloat(d.lat))
        .hexBinPointLng(d => parseFloat(d.lng))
        .hexBinPointWeight(1)
        .hexAltitude(d => d.sumWeight * 0.05)
        .hexTopColor(() => '#ff4444')
        .hexSideColor(() => 'rgba(255, 68, 68, 0.2)')
        .hexBinMerge(true)
        .hexBinPointsData(eventData)
        .hexLabel(hex => {
            const count = hex.points.length;
            const latestEvent = hex.points.sort((a, b) => new Date(b.date) - new Date(a.date))[0];
            
            return `
                <div style="background: rgba(15, 15, 15, 0.95); padding: 12px; border-radius: 6px; border: 1px solid #ff4444; color: white; min-width: 250px;">
                    <h4 style="margin: 0 0 5px 0; color: #ffaa00;">🔥 ${count} sự kiện tại khu vực này</h4>
                    <p style="margin: 0; font-size: 12px; color: #aaa;">📅 Gần nhất: ${latestEvent.date}</p>
                    <hr style="border-color: #333; margin: 8px 0;">
                    <p style="margin: 0; font-size: 13px; max-width: 300px; white-space: normal; line-height: 1.4;">${latestEvent.notes}</p>
                </div>
            `;
        })
        .onHexClick((hex, event, coords) => {
            myGlobe.pointOfView({ lat: coords.lat, lng: coords.lng, altitude: 0.6 }, 1000);
        });

    myGlobe.pointOfView({ lat: 32.42, lng: 53.68, altitude: 1.5 }, 2000);
    myGlobe.controls().autoRotate = true;
    myGlobe.controls().autoRotateSpeed = 0.5;
}

function setupToggleButtons() {
    const btn3D = document.getElementById('btn-3d');
    const btn2D = document.getElementById('btn-2d');
    const div3D = document.getElementById('globe-viz');
    const div2D = document.getElementById('map-2d');

    btn2D.addEventListener('click', () => {
        currentMode = '2D';
        btn2D.classList.add('active');
        btn3D.classList.remove('active');
        div3D.style.display = 'none';
        div2D.style.display = 'block';

        setTimeout(() => { myMap2D.invalidateSize(); }, 100);
    });

    btn3D.addEventListener('click', () => {
        currentMode = '3D';
        btn3D.classList.add('active');
        btn2D.classList.remove('active');
        div2D.style.display = 'none';
        div3D.style.display = 'block';

        const container = document.getElementById('map-container');
        myGlobe.width(container.clientWidth);
        myGlobe.height(container.clientHeight);
    });
}

window.addEventListener('resize', () => {
    const container = document.getElementById('map-container');
    if(myGlobe) {
        myGlobe.width(container.clientWidth);
        myGlobe.height(container.clientHeight);
    }
});

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

// KÍCH HOẠT CHẠY 
setupToggleButtons();
setupRefreshButtons();
fetchOilData(); 
initDashboard();