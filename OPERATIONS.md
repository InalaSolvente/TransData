# TransData Operations

## 1. Proposito

Este documento describe como operar TransData en su estado actual.

Debe tratarse como un documento vivo.  
Puede cambiar a medida que:

- avance el refresh
- cambie la politica operativa
- aparezcan nuevas restricciones de la API
- el flujo sectorial se estabilice mejor

---

## 2. Objetivo operativo actual

El objetivo operativo de TransData hoy es mantener y mejorar el activo central del proyecto:

- `data/master/licitaciones_transport_master.csv`

Ese master debe mantenerse:

- consistente
- enriquecido
- refrescado incrementalmente
- sincronizado con las capas derivadas

Las capas derivadas actuales son:

- `analytics`
- `quality`
- `serving`
- `health reports`

---

## 3. Runner operativo

El runner operativo principal es:

- `src/pipeline/mp_operate_pipeline.py`

Su comando base es:

```powershell
python src\pipeline\mp_operate_pipeline.py
```

La idea es que este comando funcione usando el `.env` como configuracion principal.  
Los flags de CLI quedan como override puntual, no como mecanismo principal de operacion.

---

## 4. Configuracion por .env

Las siguientes variables controlan el runner operativo:

```env
MP_OPERATION_MODE=daily
MP_OPERATION_RAW_PATTERN=mp_raw_*.json
MP_OPERATION_MIN_SCORE=3
MP_OPERATION_ENRICH_LIMIT=10000
MP_OPERATION_REFRESH_SLEEP_SEC=0.6
MP_OPERATION_RUN_HEALTH=true

MP_DAILY_RUN_REFRESH=true
MP_DAILY_REFRESH_LIMIT=300
MP_DAILY_RUN_HEALTH=true

MP_WEEKLY_RUN_REFRESH=true
MP_WEEKLY_REFRESH_LIMIT=1000
MP_WEEKLY_RUN_HEALTH=true
```

### Significado

- `MP_OPERATION_MODE`:
  - define el preset operativo por defecto
  - valores esperados: `daily`, `weekly`

- `MP_OPERATION_RAW_PATTERN`:
  - patron de raws a considerar en el runner

- `MP_OPERATION_MIN_SCORE`:
  - puntaje minimo del filtro de transporte

- `MP_OPERATION_ENRICH_LIMIT`:
  - limite por corrida para enrich dentro del ciclo operativo

- `MP_OPERATION_REFRESH_SLEEP_SEC`:
  - pausa base entre licitaciones refrescadas

- `MP_OPERATION_RUN_HEALTH`:
  - comportamiento por defecto para generar health report

- `MP_DAILY_*`:
  - politica especifica del modo diario

- `MP_WEEKLY_*`:
  - politica especifica del modo semanal

---

## 5. Modos operativos

### 5.1 Daily

Pensado para operacion frecuente y conservadora.

Uso recomendado:

- refresh en tandas moderadas
- mantener salud operativa
- resincronizar derivados si cambia el master

La configuracion se toma desde:

- `MP_DAILY_RUN_REFRESH`
- `MP_DAILY_REFRESH_LIMIT`
- `MP_DAILY_RUN_HEALTH`

### 5.2 Weekly

Pensado para una corrida mas amplia.

Uso recomendado:

- avanzar mas fuerte en refresh
- actualizar capas derivadas despues de cambios mas grandes
- dejar un health report mas representativo del estado semanal

La configuracion se toma desde:

- `MP_WEEKLY_RUN_REFRESH`
- `MP_WEEKLY_REFRESH_LIMIT`
- `MP_WEEKLY_RUN_HEALTH`

---

## 6. Flujo que ejecuta el runner

El runner operativo utiliza internamente el transform runner y el health report.

El flujo actual es:

1. `transform batch`
2. `seleccion transporte`
3. `append transport master`
4. `enrich`
5. `refresh` segun el modo operativo
6. resincronizacion automatica de:
   - `analytics`
   - `quality`
   - `serving`
7. `health report`
8. `operation summary`

Nota:

- si el `transport master` no cambia, las capas derivadas no deberian reprocesarse innecesariamente
- si el master cambia, el runner ya puede resincronizarlas automaticamente

---

## 7. Formas de uso

### Usar solo el .env

```powershell
python src\pipeline\mp_operate_pipeline.py
```

Este es el modo recomendado para operacion normal.

### Forzar modo puntual

```powershell
python src\pipeline\mp_operate_pipeline.py --mode weekly
```

### Desactivar refresh para una corrida

```powershell
python src\pipeline\mp_operate_pipeline.py --no-refresh
```

### Desactivar health para una corrida

```powershell
python src\pipeline\mp_operate_pipeline.py --no-health
```

### Override puntual de limite de refresh

```powershell
python src\pipeline\mp_operate_pipeline.py --refresh-limit 500
```

---

## 8. Artefactos que revisar despues de correr

### Operacion

- `data/reports/operations/mp_operate_pipeline_summary_*.json`

### Salud general

- `data/reports/mp_pipeline_health_*.json`

### Refresh

- `data/master/mp_refresh_summary_*.json`
- `data/history/licitaciones_transport_status_history.csv`
- `data/raw/refresh/`

### Derivados

- `data/analytics/`
- `data/reports/quality/`
- `data/serving/`

---

## 9. Que mirar en una corrida sana

Una corrida razonable deberia dejar señales como estas:

- sin errores graves de API persistentes
- resumen operativo generado
- health report generado si esta habilitado
- el `transport master` consistente
- refresh avanzando sin reprocesar innecesariamente la cola
- adjudicaciones capturadas aumentando gradualmente

---

## 10. Señales para pausar o ajustar

Conviene pausar, bajar limites o revisar configuracion si vemos:

- muchos errores consecutivos de API
- aumento anormal de retries
- refresh sin cambios reales durante muchas corridas
- inconsistencias nuevas en `quality`
- diferencias sospechosas entre `transport master` y capas derivadas

---

## 11. Recomendacion practica actual

Mientras el refresh sigue estabilizandose:

1. usar `daily` como modo base
2. subir `weekly` de forma prudente
3. revisar `quality` y `health` despues de tandas grandes
4. tratar `analytics` y `serving` como capas derivadas que pueden ajustarse

En esta etapa, la operacion todavia debe privilegiar:

- trazabilidad
- control incremental
- capacidad de corregir

por sobre automatizacion agresiva.
