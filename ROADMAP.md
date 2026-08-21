# TransData Roadmap

## 1. Propósito de este documento

Este roadmap es un documento vivo.  
Puede y debe ir cambiando a medida que el proyecto avance, cambien las prioridades o se descubran nuevas restricciones técnicas y de negocio.

Su objetivo es ordenar la evolución del proyecto TransData de manera incremental y realista.

---

## 2. Objetivo general del roadmap

Construir progresivamente un sistema de datos robusto sobre licitaciones de transporte que termine habilitando una aplicación útil para consulta, análisis e inteligencia sectorial.

La secuencia deseada es:

1. asegurar cobertura de ingest
2. estabilizar transform
3. consolidar master sectorial
4. enriquecer detalle
5. actualizar incrementalmente
6. habilitar consumo en una aplicación

---

## 3. Estado actual del proyecto

Actualmente el proyecto ya cuenta con:

- ingest histórico funcional
- cobertura por `fecha_consulta`
- raw persistido y reutilizable
- parse batch de raws
- clasificación sectorial para transporte
- `transport master` consolidado
- `transport master core` reconstruible con revisión manual y auditoría reproducible
- enrich completo sobre `transport master`
- refresh incremental funcionando y ya en validación operativa real
- capa analítica derivada inicial
- quality check del `transport master`
- capa de serving inicial para futura aplicación
- vistas de serving separadas para `listing` y `detail` de aplicación
- contrato mínimo de endpoints del backend web definido
- stack tecnico recomendado definido para la app web
- backend MVP scaffolded sobre FastAPI
- frontend MVP scaffolded sobre Next.js

Estado operativo actual:

- el enrich ya cubre todo el `transport master`
- el refresh ya demostró captura real de adjudicatarios en tandas controladas
- todavía puede requerir ajustes finos a medida que aumente la cobertura del refresh
- las capas `analytics`, `quality` y `serving` deben tratarse como derivadas provisionales hasta estabilizar mejor el refresh
- existe un runner operativo con presets diarios y semanales para orquestar refresh, sincronización de derivados y health report
- existe una auditoría del filtro de transporte y una cola de revisión manual agrupada por dominio
- `analytics`, `quality` y `serving` ya pueden derivarse desde `transport master core` cuando existe

El foco actual debe estar en robustecer y limpiar el flujo sectorial antes de avanzar a la aplicación final.

---

## 4. Próximos pasos

### 4.1 Fase inmediata

Objetivo: consolidar el flujo actual de punta a punta.

Tareas:

1. estabilizar definitivamente el flujo:
   - ingest
   - transform
   - selección transporte
   - transport master
   - transport master core
   - enrich
   - refresh
   - runner operativo
2. seguir expandiendo el refresh por tandas hasta cubrir el master sectorial
3. revisar y mejorar reglas de clasificación de transporte
   - mantener auditoría automática del filtro
   - aplicar revisión manual guiada sobre el universo pendiente
   - mantener reconstrucción reproducible del `transport master core`
4. reducir código residual o scripts que no formen parte del flujo principal

### 4.2 Fase siguiente

Objetivo: mejorar operación incremental.

Tareas:

1. mantener enrich incremental solo para registros nuevos o pendientes
2. mantener refresh incremental con prioridad por cola y revisita por threshold
3. agregar métricas de cobertura y estado del pipeline
4. generar resúmenes más claros para operación diaria
5. mejorar consistencia entre `transport master`, `transport master core`, `analytics`, `quality` y `serving`
6. incorporar señales de calidad del filtro de transporte en la observabilidad operativa
7. usar `transport master core` como fuente preferente para capas derivadas y futura aplicación

### 4.3 Fase de refresh

Objetivo: mantener vivo el master sin reconsultar todo el histórico.

Tareas:

1. actualizar estados de licitaciones ya guardadas
2. detectar cierres y adjudicaciones
3. refrescar solo registros activos o relevantes
4. separar refresh de estado y refresh de detalle si conviene

### 4.4 Fase analítica

Objetivo: preparar datos para explotación de negocio.

Tareas:

1. seguir ajustando columnas derivadas útiles para análisis
2. preparar agregados por organismo, región, estado y periodo
3. revisar consistencia y calidad del `transport master`
4. mantener datasets listos para dashboards y consultas
5. recalcular derivados relevantes cuando el refresh cambie el master

Nota operativa:

- cualquier capa analítica que construyamos antes de validar el refresh debe tratarse como derivada provisional
- puede requerir ajustes en columnas, reglas o agregados cuando observemos cómo cambian estados y adjudicaciones después del refresh

### 4.5 Fase de aplicación

Objetivo: construir la futura aplicación sobre el master sectorial.

Modelo de uso principal definido:

