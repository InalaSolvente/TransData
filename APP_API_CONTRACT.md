# TransData App API Contract

## 1. Proposito

Este documento define el contrato minimo de endpoints para el backend web de TransData.

Su objetivo es dejar claro:

- que endpoints existen en el MVP
- que parametros aceptan
- que forma tienen las respuestas
- como se conectan con las vistas `listing` y `detail`

No fija todavia un framework, pero si fija la interfaz esperada del backend.

---

## 2. Principios del contrato

1. la API sirve datos internos derivados, no consulta Mercado Publico en tiempo real
2. el dominio principal inicial es `licitaciones`
3. la forma de respuesta debe ser estable aunque cambie el almacenamiento interno
4. el backend debe ser extensible a `empresas`, `compradores` y BI
5. el frontend web debe poder resolverse solo con esta API

---

## 3. Convenciones generales

### 3.1 Base path

Base path recomendado:

- `/api`

### 3.2 Formato de respuesta

Todas las respuestas exitosas devuelven JSON.

### 3.3 Versionado

Para el MVP, se puede trabajar sin version en URL.

Cuando haga falta endurecer compatibilidad, pasar a:

- `/api/v1/...`

### 3.4 Errores

Formato recomendado:

```json
{
  "error": {
    "code": "not_found",
    "message": "No existe licitacion para el codigo solicitado.",
    "details": {}
  }
}
```

Codigos sugeridos:

- `bad_request`
- `not_found`
- `validation_error`
- `internal_error`

### 3.5 Paginacion

Para endpoints de listado:

- `page`: entero, base 1
- `page_size`: entero

Respuesta recomendada:

```json
{
  "data": [],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_results": 7676,
    "total_pages": 308
  }
}
```

---

## 4. Endpoints MVP

## 4.1 GET `/api/licitaciones`

Objetivo:

- alimentar la pantalla `Licitaciones`

Fuente principal:

- `transport_app_listing_latest.csv`

Query params soportados:

- `q`
- `estado_bucket`
- `region`
- `comuna`
- `periodo_publicacion`
- `revision_segmento`
- `revision_prioridad`
- `revision_decision`
- `adjudicacion_capturada`
- `requiere_refresh_adjudicacion`
- `page`
- `page_size`
- `sort`

Semantica:

- `q`: busqueda por texto libre sobre nombre y comprador
- `sort`: string tipo `fecha_publicacion:desc` o `monto_estimado:desc`

Respuesta recomendada:

```json
{
  "data": [
    {
      "codigo_licitacion": "2904-8-LE26",
      "nombre": "SERVICIO DE TRANSPORTE - MUNICIPALIDAD DE HUALAIHUE",
      "estado": "Cerrada",
      "estado_bucket": "cerrada",
      "fecha_publicacion": "2026-04-24T11:07:00",
      "fecha_cierre": "2026-05-05T12:30:00",
      "periodo_publicacion": "2026-04",
      "comprador_nombre": "I MUNICIPALIDAD DE HUALAIHUE",
      "comprador_rut": "69.252.200-1",
      "region": "Region de los Lagos",
      "comuna": "Hualaihue",
      "monto_estimado": null,
      "monto_adjudicado": null,
      "moneda": "CLP",
      "transport_score": 3,
      "revision_segmento": "",
      "revision_prioridad": "",
      "revision_decision": "INCLUIR",
      "flag_mixed_bundle": false,
      "flag_clean_transport_amount": true,
      "adjudicacion_capturada": false,
      "requiere_refresh_adjudicacion": true,
      "fue_enriquecida": true,
      "url_ficha": ""
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_results": 7676,
    "total_pages": 308
  },
  "applied_filters": {
    "estado_bucket": ["adjudicada"],
    "region": ["Region Metropolitana de Santiago"]
  },
  "sort": {
    "field": "fecha_publicacion",
    "direction": "desc"
  }
}
```

