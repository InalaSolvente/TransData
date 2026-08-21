# TransData Web App Backend Architecture

## 1. Proposito

Este documento define la arquitectura minima recomendada para el backend de la futura aplicacion web de TransData.

La idea es partir con una base simple y operable sobre los datasets actuales, pero dejando espacio para crecer hacia un producto de inteligencia sectorial mas amplio, con informacion adicional de empresas y compradores.

---

## 2. Objetivo del backend

El backend debe servir como capa de acceso estable para la aplicacion web.

No debe depender de la API de Mercado Publico en tiempo real.

Sus responsabilidades iniciales deberian ser:

- exponer licitaciones para consulta web
- servir filtros y resultados paginados
- entregar fichas detalladas por `codigo_licitacion`
- proveer metadata para filtros y facetas
- encapsular la lectura de datasets derivados

En una fase posterior, tambien deberia poder:

- integrar datos adicionales de empresas
- integrar perfiles de compradores
- habilitar vistas BI y comparativas
- soportar watchlists, favoritos y seguimiento

---

## 3. Tipo de aplicacion

La aplicacion objetivo es:

- una pagina web
- con backend propio
- con frontend separado de la logica de acceso a datos

La arquitectura recomendada es:

1. `Frontend web`
2. `Backend API`
3. `Serving layer / data access layer`
4. `Datasets derivados y maestros`

---

## 4. Principio rector

El backend no debe consultar directo la API publica como mecanismo principal de lectura.

Debe leer desde activos internos del proyecto:

- `transport_master_core`
- `transport_app_listing_latest.csv`
- `transport_app_detail_latest.csv`
- `analytics`
- `quality`
- `health`

Esto mantiene:

- velocidad
- estabilidad
- trazabilidad
- independencia de la API externa

---

## 5. Arquitectura minima recomendada

### 5.1 Capa 1: Frontend web

Responsabilidad:

- interfaz de usuario
- tablas, filtros, busqueda
- navegacion entre listado y ficha

No deberia:

- leer CSV directamente
- contener logica de negocio critica
- reconstruir joins complejos en cliente

### 5.2 Capa 2: Backend API

Responsabilidad:

- recibir requests del frontend
- validar parametros
- aplicar filtros, orden y paginacion
- responder JSON consistente

Esta es la capa que queremos definir ahora como MVP tecnico.

### 5.3 Capa 3: Data access / serving repository

Responsabilidad:

- leer datasets servidos
- normalizar tipos
- ocultar detalles de rutas y formatos
- entregar objetos listos para endpoints

Esta capa evita que cada endpoint abra archivos de forma desordenada.

### 5.4 Capa 4: Data assets

Responsabilidad:

- contener los activos generados por el pipeline

Activos base actuales:

- `data/master/licitaciones_transport_master_core.csv`
- `data/serving/transport_app_listing_latest.csv`
- `data/serving/transport_app_detail_latest.csv`
- `data/serving/transport_dataset_manifest_latest.json`
- `data/serving/transport_app_contract_latest.json`

---

## 6. Modelo de backend minimo

La primera version del backend deberia girar en torno a cuatro dominios:

1. `licitaciones`
2. `metadata`
3. `market`
4. `system`

### 6.1 Dominio `licitaciones`

Objetivo:

- alimentar el explorador y la ficha

Datasets fuente:

- `transport_app_listing_latest.csv`
- `transport_app_detail_latest.csv`

Endpoints iniciales sugeridos:

- `GET /api/licitaciones`
- `GET /api/licitaciones/{codigo_licitacion}`

### 6.2 Dominio `metadata`

Objetivo:

- devolver filtros, facetas y contrato de datos

Fuentes:

- `transport_dataset_manifest_latest.json`
- `transport_app_contract_latest.json`

Endpoints iniciales sugeridos:

- `GET /api/metadata/filters`
- `GET /api/metadata/contract`

### 6.3 Dominio `market`

Objetivo:

- exponer agregados simples para la futura vista Mercado

Fuentes:

- `analytics`
- agregados por comprador y region-periodo

Endpoints iniciales sugeridos:

- `GET /api/market/summary`
- `GET /api/market/buyers`
- `GET /api/market/regions`

### 6.4 Dominio `system`

Objetivo:

- exponer estado operativo del dataset

Fuentes:

- `quality`
- `health`

Endpoints iniciales sugeridos:

- `GET /api/system/health`
- `GET /api/system/quality`

---

## 7. Endpoints MVP recomendados

### 7.1 `GET /api/licitaciones`

Uso:

- alimentar la tabla principal

Parametros recomendados:

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

Respuesta esperada:

- filas de `listing`
- total de resultados
- pagina actual
- total de paginas

### 7.2 `GET /api/licitaciones/{codigo_licitacion}`

Uso:

- alimentar la ficha

Respuesta esperada:

- fila completa de `detail`

### 7.3 `GET /api/metadata/filters`

Uso:

- popular selects y filtros del frontend

Respuesta esperada:

- buckets y valores disponibles desde manifest

### 7.4 `GET /api/metadata/contract`

Uso:

- documentacion tecnica y futura autoconfiguracion del frontend

Respuesta esperada:

- contrato JSON de app

### 7.5 `GET /api/market/summary`

