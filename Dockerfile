FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# 1. ติดตั้ง Dependencies (รวม curl และ git ที่จำเป็นสำหรับบาง Lib)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        default-libmysqlclient-dev \
        libmariadb-dev-compat \
        libmariadb-dev \
        libssl-dev \
        libffi-dev \
        python3-dev \
        pkg-config \
        netcat-openbsd \
        curl \
        git \ 
        shared-mime-info \
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /code/
COPY entrypoint.sh /entrypoint.sh

# ✅ แก้ปัญหา Line Endings (Windows -> Linux) ที่ทำให้เกิด Error 255
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

# Build Tailwind (ถ้ามี)
RUN if [ -d /code/theme/static_src ]; then \
            cd /code/theme/static_src && npm install --no-audit --no-fund && npm run build || true; \
        fi

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]