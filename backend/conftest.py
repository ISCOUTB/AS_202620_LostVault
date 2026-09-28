import os

# Secreto solo para pruebas; el servicio real lo lee del entorno (nunca del código).
os.environ.setdefault("JWT_SECRET", "secreto-solo-para-tests-0123456789abcdef")
