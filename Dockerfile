# Gunakan image dasar Python
FROM python:3.9-slim

# Set lingkungan kerja di dalam container
WORKDIR /app

# Copy requirements.txt dan install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode ke dalam container
COPY . .

# Eksekusi script Python saat container berjalan
CMD ["python3", "model.py"]

