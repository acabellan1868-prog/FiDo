FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código y frontend
COPY app/ app/
COPY static/ static/

# Puerto de la aplicación
EXPOSE 8080

# Arrancar uvicorn
CMD ["uvicorn", "app.principal:app", "--host", "0.0.0.0", "--port", "8080"]
