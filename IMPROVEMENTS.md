# Mejoras propuestas para la calculadora de fertirriego

Este documento resume oportunidades de mejora priorizadas para hacer la calculadora más
robusta, clara y útil para usuarios técnicos y de campo.

## 1) Claridad en resultados (UI y reportes)
- **Tabla de aportes por fertilizante**: mostrar una breve leyenda con unidades y
  la definición de “aporte por etapa” vs “aporte por ciclo completo”.
- **Resumen ejecutivo**: incluir un bloque compacto con metas de cultivo, etapa
  actual, y déficits críticos (macros y micros).
- **Estandarizar unidades**: mostrar coherentemente kg/ha por etapa y por aplicación,
  evitando ambigüedades al exportar a PDF/Excel.

## 2) Consistencia front/back
- **Contratos de respuesta**: documentar y validar (con schemas) los campos
  clave para resultados, PDF y Excel (fertilizer_program, micronutrients,
  contributions, etc.).
- **Mapeo de datos**: crear utilidades únicas de normalización que eviten diferencias
  entre la UI, el PDF y el Excel.

## 3) Validaciones agronómicas adicionales
- **Alertas de rangos**: alertar si el pH o HCO₃ están fuera de rango y se espera
  un ajuste (ácido, quelatos, etc.).
- **Chequeo de compatibilidad**: resaltar incompatibilidades entre fertilizantes,
  no solo bloquear la receta.

## 4) Mejoras de experiencia de usuario
- **Indicador de progreso** por etapa y resumen de inputs clave.
- **Explicaciones contextuales** (tooltips) para déficits, eficiencias y aportes.
- **Historial de cálculos** con notas rápidas del usuario.

## 5) Calidad y testing
- **Matriz de escenarios**: definir 50–100 escenarios base con datos de suelo/agua,
  cultivos y etapas representativas.
- **Pruebas E2E**: automatizar al menos los casos críticos (flujo completo hasta PDF).
- **Pruebas de regresión**: validar consistencia numérica entre UI, PDF y Excel.

## 6) Performance y resiliencia
- **Caching** de catálogos y curvas.
- **Manejo de errores**: mensajes específicos cuando un endpoint falla, con
  acciones sugeridas para el usuario.
