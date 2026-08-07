# Dockerfile for deploying the Travel Expense Extraction Agent on Render
# (or any Docker-based host). Installs system-level OCR/PDF dependencies
# that Render's native Python build environment can't install itself.

FROM python:3.11-slim

# tesseract-ocr: local OCR fallback for image extraction
# poppler-utils: PDF rasterization (pdf2image) for scanned PDFs
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT dynamically; default to 8501 for local/other hosts.
ENV PORT=8501
EXPOSE 8501

CMD streamlit run app.py --server.port ${PORT:-8501} --server.address 0.0.0.0 --server.headless true
