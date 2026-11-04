# Python 3.11 tabanlı hafif imaj
FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem bağımlılıklarını ve sistem güncellemelerini yükle
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Bağımlılık dosyasını kopyala ve kütüphaneleri yükle (Cache avantajı için önce bunu kopyalıyoruz)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Proje kodlarının tamamını kopyala
COPY . .

# FastAPI'nin çalışacağı portu dışarı aç
EXPOSE 8000

# Servisi ayağa kaldır (Container içinde 0.0.0.0 dinlenmeli!)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]