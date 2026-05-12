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

# Mở cửa cho cổng Frontend (5173) và Backend (3000)
EXPOSE 5173 3000

# Lệnh khởi chạy
CMD ["npm", "run", "dev"]