Campos minimos de cada item:

- todos los campos de `transport_app_listing_latest.csv`

---

## 4.2 GET `/api/licitaciones/{codigo_licitacion}`

Objetivo:

- alimentar la pantalla `Ficha de Licitacion`

Fuente principal:

- `transport_app_detail_latest.csv`

Path param:

- `codigo_licitacion`

Respuesta recomendada:

```json
{
  "data": {
    "codigo_licitacion": "2904-8-LE26",
    "nombre": "SERVICIO DE TRANSPORTE - MUNICIPALIDAD DE HUALAIHUE",
    "descripcion": "El objetivo de la presente licitacion es contratar servicios de transporte de pasajeros...",
    "estado": "Cerrada",
    "estado_bucket": "cerrada",
    "fecha_publicacion": "2026-04-24T11:07:00",
    "fecha_cierre": "2026-05-05T12:30:00",
    "dias_hasta_cierre": 11,
    "comprador_nombre": "I MUNICIPALIDAD DE HUALAIHUE",
    "comprador_rut": "69.252.200-1",
    "region": "Region de los Lagos",
    "comuna": "Hualaihue",
    "unidad_nombre": "DEPARTAMENTO DE ADMINISTRACION",
    "monto_estimado": null,
    "monto_adjudicado": null,
    "moneda": "CLP",
    "proveedor_adjudicado_nombre": "",
    "proveedor_adjudicado_rut": "",
    "transport_score": 3,
    "transport_rule": "score",
    "revision_decision": "INCLUIR",
    "revision_segmento": "",
    "revision_prioridad": "",
    "revision_confianza": "",
    "revision_pendiente_manual": false,
    "flag_mixed_bundle": false,
    "flag_clean_transport_amount": true,
    "adjudicacion_capturada": false,
    "requiere_refresh_adjudicacion": true,
    "fue_enriquecida": true,
    "ultima_revision": "2026-05-08 17:13:50",
    "ultima_actualizacion_detectada": "2026-05-08 17:13:50",
    "url_ficha": ""
  }
}
```

Si no existe el codigo:

- `404 not_found`

---

## 4.3 GET `/api/metadata/filters`

Objetivo:

- popular filtros del frontend

Fuentes:

- `transport_dataset_manifest_latest.json`

Respuesta recomendada:

```json
{
  "data": {
    "estado_bucket": ["adjudicada", "cerrada", "desierta", "otro", "publicada"],
    "region": ["Region Metropolitana de Santiago", "Region de Coquimbo"],
    "comuna": ["Santiago", "Coquimbo"],
    "periodo_publicacion": ["2026-02", "2026-03", "2026-04"],
    "revision_segmento": ["educacion", "salud", "social", "otros"],
    "revision_prioridad": ["ALTA", "MEDIA", "BAJA"],
    "revision_decision": ["INCLUIR", "INCLUIR_PARCIAL"]
  }
}
```

---

## 4.4 GET `/api/metadata/contract`

Objetivo:

- exponer contrato de datos y vistas de app

Fuentes:

- `transport_app_contract_latest.json`

Respuesta:

- devolver el contrato casi tal cual

---

## 4.5 GET `/api/market/summary`

Objetivo:

- alimentar tarjetas o resumenes de la pantalla `Mercado`

Fuentes:

- `transport_analytics_summary_*.json`
- o derivado equivalente latest

Respuesta recomendada:

```json
{
  "data": {
    "rows": 7676,
    "unique_codigos": 7676,
    "enriched_rows": 7676,
    "adjudicacion_capturada_rows": 5032,
    "refresh_pending_rows": 2644,
    "publicacion_min": "2026-02-04T17:10:00",
    "publicacion_max": "2026-04-24T11:07:00"
  }
}
```

---

## 4.6 GET `/api/market/buyers`

Objetivo:

- mostrar compradores agregados

Fuente:

- `transport_agg_buyers_*.csv`

