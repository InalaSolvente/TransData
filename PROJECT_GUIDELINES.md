# TransData Project Guidelines

## 1. Propósito del proyecto

TransData tiene como propósito construir una base de datos histórica, confiable y utilizable sobre licitaciones públicas, con foco inicial en el sector de transporte terrestre de pasajeros en Chile.

El objetivo no es solo descargar datos desde Mercado Público, sino convertir una fuente pública inestable en un activo de datos reutilizable, estructurado y mantenible.

Este proyecto debe habilitar:

- análisis de mercado
- inteligencia competitiva
- seguimiento histórico de licitaciones
- exploración de oportunidades
- soporte de datos para una futura aplicación

---

## 2. Objetivo principal de la aplicación futura

La futura aplicación debe apoyarse principalmente en un master sectorial de transporte ya consolidado y enriquecido.

Su objetivo principal será facilitar:

- búsqueda y consulta de licitaciones relevantes
- análisis histórico por organismo, región, estado y fechas
- exploración de tendencias del mercado
- soporte a análisis interno y decisiones comerciales
- futura construcción de dashboards y vistas analíticas

La aplicación no debe depender en tiempo real de la API de Mercado Público como fuente principal de lectura.

---

## 3. Visión general

TransData se concibe como un sistema tipo Data-as-a-Service para licitaciones públicas.

La lógica general del proyecto es:

1. extraer licitaciones desde la API
2. guardar respuestas raw para trazabilidad
3. transformar raws a estructura tabular limpia
4. identificar el subconjunto relevante para transporte
5. consolidarlo en un master sectorial
6. enriquecerlo con mayor detalle
7. dejarlo listo para consumo analítico y de aplicación

---

## 4. Principios rectores

### 4.1 Robustez primero

La API de Mercado Público debe asumirse como inestable.  
Toda pieza del pipeline debe tolerar:

- errores 500
- timeouts
- respuestas vacías
- respuestas parciales
- cambios o diferencias en estructura JSON

El sistema debe fallar de forma controlada y registrar evidencia suficiente para reintentos y diagnóstico.

### 4.2 Raw como fuente de verdad operativa

Toda consulta válida debe quedar almacenada en `data/raw/`.

La capa raw permite:

- reprocesar sin volver a consultar la API
- auditar históricos
- reconstruir derivados
- corregir transformaciones futuras sin perder cobertura previa

### 4.3 Separación estricta de etapas

Las responsabilidades deben mantenerse separadas:

- `ingest`: consulta y persistencia raw
- `transform`: parse y normalización tabular
- `transport filter`: selección sectorial
- `master`: consolidación histórica
- `enrich`: consulta de detalles adicionales
- `refresh`: actualización incremental futura

### 4.4 Idempotencia

Una corrida repetida no debe:

- duplicar registros
- corromper salidas existentes
- inflar contadores operativos artificialmente
- requerir limpieza manual

La clave principal de consolidación debe ser `codigo_licitacion`.

### 4.5 Reprocesamiento simple

Si existe raw, debe poder rehacerse:

- parse
- clasificación transporte
- master
- enrich derivado

sin requerir nuevas consultas a la API salvo cuando sea estrictamente necesario.

---

## 5. Arquitectura lógica esperada

### 5.1 Ingest

Responsabilidades:

- consultar la API
- guardar raws
- registrar fallos
- registrar cobertura de fechas
- evitar reconsultas innecesarias

Restricciones:

- no hacer transformaciones pesadas
- no aplicar filtrado sectorial destructivo

### 5.2 Transform

Responsabilidades:

- leer raws ya almacenados
- extraer `Listado`
- normalizar columnas
- generar salidas procesadas reutilizables

### 5.3 Selección de transporte

Responsabilidades:

- clasificar licitaciones de transporte
- dejar trazabilidad del criterio de clasificación
- operar como derivado del processed, no del raw directo

### 5.4 Master sectorial

Responsabilidades:

- consolidar licitaciones de transporte en un archivo histórico único
- evitar duplicados
- conservar metadata operativa
- servir como dataset central para análisis y futura aplicación

### 5.5 Enrich

Responsabilidades:

- consultar detalle por `codigo_licitacion`
- agregar campos adicionales relevantes
- ejecutarse incrementalmente sobre el master sectorial

