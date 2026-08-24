# Transport Rule Review

Generado: `2026-05-08T00:22:54.450610`

## Resumen

- Archivo audit removido: `C:\Users\User\OneDrive\Desktop\TransData-main\data\processed\transport\audit\transport_rule_audit_removed_20260508_002013.csv`
- Filas removidas analizadas: `2066`
- Bucket dominante: `generic_ambiguous`

## Lectura rápida

- La mayor parte del ruido removido proviene de casos genéricos `servicio_transporte` sin contexto suficiente de pasajeros terrestres.
- Las exclusiones por marítimo, aéreo, ambulancia, logística y transporte de vehículos parecen bien encaminadas.
- Los casos mixtos `pasajeros y carga` aparecen pocos, pero son consistentes y conviene mantenerlos fuera salvo decisión de negocio contraria.

## generic_ambiguous

- Filas: `1790`
- Positive hits top: `{'servicio_transporte': 1715, 'servicio_transporte,traslado': 57, 'acercamiento,servicio_transporte': 16, 'acercamiento,traslado': 2}`
- Exclusion hits top: `{'': 1790}`
- Negative hits top: `{'': 1790}`

Muestra:

- `1214102-27-LP26` | rejected | SERVICIO DE TRANSPORTE PARA CENTROS DE SALUD
- `1347870-1-LE26` | rejected | SERVICIO DE TRANSPORTE MEMO 57 SDM RES.149
- `1501468-12-LP26` | rejected | SERVICIO DE TRANSPORTE SLEP DEL ACONCAGUA
- `1723-23-LE26` | rejected | Servicio de Transporte  de la DIDECO
- `1953-12-LE26` | rejected | 502 CONTRATACION SERVICIO DE TRANSPORTE CCJJ 26-27
- `218-17-LE26` | rejected | SERVICIO DE TRANSPORTE PRLAC M. DE SAN JOAQUÍN
- `2381-15-LE26` | rejected | SERVICIO DE TRANSPORTE PARA TRASLADO DE PROFESIONALES DEL CONVENIO REFORZAMIENTO DE LA ATENCION INTEGRAL DE NIÑOS Y NIÑAS ADOLESCENTES Y JOVENES VINCULADOS A LA RED SPE Y SRJS
- `2381-18-LE26` | rejected | SERVICIO DE TRANSPORTE PARA TRASLADO DE PROFESIONALES DEL CONVENIO CUIDADOS PALIATIVOS UNIVERSALES 2026

## exclusion_context

- Filas: `243`
- Positive hits top: `{'servicio_transporte': 206, 'servicio_transporte,traslado': 32, 'traslado,van': 3, 'servicio_transporte,van': 1, 'bus,minibus,van': 1}`
- Exclusion hits top: `{'excl_equipos': 55, 'excl_aereo': 43, 'excl_insumos': 29, 'excl_maritimo': 29, 'excl_equipos,excl_maquinaria': 15, 'excl_transporte_vehiculos': 11, 'excl_materiales': 11, 'excl_equipos,excl_materiales': 8, 'excl_ambulancia': 7, 'excl_distribucion': 5}`
- Negative hits top: `{'': 243}`

Muestra:

- `1027-4-LP26` | rejected_exclusion_context | Servicio de Transporte de Maquinaria y Equipos de la Administración Directa Oficina Provincial de Huasco Vialidad – Región de Atacama.
- `1337-10-LE26` | rejected_exclusion_context | Convenio del Servicio de transporte aéreo para funcionariosas de la Dirección de Vialidad Palena y traslado de documentación entre Chaitén – Puerto Montt – Chaitén
- `2328-24-LE26` | rejected_exclusion_context | LICITACIÓN PÚBLICA E-12026 “SERVICIO DE TRANSPORTE MARITIMO PARA ESTUDIANTES SECTOR ISLA TENGLO” 
- `2332-14-LE26` | rejected_exclusion_context | SERVICIO DE TRANSPORTE MARITIMO Y TERRESTRE ESR26
- `3526-12-LP26` | rejected_exclusion_context | SERVICIO DE TRANSPORTE AÉREO
- `1057417-43-I226` | rejected_exclusion_context | CONVENIO POR SERVICIO DE TRANSPORTE DE PACIENTES EN AMBULANCIA
- `1214102-9-LE26` | rejected_exclusion_context | SERVICIO DE TRANSPORTE PARA CENTROS DE SALUD
- `1214103-1-LE26` | rejected_exclusion_context | SERVICIO DE TRANSPORTE DE LA CORPORACIÓN CULTURAL

## mixed_passenger_cargo

