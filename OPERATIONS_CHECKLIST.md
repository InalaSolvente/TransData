# TransData Operations Checklist

## 1. Proposito

Este checklist sirve para operar TransData con una rutina simple y repetible.

Debe tratarse como una guia viva.  
Puede cambiar a medida que el refresh se estabilice, cambie el backlog o aparezcan nuevas señales en `quality` y `health`.

---

## 2. Antes de correr

- revisar [.env](</c:/Users/User/OneDrive/Desktop/TransData-main/.env>)
- confirmar `MP_OPERATION_MODE`
- confirmar limite de refresh del modo activo
- confirmar si `health` esta habilitado
- confirmar que el objetivo sigue siendo el `transport master`

Chequeos recomendados:

- `MP_OPERATION_MODE=daily` para operacion normal
- `MP_OPERATION_MODE=weekly` solo cuando queramos avanzar mas fuerte
- revisar que `MP_REFRESH_LIMIT` o el preset del modo no sea demasiado agresivo para la API

---

## 3. Corrida normal

Comando recomendado:

```powershell
python src\pipeline\mp_operate_pipeline.py
```

Overrides puntuales utiles:

```powershell
python src\pipeline\mp_operate_pipeline.py --mode weekly
```

```powershell
python src\pipeline\mp_operate_pipeline.py --refresh-limit 500
```

```powershell
python src\pipeline\mp_operate_pipeline.py --no-refresh
```

---

## 4. Durante la corrida

Mirar en consola:

- modo operativo
- refresh habilitado o no
- refresh limit
- enrich limit
- health habilitado o no

Si hay refresh, revisar:

- cantidad seleccionada para refresh
- desglose de cola:
  - nunca refrescadas
  - con error pendiente
  - revisitas por threshold
  - exitosas pendientes no vencidas
- primeros codigos a refrescar

---

## 5. Despues de correr

### Revisar resumen operativo

- `data/reports/operations/mp_operate_pipeline_summary_*.json`

### Revisar health report

- `data/reports/mp_pipeline_health_*.json`

Validar al menos:

- `transport_master_rows`
- `transport_adjudicacion_capturada_rows`
- `transport_refresh_pending_award_rows`
- `transport_refresh_success_rows`
- `transport_refresh_error_rows`

### Revisar refresh

- `data/master/mp_refresh_summary_*.json`
- `data/history/licitaciones_transport_status_history.csv`

Validar:

- `successful_rows`
- `failed_rows`
- `changed_rows`
- `state_changed_rows`
- `award_changed_rows`

### Revisar calidad derivada

- `data/reports/quality/transport_quality_summary_*.json`

Mirar:

- `issues_count`
- `severity_counts`
- si aparecieron incoherencias nuevas de adjudicacion o estados

---

## 6. Señales de corrida sana

- el runner termina sin errores de ejecucion
- se genera resumen operativo
- se genera health report si estaba habilitado
- el refresh avanza la cola sin repetir demasiado las mismas filas
- aumentan gradualmente las adjudicaciones capturadas
- no crecen los errores de refresh de forma anormal

---

## 7. Señales para frenar o ajustar

- muchos errores HTTP o de conexion
- `failed_rows` alto respecto de `successful_rows`
- refresh con muchos retries y pocos cambios
- aumento inesperado en issues de calidad
- resincronizacion derivada inconsistente con el master

Acciones sugeridas:

1. bajar `refresh_limit`
2. volver a `daily`
3. pausar refresh y correr solo `health` y `quality`
4. revisar raws de refresh y resumenes recientes

---

## 8. Rutina recomendada hoy

### Diario

1. correr `python src\pipeline\mp_operate_pipeline.py`
2. revisar `operation summary`
3. revisar `health`
4. revisar si bajaron pendientes de adjudicacion

### Semanal

1. subir a `weekly` si la API se ve estable
2. correr el runner operativo
3. revisar `quality`
4. revisar consistencia entre `master`, `analytics` y `serving`
5. actualizar [CURRENT_STATUS.md](</c:/Users/User/OneDrive/Desktop/TransData-main/CURRENT_STATUS.md>) si cambian señales importantes