- usuario objetivo primario:
  - analista comercial o de inteligencia de mercado
  - equipo interno que busca oportunidades, tendencias y trazabilidad de compradores
- tarea principal:
  - descubrir licitaciones relevantes
  - filtrarlas rápido
  - abrir una ficha detallada
  - decidir si vale seguimiento comercial o analítico
- lógica base de producto:
  - una vista `listing` para búsqueda, filtros, orden y priorización
  - una vista `detail` para lectura profunda de cada licitación
  - ambas conectadas por `codigo_licitacion`
- fuente de datos esperada:
  - `transport_app_listing_latest.csv`
  - `transport_app_detail_latest.csv`
  - con `transport_master_core` como origen preferente
- arquitectura de backend definida:
  - aplicación web
  - backend API propio
  - capa de acceso a datasets derivados
  - crecimiento futuro hacia empresas, compradores y BI
- contrato API MVP definido:
  - `licitaciones`
  - `metadata`
  - `market`
  - `system`
- stack recomendado:
  - `Next.js`
  - `FastAPI`
  - `DuckDB`
  - `PostgreSQL` mas adelante para datos de aplicacion

Estructura de pantallas definida:

1. `Licitaciones`
   - pantalla principal
   - tabla, filtros, orden y paginacion
2. `Ficha de Licitacion`
   - detalle completo por `codigo_licitacion`
3. `Mercado`
   - agregados y patrones
4. `Calidad`
   - salud operativa y estado del dataset

Orden recomendado de implementacion:

1. `Licitaciones`
2. `Ficha de Licitacion`
3. `Mercado`
4. `Calidad`

Tareas:

1. definir modelo de uso principal
   - listing liviano para búsqueda
   - detail enriquecido por licitación
   - flujo principal: buscar -> filtrar -> abrir ficha -> evaluar oportunidad
   - flujo secundario: explorar mercado -> comparar compradores/segmentos -> detectar patrones
2. construir interfaz de consulta
   - tabla principal basada en `listing`
   - ficha basada en `detail`
   - navegación mínima: `Licitaciones -> Ficha`
3. definir contrato mínimo del backend web
   - endpoints de `licitaciones`
   - endpoints de `metadata`
   - endpoints de `market`
   - endpoints de `system`
   - respuestas JSON, filtros, paginacion y errores
4. implementar backend MVP con el stack recomendado
   - scaffolding FastAPI
   - repositorios para `listing`, `detail`, `metadata`, `market`, `system`
5. implementar frontend MVP con el stack recomendado
   - pantalla `Licitaciones`
   - pantalla `Ficha de Licitacion`
   - bases de `Mercado` y `Calidad`
6. permitir filtros por fechas, región, comprador, estado y segmento validado
7. agregar vistas de historial, adjudicación y detalle enriquecido
8. habilitar análisis exploratorio y visualizaciones
9. dejar espacio para una futura capa de favoritos, seguimiento o watchlist sin depender de la API
10. preparar la expansión futura hacia entidad `empresa` y vistas tipo BI

---

## 5. Prioridades vigentes

Hoy las prioridades deberían ser, en este orden:

1. robustez operativa del pipeline
2. calidad del `transport master`
3. refresh incremental confiable y escalable
4. consistencia de capas derivadas (`analytics`, `quality`, `serving`)
5. preparación del modelo de datos para la aplicación

---

## 6. Entregables deseados en el mediano plazo

Los entregables más valiosos a mediano plazo son:

- un `transport master` confiable y estable
- un `transport master core` listo para consumo analitico y aplicacion
- un enrich incremental utilizable
- un refresh de estados y adjudicaciones funcional y trazable
- una capa de datos lista para consumo analítico
- una base clara para desarrollar la aplicación

---

## 7. Riesgos conocidos

Riesgos que deben seguir considerándose:

- inestabilidad de la API de Mercado Público
- cambios de estructura en las respuestas
- clasificación imperfecta de transporte
- costo operativo de enrich a gran escala
- duplicidad o ruido si el pipeline pierde separación por etapas

---

## 8. Criterios para actualizar este roadmap

Este roadmap debe actualizarse cuando ocurra alguna de estas situaciones:

- se cierra una fase importante
- cambia la prioridad del proyecto
- aparece una restricción técnica relevante
- se redefine el objetivo de la futura aplicación
- se detecta que una línea de trabajo dejó de ser necesaria

---

## 9. Regla práctica de evolución

Antes de abrir una nueva línea de trabajo, validar:

1. si mejora el activo central del proyecto
2. si reduce riesgo operativo
3. si facilita la futura aplicación
4. si evita dependencia innecesaria de la API
5. si aporta claridad en vez de complejidad

Si no cumple al menos parte importante de eso, probablemente no es el siguiente paso correcto.
