# TransData App Data Contract

## 1. Proposito

Este documento define el contrato de datos recomendado para la futura aplicacion de TransData.

No reemplaza los artefactos generados en `data/serving/`, pero si fija la idea base de consumo para producto:

- una vista liviana para listados y busqueda
- una vista detallada para ficha por licitacion

---

## 2. Fuentes de datos

La fuente preferente para la aplicacion es:

- `data/master/licitaciones_transport_master_core.csv`

Si el core no existe, las capas derivadas pueden caer temporalmente a:

- `data/master/licitaciones_transport_master.csv`

La aplicacion no debe leer directo desde la API de Mercado Publico.

---

## 3. Vistas de serving

La capa de serving actual entrega tres artefactos:

- `data/serving/transport_dataset_latest.csv`
- `data/serving/transport_app_listing_latest.csv`
- `data/serving/transport_app_detail_latest.csv`

Y dos metadatos asociados:

- `data/serving/transport_dataset_manifest_latest.json`
- `data/serving/transport_app_contract_latest.json`

---

## 4. Vista Listing

Archivo:

- `transport_app_listing_latest.csv`

Objetivo:

- tabla principal de resultados
- busqueda y filtros
- ordenamiento y paginacion

Clave:

- `codigo_licitacion`

Columnas principales:

- `codigo_licitacion`
- `nombre`
- `estado`
- `estado_bucket`
- `fecha_publicacion`
- `fecha_cierre`
- `periodo_publicacion`
- `comprador_nombre`
- `comprador_rut`
- `region`
- `comuna`
- `monto_estimado`
- `monto_adjudicado`
- `moneda`
- `transport_score`
- `revision_segmento`
- `revision_prioridad`
- `revision_decision`
- `flag_mixed_bundle`
- `flag_clean_transport_amount`
- `adjudicacion_capturada`
- `requiere_refresh_adjudicacion`
- `fue_enriquecida`
- `url_ficha`

Filtros recomendados:

- `estado_bucket`
- `region`
- `comuna`
- `periodo_publicacion`
- `revision_segmento`
- `revision_prioridad`
- `revision_decision`
- `adjudicacion_capturada`
- `requiere_refresh_adjudicacion`

Orden recomendado por defecto:

1. `fecha_publicacion desc`
2. `codigo_licitacion asc`

---

## 5. Vista Detail

Archivo:

- `transport_app_detail_latest.csv`

Objetivo:

- ficha individual por licitacion
- lectura completa del caso
- soporte de analisis comercial

Clave:

- `codigo_licitacion`

Columnas principales:

- `codigo_licitacion`
- `nombre`
- `descripcion`
- `estado`
- `estado_bucket`
- `fecha_publicacion`
- `fecha_cierre`
- `dias_hasta_cierre`
- `comprador_nombre`
- `comprador_rut`
- `region`
- `comuna`
- `unidad_nombre`
- `monto_estimado`
- `monto_adjudicado`
- `moneda`
- `proveedor_adjudicado_nombre`
- `proveedor_adjudicado_rut`
- `transport_score`
- `transport_rule`
- `revision_decision`
- `revision_segmento`
- `revision_prioridad`
- `revision_confianza`
- `revision_pendiente_manual`
- `flag_mixed_bundle`
- `flag_clean_transport_amount`
- `adjudicacion_capturada`
- `requiere_refresh_adjudicacion`
- `fue_enriquecida`
- `ultima_revision`
- `ultima_actualizacion_detectada`
- `url_ficha`

---

## 6. Reglas de negocio importantes

### 6.1 Mixed bundle

Si `flag_mixed_bundle=true`, el monto no debe usarse directamente para market sizing sin depuracion adicional.

### 6.2 Revision manual

`revision_decision`, `revision_segmento`, `revision_prioridad` y `revision_confianza` representan la capa de revision manual ya aplicada al `transport master core`.

### 6.3 Refresh pendiente

Si `requiere_refresh_adjudicacion=true`, la licitacion puede seguir cambiando en su detalle de adjudicacion.

### 6.4 Adjudicacion capturada

`adjudicacion_capturada=true` indica que ya existe un nivel util de captura de adjudicatario en el master.

---

## 7. Contrato operativo

La futura aplicacion deberia asumir:

1. `listing` como vista principal de consulta
2. `detail` como vista de ficha
3. `codigo_licitacion` como clave de enlace entre vistas
4. el manifest y el contract JSON como metadata de apoyo para filtros y tipos

---

## 8. Evolucion esperada

Este contrato puede ampliarse cuando:

- el refresh estabilice mejor estados y adjudicaciones
- aparezcan nuevas necesidades de producto
- se defina el backend o la interfaz final

Pero la idea base deberia mantenerse:

- una vista de listado clara
- una vista de detalle rica
- un origen estable desde `transport master core`