Query params recomendados:

- `page`
- `page_size`
- `region`
- `sort`

Respuesta recomendada:

```json
{
  "data": [
    {
      "buyer_key": "buyer-key",
      "comprador_nombre_final": "I MUNICIPALIDAD ...",
      "comprador_rut": "69.000.000-0",
      "comprador_region_final": "Region Metropolitana de Santiago",
      "licitaciones": 24,
      "monto_estimado_total": 120000000.0,
      "monto_adjudicado_total": 90000000.0,
      "adjudicadas": 10,
      "enriquecidas": 24
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 25,
    "total_results": 200,
    "total_pages": 8
  }
}
```

---

## 4.7 GET `/api/market/regions`

Objetivo:

- mostrar comportamiento por region, periodo y estado

Fuente:

- `transport_agg_region_period_*.csv`

Query params recomendados:

- `region`
- `periodo_publicacion`
- `estado_bucket`

Respuesta recomendada:

```json
{
  "data": [
    {
      "comprador_region_final": "Region Metropolitana de Santiago",
      "publicacion_periodo": "2026-04",
      "estado_grupo": "adjudicada",
      "licitaciones": 120,
      "monto_estimado_total": 1000000000.0,
      "monto_adjudicado_total": 760000000.0
    }
  ]
}
```

---

## 4.8 GET `/api/system/health`

Objetivo:

- mostrar estado operativo general del dataset

Fuente:

- `mp_pipeline_health_*.json`

Respuesta:

- devolver resumen health latest

---

## 4.9 GET `/api/system/quality`

Objetivo:

- mostrar issues actuales de calidad

Fuentes:

- `transport_quality_summary_*.json`
- `transport_quality_issues_*.csv`

Respuesta recomendada:

```json
{
  "summary": {
    "total_rows": 7676,
    "issues_count": 3,
    "severity_counts": {
      "critical": 0,
      "warning": 151,
      "info": 3
    }
  },
  "issues": [
    {
      "issue_type": "adjudicadas_sin_adjudicacion_capturada",
      "severity": "warning",
      "count": 151,
      "description": "Licitaciones adjudicadas que aun no tienen adjudicacion capturada en el master."
    }
  ]
}
```

---

## 5. Reglas de filtro y sort del MVP

### 5.1 Filtros multivalor

Los filtros de tipo lista pueden aceptarse como:

- query repetida:
  - `?region=A&region=B`

o como csv simple:

- `?region=A,B`

La implementacion puede elegir una, pero debe quedar fija.

### 5.2 Sort permitido

Sort recomendado para `licitaciones`:

- `fecha_publicacion`
- `fecha_cierre`
- `monto_estimado`
- `monto_adjudicado`
- `transport_score`

Formato recomendado:

- `sort=fecha_publicacion:desc`

### 5.3 Page size

Limites recomendados:

- default: `25`
- maximo: `100`

---

## 6. Contrato de entidades futuras

El MVP no necesita exponerlas todavia, pero el contrato debe dejar espacio para:

- `/api/empresas`
- `/api/empresas/{empresa_id}`
- `/api/compradores`
- `/api/compradores/{comprador_id}`

Especialmente si luego queremos movernos a una experiencia mas parecida a inteligencia comercial tipo BI.

---

## 7. Decisiones tomadas

1. el MVP expone primero `licitaciones`, `metadata`, `market` y `system`
2. `licitaciones` es el dominio central inicial
3. `listing` y `detail` son las dos salidas obligatorias para la web
4. la API debe ser suficiente para frontend sin leer archivos directo
5. el contrato deja espacio para crecer a `empresas` mas adelante

---

## 8. Siguiente paso recomendado

Con este contrato listo, el siguiente paso natural es:

1. elegir stack tecnico del backend
2. implementar repositorios de lectura para `listing`, `detail`, `manifest`, `contract`, `health` y `quality`
3. exponer los endpoints MVP de la web