---

## 6. Política de ingest

### 6.1 Estrategia de consulta

La estrategia por defecto debe minimizar presión sobre la API.

Cuando la API lo permita, se debe preferir consulta por fecha completa antes que fragmentación innecesaria por estado.

### 6.2 Cobertura por fecha real

La cobertura del ingest debe medirse por `fecha_consulta`, no por `days_ago`.

Esto evita reconsultar el mismo día calendario solo porque cambió su desplazamiento relativo.

### 6.3 Backfill incremental

El batch de ingest debe poder ejecutarse varias veces hacia atrás y consultar solo fechas no cubiertas exitosamente.

### 6.4 Evidencia operativa

Cada falla relevante debe registrar:

- `fecha_consulta`
- `estado_consulta` si aplica
- `query_mode`
- `http_status`
- `motivo`
- `attempts`
- `last_error`
- `response_snippet` cuando sea útil

---

## 7. Política de transformación

### 7.1 Parse tolerante

El parser debe tolerar variaciones del JSON sin romper la corrida completa.

### 7.2 Normalización consistente

Las columnas de salida deben ser estables y fáciles de consumir.  
Campos prioritarios:

- `codigo_licitacion`
- `nombre_licitacion`
- `descripcion`
- `estado_actual`
- `fecha_publicacion`
- `fecha_cierre`
- `comprador_nombre`
- `comprador_rut`
- `region`

### 7.3 Transform no destructivo

El transform produce derivados, pero no modifica el raw.

---

## 8. Política sectorial de transporte

### 8.1 El filtro de transporte es derivado

La selección de transporte ocurre después del parse y no debe reemplazar la raw layer.

### 8.2 Clasificación trazable

Toda clasificación debe poder explicarse mediante:

- score
- reglas positivas
- reglas negativas
- campos donde hubo match

### 8.3 Master sectorial prioritario

El activo principal de negocio del proyecto es el `transport master`, porque concentra el universo relevante para análisis y aplicación.

---

## 9. Política de master

### 9.1 Master general

Puede existir un master amplio de licitaciones como respaldo estructural e histórico general.

### 9.2 Master sectorial

El master más importante para el producto es el master de transporte:

- una fila por `codigo_licitacion`
- histórico consolidado
- metadata operativa
- columnas de enrich

### 9.3 Append incremental

Solo deben agregarse o actualizarse registros nuevos o modificados.  
No se debe reconstruir desde cero como práctica normal si puede evitarse.

---

## 10. Política de enrich

### 10.1 Enrich sobre transport master

El enrich debe ejecutarse sobre el master sectorial y no sobre todo el universo de licitaciones.

### 10.2 Enrich incremental

Debe priorizar:

- registros nuevos
- registros pendientes
- reintentos de errores recuperables

### 10.3 Persistencia del estado de enrich

Cada fila debe poder indicar:

- si fue enriquecida
- cuándo
- si tuvo error
- qué detalle se obtuvo

---

## 11. Política de limpieza del código

### 11.1 Menos scripts huérfanos

Los archivos bajo `src/transform/` deben responder a funciones reales del pipeline.

### 11.2 Una responsabilidad por módulo

Cada archivo debe tener una responsabilidad clara:

- parsear
- filtrar
- consolidar
- enriquecer
- refrescar
- orquestar

### 11.3 Evitar duplicación funcional

No deben convivir dos scripts que hagan esencialmente lo mismo con nombres distintos.

---

## 12. Flujo operativo recomendado

El flujo recomendado hoy es:

1. correr ingest para nuevos días o backfill pendiente
2. correr transform batch sobre raws nuevos
3. seleccionar licitaciones relevantes para transporte
4. consolidarlas en `transport master`
5. enriquecer el `transport master`

---

## 13. Criterio para futuras decisiones

Toda mejora futura debería evaluarse con estas preguntas:

1. ¿Reduce dependencia de la API?
2. ¿Mejora trazabilidad?
3. ¿Facilita reprocesamiento?
4. ¿Evita duplicación?
5. ¿Aporta valor al master sectorial?
6. ¿Mantiene el sistema simple de operar?

Si la respuesta es no, probablemente no es prioritaria todavía.