- Filas: `21`
- Positive hits top: `{'servicio_transporte,transporte_pasajeros': 14, 'transporte_pasajeros': 3, 'servicio_transporte': 2, 'traslado,traslado_pasajeros': 2}`
- Exclusion hits top: `{'': 19, 'excl_maritimo': 2}`
- Negative hits top: `{'carga,pasajeros_y_carga': 19, 'carga,carga_y_pasajeros,transporte_carga': 2}`

Muestra:

- `3894-1-B226` | rejected_mixed_passenger_cargo | SERVICIO DE TRANSPORTE DE PASAJEROS Y CARGA DE CAMIONETAS PARA USO INTERNO DE LA MUNICIPALIDAD DE LAMPA LÍNEAS N° 3 4 5 Y 10
- `1080089-67-LE25` | rejected_mixed_passenger_cargo | Servicio de transporte marítimo regional
- `2983-6-LE25` | rejected_mixed_passenger_cargo | SERVICIO TRANSPORTE DE PASAJEROS Y CARGA
- `1224957-37-LQ25` | rejected_mixed_passenger_cargo | TRANSPORTE DE PASAJEROS Y CARGA MENOR
- `3894-35-LQ25` | rejected_mixed_passenger_cargo | SERVICIO DE TRANSPORTE DE PASAJEROS Y CARGA EN CAMIONETAS PARA USO INTERNO DE LA MUNICIPALIDAD DE LAMPA 2DO LLAMADO.
- `3894-43-LQ25` | rejected_mixed_passenger_cargo | SERVICIO DE TRANSPORTE DE PASAJEROS Y CARGA DE CAMIONETAS PARA USO INTERNO DE LA MUNICIPALIDAD DE LAMPA 2DO LLAMADO LÍNEAS N° 5 Y10.
- `3894-7-LQ25` | rejected_mixed_passenger_cargo | SERVICIO DE TRANSPORTE DE PASAJEROS Y CARGA EN CAMIONETAS PARA USO INTERNO DE LA MUNICIPALIDAD DE LAMPA
- `2342-94-LQ24` | rejected_mixed_passenger_cargo | SERVICIO DE TRANSPORTE DE PASAJEROS Y CARGA EN CAMIONETAS PARA USO INTERNO DE LA I. MUNICIAPLIDAD DE SAN BERNARDO

## mixed_cargo

- Filas: `10`
- Positive hits top: `{'servicio_transporte,traslado': 4, 'servicio_transporte': 3, 'bus,servicio_transporte': 1, 'servicio_transporte,traslado,van': 1, 'bus,traslado': 1}`
- Exclusion hits top: `{'': 3, 'excl_distribucion,excl_logistica': 3, 'excl_maritimo': 1, 'excl_equipos,excl_insumos': 1, 'excl_insumos,excl_materiales': 1, 'excl_transporte_vehiculos,excl_traslado_vehiculos': 1}`
- Negative hits top: `{'carga': 6, 'carga,transporte_carga': 3, 'carga,grua': 1}`

Muestra:

- `1006-8-LE26` | rejected_mixed_cargo | SERVICIO DE TRANSPORTE EN BUSES INTERPROVINCIALES
- `1092-17-LE25` | rejected_mixed_cargo | Servicio de Transporte de productos forestales
- `1173639-3-LE24` | rejected_mixed_cargo | SERVICIO DE TRANSPORTE RUTA CALLE DPP DE TALAGANTE
- `1033-24-L123` | rejected_mixed_cargo | “SERVICIO DE TRANSPORTE DE MATERIALES E INSUMOS DE VIVERO, PROGRAMA SIEMBRA POR CHILE CONAF ANTOFAGASTA”
- `1216062-7-LR23` | rejected_mixed_cargo | Contratación de servicio de transporte
- `1171166-4-LP23` | rejected_mixed_cargo | SERVICIO DE TRANSPORTE Y DISTRIBUCIÓN LOGISTICA
- `4629-8-LE23` | rejected_mixed_cargo | Servicio de transporte de vehículos DT
- `1006-3-LE23` | rejected_mixed_cargo | SERVICIO DE TRASLADO EN BUS

## negative_score

- Filas: `2`
- Positive hits top: `{'servicio_transporte': 2}`
- Exclusion hits top: `{'': 2}`
- Negative hits top: `{'camion': 1, 'camion,camion_aljibe': 1}`

Muestra:

- `1027-18-LP24` | rejected_negative_score | Servicio de Transporte de Material Granular Huasco
- `1116330-1-LE21` | rejected_negative_score | SERVICIO DE TRANSPORTE DE AGUA POTABLE 2022

## Recomendación

1. Revisar primero el bucket `generic_ambiguous`, porque ahí está casi todo el volumen removido.
2. Mantener por ahora las exclusiones de marítimo, aéreo, logística y transporte de vehículos.
3. Si queremos recuperar parte del universo, hacerlo creando contexto positivo adicional para programas sociales, salud y educación, no relajando exclusiones duras.