Uso:

- primera capa de visualizacion o tarjetas de mercado

### 7.6 `GET /api/system/health`

Uso:

- vista interna de estado operativo

---

## 8. Forma de crecimiento recomendada

La arquitectura debe permitir evolucionar desde:

- `licitacion` como unidad central

hacia:

- `empresa`
- `comprador`
- `mercado`
- `sector`

Eso importa porque la aplicacion no deberia quedarse solo en "ver licitaciones", sino abrir la puerta a una experiencia mas parecida a inteligencia comercial.

Ejemplo de evolucion futura:

### Etapa 1

- explorar licitaciones
- ver detalle
- mirar agregados basicos

### Etapa 2

- crear entidad `empresa`
- asociar adjudicatarios a un perfil propio
- guardar razon social, rut, rubro, historial de adjudicaciones

### Etapa 3

- crear entidad `comprador`
- consolidar historial por organismo
- comparar demanda por comprador o region

### Etapa 4

- construir vistas tipo BI
- comparativas por empresa
- market share aproximado
- recurrencia de compradores
- patrones de adjudicacion

---

## 9. Entidades futuras recomendadas

Aunque hoy no las implementemos, conviene dejar nombradas estas entidades:

1. `Licitacion`
2. `Empresa`
3. `Comprador`
4. `Adjudicacion`
5. `Periodo`
6. `Segmento`

Hoy el backend MVP debe arrancar con `Licitacion`, pero sin cerrarse a que luego el centro de navegacion tambien pueda ser `Empresa`.

---

## 10. Almacenamiento recomendado para el MVP

Para el MVP tecnico, la opcion mas simple y realista es:

1. leer desde los CSV y JSON servidos
2. encapsular esa lectura en una capa repository

No hace falta introducir una base de datos relacional todavia si:

- el volumen sigue siendo manejable
- el uso inicial es exploracion web interna

Pero la arquitectura debe permitir migrar despues a:

- SQLite
- PostgreSQL
- DuckDB

sin reescribir el frontend.

---

## 11. Recomendacion de stack conceptual

Sin fijar aun una tecnologia cerrada, el backend deberia poder ofrecer:

- API HTTP JSON
- filtros y paginacion
- cache ligera o lectura optimizada
- separacion entre endpoints y acceso a datos

Lo importante por ahora no es el framework exacto, sino la forma:

- `routes`
- `services`
- `repositories`
- `schemas`

---

## 12. Stack tecnico recomendado

La recomendacion para TransData hoy es:

### 12.1 Frontend web

- `Next.js` con `TypeScript`
- `TanStack Query`
- `TanStack Table`
- `shadcn/ui`
- `Recharts`

Motivo:

- sirve muy bien para una web de exploracion con tablas, filtros y vistas de detalle
- facilita SSR o carga mixta si mas adelante hace falta
- deja espacio para crecer a una app mas rica en navegacion y BI

### 12.2 Backend API

- `FastAPI`
- `Pydantic`
- `Uvicorn`

Motivo:

- ya esta alineado con el stack actual del repo
- encaja muy bien con JSON API, filtros y contratos tipados
- es rapido de implementar para un MVP interno o semi-productivo

### 12.3 Capa de acceso a datos

- `DuckDB` como motor de consulta local
- lectura desde `CSV` servidos en la primera etapa
- migracion recomendada a `Parquet` cuando el backend empiece a usarse de forma intensiva

Motivo:

- consulta datasets analiticos muy bien
- evita levantar una base relacional demasiado pronto
- simplifica filtros, orden, paginacion y agregados
- es muy buena base para una app tipo inteligencia sectorial

### 12.4 Persistencia transaccional futura

- `PostgreSQL`

Motivo:

- no hace falta para el MVP de lectura
- pero es la mejor candidata cuando aparezcan:
  - usuarios
  - favoritos
  - watchlists
  - notas
  - perfiles enriquecidos de empresas
  - entidades propias no derivadas del pipeline

### 12.5 Pipeline de datos

- mantener `Python + pandas`
- mantener scripts batch existentes
- seguir usando `.env` como control operativo

Motivo:

- ya es el lenguaje dominante del repo
- evita reescrituras innecesarias
- es suficiente para la fase actual del proyecto

### 12.6 Visualizacion analitica

- en frontend: `Recharts`
- opcional futuro: capa BI embebida o dashboards internos

Motivo:

- suficiente para una primera capa de insight
- no obliga a introducir una herramienta externa todavia

---

## 13. Decisiones ya tomadas

Estas decisiones quedan fijadas para evitar volver a discutir lo mismo:

1. la aplicacion es web
2. la API publica no es la fuente de lectura del frontend
3. el backend debe consumir datasets derivados internos
4. el primer dominio funcional es `licitaciones`
5. el diseno debe permitir crecer a `empresas` y BI mas adelante
6. el MVP no necesita base de datos obligatoria desde el dia uno
7. el stack recomendado es `Next.js + FastAPI + DuckDB`

---

## 14. Siguiente paso recomendado

Con esta arquitectura definida, el siguiente paso natural es:

1. definir el contrato minimo de endpoints
2. elegir stack tecnico del backend
3. implementar un backend web pequeno sobre `listing` y `detail`
