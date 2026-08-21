# TransData: origen, vision y estado actual

## Como nacio el proyecto

TransData nace para convertir datos publicos dispersos y dificiles de operar en informacion util para decisiones de negocio. El primer dominio elegido es el transporte terrestre de pasajeros en Chile, usando las licitaciones publicas de Mercado Publico / ChileCompra.

La necesidad inicial nunca fue solo descargar licitaciones. El proyecto busca construir un activo de datos historico, trazable y reutilizable para entender oportunidades, compradores, estados, adjudicaciones y comportamiento del mercado.

Desde el comienzo se asumio una restriccion central: la API de Mercado Publico es inestable y no puede tratarse como una fuente perfectamente confiable. Por eso la arquitectura conserva los datos raw, separa las etapas del pipeline y permite reprocesar sin volver a depender de la API.

## Idea central

TransData busca convertirse en una plataforma de inteligencia sectorial y Data-as-a-Service. Su primer producto de datos es un universo confiable de licitaciones de transporte, sobre el que un analista comercial, empresa proveedora o equipo de inteligencia puede descubrir procesos relevantes, filtrarlos, revisar una ficha enriquecida y analizar compradores, estados y adjudicaciones.

La licitacion es la entidad inicial, pero no es el limite del producto. La arquitectura debe poder crecer hacia empresas, compradores, adjudicatarios, contratos y vistas BI comparables a una plataforma de inteligencia comercial sectorial.

## Decisiones que guiaron el desarrollo

- Separar ingest y transform.
- Guardar siempre una capa raw reutilizable.
- Ejecutar el ingest historico en ventanas pequenas para tolerar una API inestable.
- Priorizar idempotencia, trazabilidad y reprocesamiento.
- Consolidar una fuente maestra sin perder evidencia de las etapas previas.
- Aplicar enrich y refresh como procesos separados.
- Usar revision manual auditada cuando las reglas automaticas no bastan.
- Preparar datasets de serving antes de conectar una aplicacion web.

Cada etapa tiene una responsabilidad clara y puede inspeccionarse o repetirse sin convertir el pipeline en un script monolitico.

## Evolucion del pipeline

```text
Mercado Publico API
  -> raw persistido por fecha_consulta
  -> parse y normalizacion tabular
  -> master general de licitaciones
  -> filtro de transporte, auditoria y revision manual
  -> transport master y transport master core
  -> enrich de detalle y refresh de estado/adjudicacion
  -> analytics, quality, serving y datasets de aplicacion
  -> API web y frontend de consulta
```

La separacion entre `transport master` y `transport master core` es importante. El primero conserva el universo sectorial enriquecido; el segundo es la version depurada para analitica y aplicacion, reconstruible desde reglas y decisiones manuales auditadas.

## Donde esta hoy el proyecto

TransData ya supero la fase exploratoria. El pipeline principal existe, produce datos y tiene capas operativas para controlar su calidad.

Segun el ultimo health report registrado el 8 de mayo de 2026, el proyecto contaba con:

- 69 archivos raw y 1.824 fechas de consulta exitosas.
- 123.347 licitaciones en el master general.
- 7.848 licitaciones en el `transport master` y 7.676 en el `transport master core`.
- Enrich aplicado al universo de transporte.
- 7.847 refresh exitosos y 1 error registrado.
- 5.135 adjudicaciones capturadas y 2.713 aun pendientes.
- 362 decisiones de revision manual aplicadas y 16 casos aun como `REVISAR_MANUAL`.

Tambien estan disponibles las capas derivadas de analytics, quality, serving, listing y detail. Se definieron contratos de datos, modelo de pantallas, arquitectura de backend y contrato de API. El backend MVP en FastAPI y el frontend MVP en Next.js ya fueron scaffolded y pueden levantarse localmente.

## Foco actual

La etapa actual combina estabilizacion operativa y validacion del producto web.

En datos, el foco es completar el refresh en tandas controladas, verificar que disminuya el backlog de adjudicaciones pendientes, revisar la consistencia de estados y cerrar los casos restantes de revision manual. Despues de cambios grandes, deben regenerarse y revisarse las capas de analytics, quality y serving.

En producto, el foco inmediato es validar el MVP completo con la API local: listado de licitaciones, filtros, ficha individual, vista de mercado y vista de calidad. Una vez validado el comportamiento, se puede mejorar la capa de consulta, posiblemente migrando la lectura de datasets desde `pandas` hacia `DuckDB` para consultas mas eficientes.

## Hacia donde va

El proximo objetivo es tener una operacion confiable y recurrente: datos de transporte actualizados, auditables y listos para consulta. Sobre esa base, TransData puede evolucionar en dos direcciones:

1. Inteligencia de licitaciones: busqueda, seguimiento, analisis de compradores, estados y adjudicaciones.
2. Inteligencia empresarial: empresas proveedoras, adjudicatarios, relacion con organismos, actividad comercial e indicadores BI.

El criterio para avanzar sigue siendo simple: cada nueva pieza debe fortalecer el activo central de datos, reducir riesgo operativo o hacer mas util la futura aplicacion sin crear complejidad innecesaria.

## Documentos relacionados

- [Estado operativo actual](./CURRENT_STATUS.md)
- [Roadmap vivo](./ROADMAP.md)
- [Directrices del proyecto](./PROJECT_GUIDELINES.md)
- [Operacion del pipeline](./OPERATIONS.md)
- [Contrato de datos de la aplicacion](./APP_DATA_CONTRACT.md)
- [Contrato de API](./APP_API_CONTRACT.md)
