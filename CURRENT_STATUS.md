# TransData Current Status

## 1. Proposito

Este documento resume el estado actual del proyecto en una forma facil de leer.

No reemplaza los reportes JSON.  
Su objetivo es dejar una foto operativa simple para saber:

- que ya funciona
- que sigue en validacion
- que conviene hacer despues

---

## 2. Estado general

TransData ya tiene operativo el flujo principal:

1. ingest historico
2. transform batch
3. filtro de transporte
4. `transport master`
5. `transport master core`
6. enrich
7. refresh incremental
8. capas derivadas:
   - analytics
   - quality
   - serving
   - app listing / app detail
   - contrato de datos para la futura aplicacion
   - modelo de pantallas para la futura aplicacion
   - arquitectura base de backend web
   - contrato minimo de endpoints del backend web
   - stack tecnico recomendado para la app web
   - backend MVP FastAPI ya scaffolded
   - frontend MVP Next.js scaffolded
9. runner operativo por `.env`

Hoy el proyecto ya no esta en fase exploratoria del pipeline base.  
El foco actual es estabilizar y escalar mejor el refresh, manteniendo coherencia entre el master core y las capas derivadas.
Tambien ya existe una linea de depuracion del filtro de transporte, con auditoria automatica y cola de revision manual pendiente.

---

## 3. Foto operativa actual

Referencia usada:

- [mp_pipeline_health_20260508_225931.json](</c:/Users/User/OneDrive/Desktop/TransData-main/data/reports/mp_pipeline_health_20260508_225931.json>)

Indicadores principales:

- `raw files`: 69
- `success dates`: 1824
- `processed files`: 65
- `general master rows`: 123347
- `transport master rows`: 7848
- `transport core master rows`: 7676
- `transport enriched rows`: 7848
- `transport refresh success rows`: 7847
- `transport refresh error rows`: 1
- `adjudicaciones capturadas`: 5135
- `pendientes de adjudicacion`: 2713
- `analytics rows`: 7676
- `quality issues count`: 3
- `serving rows`: 7676
- `app listing rows`: 7676
- `app detail rows`: 7676
- `filas revisadas manualmente aplicadas`: 362
- `filas aun en revision manual`: 16

Indicadores actuales del filtro de transporte:

- `seguirian como transporte con reglas nuevas`: 6039
- `saldrian del universo actual`: 1809
- `pendientes de revision manual`: 362
- `grupos de revision`: education 181, social 89, health 47, other 35

---

## 4. Lo que ya esta bien encaminado

- ingest con cobertura por `fecha_consulta`
- backfill incremental
- transform reproducible desde raw
- master sectorial consolidado
- master core reconstruible con revision manual y auditoria reproducible
- enrich completo sobre el `transport master`
- refresh con cola incremental y revisita por threshold
- resincronizacion automatica de `analytics`, `quality` y `serving` usando `transport master core` como fuente preferente
- health report con metricas utiles para operacion
- auditoria del filtro de transporte
- cola de revision manual agrupada para el filtro de transporte
- integracion real del CSV revisado al `transport master core`
- serving reforzado con vistas separadas para `listing` y `detail` de aplicación
- contrato explicito de datos para la aplicacion en `APP_DATA_CONTRACT.md` y `transport_app_contract_latest.json`
- modelo explicito de pantallas y navegacion en `APP_SCREEN_MODEL.md`
- arquitectura base del backend web en `APP_BACKEND_ARCHITECTURE.md`
- contrato minimo de API en `APP_API_CONTRACT.md`
- stack recomendado definido: `Next.js + FastAPI + DuckDB`, con `PostgreSQL` futuro para datos de aplicacion
- backend MVP implementado en `src/api/`
- frontend MVP implementado en `web/`

---

## 5. Lo que sigue en validacion

- comportamiento del refresh a escala completa
- velocidad real de captura de adjudicaciones faltantes
- consistencia final de estados despues de varias corridas
- calidad de algunas reglas del filtro de transporte
- cierre de la revision manual del universo `borderline_generic`
- cierre de los 16 casos que aun quedaron como `REVISAR_MANUAL`

---

## 6. Riesgos vigentes

- la API sigue siendo inestable
- el refresh puede requerir ajustes finos segun el comportamiento real
- las capas derivadas siguen siendo provisionales hasta estabilizar mejor adjudicaciones y estados

---

## 7. Siguiente foco recomendado

1. seguir avanzando el refresh en tandas controladas
2. observar caida real del backlog de adjudicaciones pendientes
3. resolver los 16 casos remanentes en `REVISAR_MANUAL`
4. revisar `quality` despues de tandas grandes
5. instalar dependencias y levantar el frontend MVP contra la API local
6. evaluar si la capa repository pasa pronto de `pandas` a `DuckDB`
7. mantener operacion basada en `.env` y resumenes trazables

---

## 8. Documentos operativos relacionados

- [PROJECT_GUIDELINES.md](</c:/Users/User/OneDrive/Desktop/TransData-main/PROJECT_GUIDELINES.md>)
- [ROADMAP.md](</c:/Users/User/OneDrive/Desktop/TransData-main/ROADMAP.md>)
- [OPERATIONS.md](</c:/Users/User/OneDrive/Desktop/TransData-main/OPERATIONS.md>)
- [OPERATIONS_CHECKLIST.md](</c:/Users/User/OneDrive/Desktop/TransData-main/OPERATIONS_CHECKLIST.md>)
