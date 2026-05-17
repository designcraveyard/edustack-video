FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV EDUPLUGIN_DATA_DIR=/var/lib/eduplugin \
    EDUPLUGIN_BIND=0.0.0.0:8000

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
