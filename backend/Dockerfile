FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Puerto por defecto de FastAPI
EXPOSE 8000

# Variables de entorno por defecto (JWT_SECRET debe sobreescribirse en ejecución)
ENV PORT=8000
ENV LOG_LEVEL=INFO

# Comando de ejecución con Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
