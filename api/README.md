# LostVault Claims API

Implementación del contrato `docs/contracts/lostvault-api.yaml` (OpenAPI 3.1) de
LostVault: reclamar un objeto perdido.

```
POST   /v1/auth/login                    (correo institucional + contraseña → JWT)
POST   /v1/objects                       (Bearer JWT; registra un objeto perdido)
DELETE /v1/objects/{objectId}            (Bearer JWT; solo quien lo reportó)
POST   /v1/objects/{objectId}/claims     (Bearer JWT, Idempotency-Key opcional)
GET    /health                           (para health checks del panel)
```

| Código | Cuándo |
|--------|--------|
| 201 | Reclamación creada y verificada (también en repetición con la misma `Idempotency-Key`, con cabecera `Idempotent-Replayed: true`) |
| 200 | El objeto ya estaba reclamado por el mismo usuario (sin `Idempotency-Key`) |
| 400 | `Idempotency-Key` vacía o de más de 255 caracteres |
| 401 | Sin token, token inválido o expirado |
| 404 | El objeto no existe |
| 409 | El objeto ya fue reclamado por otro usuario |
| 422 | Identidad no verificada, o `Idempotency-Key` ya usada con otro objeto |

Los errores tienen la forma `{"code": "...", "message": "..."}`.

## Configuración

Define `JWT_SECRET` como variable de entorno del servicio.

| Variable | Descripción | Por defecto |
|----------|-------------|-------------|
| `JWT_SECRET` | **Obligatoria.** Secreto con el que se verifican los JWT | — |
| `JWT_ALGORITHM` | Algoritmo del JWT | `HS256` |
| `VERIFIED_EMAIL_DOMAINS` | Dominios cuya identidad se considera verificada | `utb.edu.co` |
| `CORS_ORIGINS` | Orígenes permitidos (coma), vacío = sin CORS | vacío |
| `AUTH_USER_EMAIL` | Correo del usuario único temporal (debe ser de `VERIFIED_EMAIL_DOMAINS`) | — |
| `AUTH_USER_PASSWORD` | Contraseña del usuario único temporal | — |
| `AUTH_USER_ID` | Id del usuario (claim `sub`) | `user-1` |
| `JWT_EXPIRES_MINUTES` | Vigencia del token emitido por el login | `60` |
| `PORT` | Puerto del servidor (debe coincidir con el Container Port del dominio) | `8000` |
| `DATABASE_URL` | URL de la base de datos (aún no se usa) | vacío |

El token debe incluir `sub` (id del usuario), `exp` y `email`. La identidad se
considera verificada si el `email` pertenece a `VERIFIED_EMAIL_DOMAINS`.

## Ejecutar en local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
export JWT_SECRET=un-secreto-largo
uvicorn app.main:app --reload
```

Probar:

```bash
TOKEN=$(python scripts/make_token.py --sub student-42 --email estudiante@utb.edu.co)
curl -i -X POST http://localhost:8000/v1/objects/1/claims \
  -H "Authorization: Bearer $TOKEN" \
  -H "Idempotency-Key: $(uuidgen)"
```

Documentación interactiva en `http://localhost:8000/docs`.

## Pruebas

```bash
pytest
```

## Docker

```bash
docker build -t lostvault-api .
docker run --rm -p 8000:8000 -e JWT_SECRET=un-secreto-largo lostvault-api
```

## Limitaciones

- El login acepta un único usuario definido por variables de entorno; hay que
  reemplazarlo por usuarios en base de datos (con contraseñas hasheadas).
- Los datos (objetos y reclamaciones) están **en memoria** y se pierden al
  reiniciar, igual que la línea base del repositorio. Hay un único objeto de
  ejemplo, `1` ("Termo negro"). Para producción real hay que reemplazar
  `app/store.py` por una base de datos.
- Con un solo proceso la idempotencia es consistente; con varias réplicas
  necesitarías almacenamiento compartido.

## Panel del encargado

La misma API publica la interfaz web en `/admin`. El panel usa el mismo origen
que la API. Configure `ADMIN_EMAIL` (un correo de los dominios verificados) y
`ADMIN_PASSWORD` como variables privadas del servicio. Use una cuenta distinta
de la configurada para la APK y un dominio HTTPS para iniciar sesión en un
despliegue público. Las credenciales quedan del lado del servidor.

- `POST /v1/admin/login` emite el JWT del encargado.
- `GET /v1/admin/objects` consulta el inventario.
- `POST /v1/admin/objects` registra un objeto recibido.
- `POST /v1/admin/objects/{object_id}/deliver` registra la entrega física.

El inventario distingue disponible, reclamado y entregado. Registrar la entrega
es idempotente y evita nuevas reclamaciones del objeto. Los datos siguen en la
memoria del proceso y se pierden al reiniciar. Ejecute un solo proceso para la
demo mientras el servicio use este almacén.
