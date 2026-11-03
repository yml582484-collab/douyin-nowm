FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.tencent.com/pypi/simple/
RUN playwright install --with-deps chromium
COPY app.py .
ENV PORT=8765
CMD sh -c "gunicorn -b 0.0.0.0:${PORT} -w 1 --threads 4 --timeout 180 app:app"
