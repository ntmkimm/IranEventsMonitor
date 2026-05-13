# Sử dụng Image chuẩn có sẵn cả Node.js và Python
FROM nikolaik/python-nodejs:python3.11-nodejs20

# Tạo thư mục làm việc trong Container
WORKDIR /app

# Copy các file cấu hình vào trước
COPY package*.json ./
COPY requirements.txt ./

# Cài đặt thư viện cho Node và Python
RUN npm install
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào Container
COPY . .

# Tạo thư mục data nếu chưa có
RUN mkdir -p /app/backend/data

# Mở cửa cho cổng Frontend (5173) và Backend (3000)
EXPOSE 5173 3000

# Cài đặt concurrently để chạy nhiều lệnh cùng lúc
RUN npm install -g concurrently
