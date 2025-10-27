# 1. Chọn image Python
FROM python:3.11-slim

# 2. Đặt thư mục làm việc bên trong container
WORKDIR /app

# 3. Sao chép CHỈ file requirements.txt vào trước
COPY requirements.txt .

# 4. Cài đặt các thư viện (làm bước này riêng để tận dụng cache)
RUN pip install --no-cache-dir -r requirements.txt

# 5. Sao chép TOÀN BỘ code (main.py, crud.py...) vào
COPY . .

# 6. Mở cổng 8000 (cổng mặc định của uvicorn)
EXPOSE 8000

# 7. Lệnh để chạy ứng dụng
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]