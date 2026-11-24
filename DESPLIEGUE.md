# Guía de despliegue — Sanar Academia FC

Arquitectura: **Base de datos (Postgres)** ← **Backend Flask en Vercel** ← **Frontend Angular en Render**.
El frontend reenvía todo lo que empieza por `/api/` al backend (regla de reescritura en `render.yaml`),
así el navegador usa un solo dominio y la sesión por cookie funciona sin configurar CORS.

> Importante: SQLite **no sirve** en Vercel (disco temporal). Hace falta una base externa.

## 1. Base de datos (Neon o Supabase, gratis)
1. Crea un proyecto Postgres en https://neon.tech (o Supabase).
2. Copia la cadena de conexión (`postgresql://usuario:clave@host/db?sslmode=require`).
   Es secreta: solo se pega en Vercel, nunca en el código ni en GitHub.

## 2. Backend en Vercel
1. En Vercel: **Add New > Project** > importa el repo `Sanar-academia-fc`.
2. **Root Directory:** `sanar-academia-main/backend`. Framework: *Other*.
3. **Environment Variables:**

| Variable | Valor |
|---|---|
| `DATABASE_URL` | la cadena de conexión de Postgres |
| `SECRET_KEY` | una clave larga y aleatoria (mínimo 32 caracteres) |
| `ADMIN_PASSWORD` | contraseña del usuario `admin` inicial (se crea solo la primera vez) |
| `COOKIE_SECURE` | `1` |

4. **Deploy.** No hace falta `vercel.json`: Vercel detecta Flask y manda todas las rutas a la app. Al terminar, abre `https://TU-BACKEND.vercel.app/api/ping`: debe responder
   `{"mensaje":"API de Flask funcionando correctamente"}`. Las tablas se crean solas al primer arranque.

## 3. Frontend en Render
1. `render.yaml` ya apunta al backend `https://sanar-academia-api.vercel.app`. Si cambias el dominio de Vercel, actualízalo ahí y sube el cambio.
2. En Render: **New > Blueprint** y elige el repo (lee `render.yaml`).
   *Alternativa manual:* **New > Static Site**, Root Directory `sanar-academia-main/sanar-fc-fronted`,
   Build Command `npm ci && npm run build && cp dist/sanar-fc-fronted/browser/index.csr.html dist/sanar-fc-fronted/browser/index.html`,
   Publish Directory `dist/sanar-fc-fronted/browser`, y en *Redirects/Rewrites* crea:
   `/api/*` → `https://TU-BACKEND.vercel.app/api/*` (Rewrite) y `/*` → `/index.html` (Rewrite).
3. Abre la URL de Render e inicia sesión con `admin` y la contraseña de `ADMIN_PASSWORD`.

## Problemas frecuentes
- **"No se pudo conectar con el servidor"**: revisa que la regla `/api/*` de Render apunte al dominio correcto de Vercel.
- **Error 500 al iniciar sesión**: revisa `DATABASE_URL` en Vercel (*Logs* del proyecto).
- **Los datos desaparecen**: `DATABASE_URL` no está definida y el backend usó SQLite temporal.
- **Sesión que no se mantiene**: verifica `COOKIE_SECURE=1` y que entres por el dominio de Render (no el de Vercel).
- **Desarrollo local**: sin variables de entorno todo funciona como antes (`python run.py` + `ng serve`).

