FROM python:3.11

WORKDIR /app

ENV TZ=Asia/Shanghai
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
