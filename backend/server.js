const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const { exec } = require('child_process');

const app = express();
const PORT = 3000;

// Cho phép Frontend ở port khác được quyền gọi API
app.use(cors()); 

// 1. API cập nhật sự kiện biểu tình (ACLED)
app.post('/api/refresh/acled', (req, res) => {
    console.log("⚡ Nhận lệnh Crawl Sự kiện (ACLED)...");
    const scriptPath = path.join(__dirname, 'iran_crawl_acled.py');
    exec(`python "${scriptPath}"`, (error, stdout, stderr) => {
        if (stdout) console.log(`[ACLED]:\n${stdout}`);
        if (error) return res.status(500).json({ error: "Crawl ACLED thất bại!" });
        res.json({ message: "Dữ liệu sự kiện đã được cập nhật!" });
    });
});

// 2. API cập nhật giá dầu (OIL)
app.post('/api/refresh/oil', (req, res) => {
    console.log("⚡ Nhận lệnh Crawl Giá dầu (Yahoo)...");
    
    // Đảm bảo đường dẫn ghép đúng
    const scriptPath = path.join(__dirname, 'crawl_oil_prices.py');
    
    console.log(`Đang chạy lệnh Oil: python "${scriptPath}"`); // In ra để xem

    exec(`python "${scriptPath}"`, (error, stdout, stderr) => {
        if (stdout) console.log(`[OIL LOG]:\n${stdout}`);
        
        // Bắt lỗi kỹ hơn
        if (error) {
            console.error(`[Node.js Lỗi Exec]: ${error.message}`);
            return res.status(500).json({ error: "Crawl Oil thất bại!" });
        }
        res.json({ message: "Dữ liệu dầu đã được cập nhật!" });
    });
});

// Thêm API này để Frontend có thể lấy dữ liệu giá dầu
app.get('/api/oil', (req, res) => {
    try {
        const dataPath = path.join(__dirname, 'data', 'oil_prices.json');
        
        // Kiểm tra nếu chưa có file (chưa bấm nút Sync Oil bao giờ) thì trả về mảng rỗng
        if (!fs.existsSync(dataPath)) {
            return res.json([]); 
        }

        const rawData = fs.readFileSync(dataPath, 'utf-8');
        res.json(JSON.parse(rawData));
    } catch (error) {
        console.error("Lỗi đọc data giá dầu:", error);
        res.status(500).json({ error: "Không thể đọc dữ liệu dầu" });
    }
});

// Tạo API Endpoint: Lấy dữ liệu biểu tình/xung đột
app.get('/api/events', (req, res) => {
    try {
        // Đọc file JSON của bạn
        const dataPath = path.join(__dirname, 'data', 'iran_protests_clean.json');
        const rawData = fs.readFileSync(dataPath, 'utf-8');
        const events = JSON.parse(rawData);
        
        // Trả dữ liệu về cho người gọi
        res.json(events);
    } catch (error) {
        console.error("Lỗi đọc data:", error);
        res.status(500).json({ error: "Không thể đọc dữ liệu" });
    }
});

app.listen(PORT, () => {
    console.log(`📡 Backend đang chạy tại: http://localhost:${PORT}`);
    console.log(`👉 API Data: http://localhost:${PORT}/api/events`);
});