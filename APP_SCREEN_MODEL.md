# TransData App Screen Model

## 1. Proposito

Este documento define la estructura minima de pantallas y navegacion de la futura aplicacion de TransData.

Su objetivo es traducir el modelo de uso ya definido a una forma concreta de producto, sin amarrarnos todavia a una tecnologia o framework especifico.

---

## 2. Usuario principal

Usuario objetivo:

- analista comercial
- analista de inteligencia de mercado
- equipo interno que revisa oportunidades de licitaciones

Necesidad principal:

- encontrar licitaciones relevantes rapido
- entender su contexto
- decidir si requieren seguimiento

---

## 3. Estructura minima de la app

La aplicacion deberia tener como base estas vistas:

1. `Explorador de Licitaciones`
2. `Ficha de Licitacion`
3. `Vista de Mercado`
4. `Panel de Calidad y Estado`

En una primera version, las dos vistas realmente imprescindibles son:

1. `Explorador de Licitaciones`
2. `Ficha de Licitacion`

---

## 4. Navegacion principal

Navegacion superior o lateral recomendada:

1. `Licitaciones`
2. `Mercado`
3. `Calidad`

Y dentro de `Licitaciones`:

- tabla principal
- filtros
- acceso a ficha individual

---

## 5. Pantalla 1: Explorador de Licitaciones

Objetivo:

- ser la vista principal de trabajo diario
- permitir busqueda, filtrado, orden y escaneo rapido

Fuente de datos:

- `transport_app_listing_latest.csv`

Componentes esperados:

- tabla de resultados
- buscador por texto
- filtros laterales o superiores
- ordenamiento
- paginacion
- acceso a ficha

Filtros minimos:

- `estado_bucket`
- `region`
- `comuna`
- `periodo_publicacion`
- `revision_segmento`
- `revision_prioridad`
- `revision_decision`
- `adjudicacion_capturada`
- `requiere_refresh_adjudicacion`

Columnas visibles por defecto:

- `nombre`
- `estado_bucket`
- `fecha_publicacion`
- `fecha_cierre`
- `comprador_nombre`
- `region`
- `monto_estimado`
- `monto_adjudicado`
- `revision_segmento`
- `revision_prioridad`

Acciones esperadas:

- abrir ficha
- copiar `codigo_licitacion`
- abrir `url_ficha`

---

## 6. Pantalla 2: Ficha de Licitacion

Objetivo:

- ver el caso completo
- entender comprador, estado, descripcion y adjudicacion
- apoyar evaluacion comercial o analitica

Fuente de datos:

- `transport_app_detail_latest.csv`

Secciones recomendadas:

1. encabezado
   - nombre
   - codigo
   - estado
   - fechas clave
2. contexto del comprador
   - comprador
   - RUT
   - region
   - comuna
   - unidad
3. oportunidad economica
   - monto estimado
   - monto adjudicado
   - moneda
4. adjudicacion
   - proveedor adjudicado
   - RUT proveedor
   - estado de captura
5. clasificacion y revision
   - score transporte
   - regla aplicada
   - segmento validado
   - prioridad
   - confianza
   - mixed bundle
6. trazabilidad operativa
   - fue enriquecida
   - requiere refresh
   - ultima revision
   - ultima actualizacion detectada
7. descripcion completa

Acciones esperadas:

- volver al listado preservando filtros
- abrir ficha original

---

## 7. Pantalla 3: Vista de Mercado

Objetivo:

- mirar patrones agregados sin entrar una por una a las licitaciones

Fuentes de datos:

- `analytics`
- agregados por comprador y periodo

Contenidos sugeridos:

- top compradores
- distribucion por region
- distribucion por estado
- evolucion por periodo
- comparacion por segmento validado

Esta vista es importante, pero no bloquea una primera version usable.

---

## 8. Pantalla 4: Panel de Calidad y Estado

Objetivo:

- dar confianza operativa a quien usa la base
- mostrar que tan actualizado y confiable esta el dataset

Fuentes de datos:

- `quality`
- `health`
- metricas de refresh

Contenidos sugeridos:

- filas enriquecidas
- pendientes de refresh
- adjudicaciones capturadas
- issues de calidad
- ultimo health report

Esta vista es muy util para equipo interno, aunque puede quedar fuera del MVP visual.

---

## 9. Flujo principal del usuario

Flujo principal:

1. entrar a `Licitaciones`
2. filtrar por region, estado, segmento o periodo
3. revisar resultados en tabla
4. abrir ficha de una licitacion
5. decidir si es relevante para seguimiento

Flujo secundario:

1. entrar a `Mercado`
2. revisar patrones por comprador, region o periodo
3. volver al listado para abrir casos concretos

---

## 10. Prioridad para una primera version

Orden recomendado de implementacion:

1. `Explorador de Licitaciones`
2. `Ficha de Licitacion`
3. `Vista de Mercado`
4. `Panel de Calidad y Estado`

Eso permite lanzar primero una app realmente util sin esperar a tener toda la capa analitica visual completa.

---

## 11. Relacion con el contrato de datos

Este modelo de pantallas debe apoyarse en:

- `APP_DATA_CONTRACT.md`
- `data/serving/transport_app_contract_latest.json`

En particular:

- `listing` alimenta la pantalla de exploracion
- `detail` alimenta la ficha
- `codigo_licitacion` conecta ambas

---

## 12. Decisiones ya tomadas

Para evitar ambiguedad mas adelante, estas decisiones quedan fijadas:

1. la app no depende de la API en tiempo real
2. el origen preferente es `transport_master_core`
3. la pantalla principal es un explorador de licitaciones, no un dashboard de marketing
4. la ficha detallada es parte del MVP funcional
5. la vista de mercado es importante, pero puede venir despues del explorador y la ficha
