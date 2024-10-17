# Gunakan image dasar Python
FROM python:3.9-slim

# Set lingkungan kerja di dalam container
WORKDIR /app

# Copy requirements.txt dan install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode ke dalam container
COPY . .

# Tambahkan entrypoint script ke container
COPY entrypoint.sh .

EXPOSE 4500

# Set permissions dan jalankan entrypoint script
RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]

