FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "forward_testing/rv_iv_analysis/rv_iv_analysis.py"]
