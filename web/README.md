# TransData Web

Frontend MVP de la aplicacion web de TransData.

## Stack

- Next.js
- TypeScript

## Requisitos

1. levantar el backend FastAPI en `http://127.0.0.1:8010`
2. crear `.env.local` basado en `.env.example`
3. instalar dependencias

```powershell
npm install
```

4. levantar entorno de desarrollo

```powershell
npm run dev
```

URL esperada:

- `http://127.0.0.1:3000`

## Pantallas MVP

- `/` -> Explorador de Licitaciones
- `/licitaciones/[codigo]` -> Ficha de Licitacion
- `/mercado` -> Resumen de mercado
- `/calidad` -> Estado de calidad
