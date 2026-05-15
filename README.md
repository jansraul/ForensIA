# 🤖 FORENSIA

### Agente Inteligente de Auditoría Forense para Detección de Fraude en Transacciones

> Proyecto Integrador - Módulo 2 | Especialización en IA Generativa  
> **Autor:** Jans López — Auditor Interno | Auditor Forense | Gestor de Riesgos  
> **Fecha de entrega:** 18/05/2025

---

## 📋 Tabla de Contenido

1. [Problema de Negocio](#-problema-de-negocio)
2. [Análisis Previo](#-análisis-previo)
3. [Arquitectura de Solución](#-arquitectura-de-solución)
4. [Componentes del Sistema](#-componentes-del-sistema)
5. [Herramientas del Agente](#-herramientas-del-agente)
6. [Controles Implementados](#-controles-implementados)
7. [Tecnologías Utilizadas](#-tecnologías-utilizadas)
8. [Instalación y Ejecución](#-instalación-y-ejecución)
9. [Demo y Uso](#-demo-y-uso)
10. [Limitaciones](#-limitaciones)
11. [Mejoras Futuras](#-mejoras-futuras)
12. [Reflexión Técnica](#-reflexión-técnica)

---

## 🔍 Problema de Negocio

### Contexto

**Industria Nacional SAC** es una empresa mediana peruana del sector industrial con más de 500 empleados, 60 proveedores activos y un volumen de 8,000+ transacciones anuales que superan los S/. 67 millones en gasto operativo.

### El dolor

El equipo de auditoría interna está conformado por solo 3 personas que realizan las revisiones de transacciones de forma **manual en hojas de Excel**. El proceso actual presenta los siguientes problemas críticos:

- **Tiempo excesivo:** Una auditoría forense de transacciones toma entre 3 a 4 semanas de revisión línea por línea.
- **Volumen inmanejable:** Con 8,000+ transacciones anuales, es humanamente imposible revisar cada una con el mismo nivel de detalle.
- **Detección tardía:** Según la **ACFE (Association of Certified Fraud Examiners)** en su informe *Occupational Fraud 2024*, la mediana de duración de un esquema de fraude antes de ser detectado es de **12 meses**.
- **Pérdida económica:** La ACFE estima que una empresa típica pierde el **5% de sus ingresos anuales por fraude**. Para Industria Nacional SAC, esto representaría aproximadamente **S/. 3.3 millones anuales**.
- **Fatiga del auditor:** El 70% del tiempo del auditor se consume en tareas repetitivas de extracción y comparación de datos, dejando poco espacio para el análisis crítico y la investigación profunda.

### ¿Por qué IA Generativa?

Una solución con IA Generativa aporta valor porque:

- **Reduce el tiempo de análisis** de semanas a minutos.
- **Detecta patrones ocultos** que el ojo humano no puede ver en miles de registros (fraccionamiento, proveedores fantasma, anomalías estadísticas).
- **Permite interacción natural:** El auditor conversa con el agente en lenguaje natural, sin necesidad de programar consultas SQL ni fórmulas complejas.
- **Interacción por voz:** El auditor puede hablar directamente con el agente usando comandos de voz, y FORENSIA responde en voz alta en español.
- **Mantiene memoria:** El agente recuerda hallazgos previos en la sesión, con opción de memoria persistente en PostgreSQL para auditorías entre sesiones.
- **Democratiza el análisis forense:** Auditores sin conocimientos de programación pueden ejecutar análisis avanzados como la Ley de Benford.

### Resultado esperado

El auditor puede cargar un dataset de transacciones y en **minutos** obtener:
- Identificación de transacciones duplicadas y pagos dobles.
- Detección de proveedores fantasma.
- Alertas de fraccionamiento de compras.
- Análisis de transacciones fuera de horario.
- Detección de sobrefacturación y outliers.
- Análisis estadístico forense (Ley de Benford).
- Reporte ejecutivo consolidado con hallazgos y recomendaciones.

---

## 📊 Análisis Previo

### Usuario Objetivo

Auditor interno o auditor forense que necesita analizar un volumen alto de transacciones para identificar irregularidades, fraudes o incumplimientos de controles internos.

### Entradas del sistema

| Entrada | Descripción |
|---------|-------------|
| CSV de transacciones | Archivo con registros de pagos a proveedores (fecha, monto, proveedor, autorizador, etc.) |
| Consultas en lenguaje natural | Preguntas del auditor al agente ("busca duplicados", "analiza al proveedor X") |
| Comandos de voz | El auditor puede hablar en español usando el micrófono del navegador |
| Parámetros opcionales | Umbrales, rangos de fecha, nombres de proveedores o empleados específicos |

### Decisiones que debe tomar el agente

- **¿Qué herramienta usar?** Según la pregunta del auditor, el agente decide dinámicamente si buscar duplicados, analizar proveedores, revisar horarios, etc.
- **¿Cuántas herramientas invocar?** Si la consulta requiere análisis cruzado, el agente puede usar múltiples herramientas en secuencia.
- **¿Cómo presentar los hallazgos?** El agente estructura la respuesta con niveles de severidad (🔴 ALTA, 🟡 MEDIA, 🟢 BAJA) y recomendaciones accionables.

### Tareas automatizables

- Detección de facturas duplicadas.
- Identificación de patrones de fraccionamiento.
- Análisis de distribución de Benford.
- Cruce de proveedores contra patrones sospechosos.
- Generación de reportes consolidados.

### Partes predecibles vs. dinámicas

| Predecible | Dinámica |
|-----------|----------|
| Carga y validación del CSV | Qué herramienta usar según la pregunta |
| Cálculos estadísticos (Benford, outliers) | Orden de ejecución de herramientas |
| Formato del reporte | Interpretación de resultados |
| Estructura de los gráficos | Recomendaciones contextuales |

### Riesgos y límites

- El agente trabaja con datos sintéticos en esta versión demo.
- No reemplaza el juicio profesional del auditor; es un asistente.
- Depende de la calidad y completitud de los datos de entrada.
- Los umbrales de detección pueden requerir calibración según la empresa.

**Este análisis justifica la arquitectura basada en agente:** el auditor hace preguntas variadas e impredecibles, y el sistema debe decidir dinámicamente qué análisis ejecutar. Un workflow fijo no cubriría esta necesidad.

---

## 🏗️ Arquitectura de Solución

### Tipo: Arquitectura basada en Agente

Se eligió una **arquitectura basada en agente** porque:

1. **Las consultas son dinámicas:** El auditor puede preguntar cualquier cosa en cualquier orden ("busca duplicados", "ahora analiza al proveedor X", "genera el reporte").
2. **El agente decide qué herramientas usar:** No hay un flujo fijo. El agente razona (ReAct) y selecciona la herramienta adecuada según la consulta.
3. **Se requiere memoria:** El agente necesita recordar hallazgos previos para dar respuestas contextuales.
4. **No aplica workflow:** Un workflow sería adecuado si los pasos fueran siempre los mismos, pero aquí el auditor puede necesitar solo un análisis específico o una investigación completa.
5. **No aplica híbrida:** No hay una parte del proceso que sea siempre predecible y otra siempre dinámica. Todo depende de lo que pregunte el auditor.

### Principio de Mínima Complejidad

Se aplicó el principio de mínima complejidad de la siguiente manera:

- **Se usa un solo agente**, no múltiples agentes coordinados.
- **No se usa dispatcher** porque no hay necesidad de clasificar y derivar a diferentes sub-sistemas.
- **No se usa workflow** porque el flujo no es lineal ni predecible.
- **No se usa RAG** porque los datos se analizan directamente con Pandas, no requieren búsqueda semántica.
- **No se usa base de datos vectorial** porque las transacciones son tabulares, no documentos de texto.
- **Memoria dual:** Sesión por defecto (lista de mensajes) para simplicidad; PostgreSQL opcional para auditorías que requieren persistencia entre sesiones.

### Flujo de la Solución

```
Usuario (Auditor) — Texto o Voz
    │
    ▼
Interfaz Streamlit (app.py) — Web Speech API (STT/TTS)
    │
    ▼
Agente ReAct con create_agent (agent.py)
    │
    ├── Razona sobre la consulta
    ├── Selecciona herramienta(s) apropiada(s)
    ├── Ejecuta herramienta(s) (tools.py)
    ├── Interpreta resultados
    ├── Consulta memoria (sesión o PostgreSQL)
    │
    ▼
Respuesta al Auditor — Texto + Voz + Visualizaciones
```

---

## 🧩 Componentes del Sistema

### Agente (agent.py)

El componente central. Implementado con `create_agent` de LangChain, utiliza el patrón **ReAct** (Reasoning + Acting): primero razona sobre qué necesita el auditor, luego actúa invocando las herramientas apropiadas, y finalmente genera una respuesta interpretativa. Soporta memoria dual: sesión (temporal) o PostgreSQL (persistente).

### Herramientas (tools.py)

10 funciones decoradas con `@tool` que realizan análisis forenses específicos. El agente las invoca dinámicamente según la consulta. Cada herramienta recibe parámetros opcionales y retorna resultados estructurados en JSON.

### Orquestador (config.py)

El system prompt actúa como orquestador del comportamiento del agente. Define sus reglas de decisión, formato de respuesta, control de dominio y personalidad profesional.

### Interfaz con Voz (app.py)

La interfaz Streamlit incluye integración de voz mediante Web Speech API del navegador:
- **Speech-to-Text (STT):** El auditor habla al micrófono y el texto se envía al agente automáticamente.
- **Text-to-Speech (TTS):** FORENSIA lee sus respuestas en voz alta en español, con opción de activar/desactivar.

### Memoria Dual (agent.py)

- **Modo sesión (por defecto):** Historial en lista Python. Sin configuración extra.
- **Modo PostgreSQL (opcional):** Memoria persistente con `PostgresSaver` de LangGraph. Requiere `DATABASE_URL` en `.env`. Se detecta automáticamente; si no hay conexión, usa modo sesión.

### ¿Por qué no se usó Dispatcher?

No se implementó un dispatcher porque toda la interacción es atendida por un solo agente. No hay necesidad de clasificar la entrada y derivarla a diferentes sistemas. El agente ReAct ya tiene la capacidad de decidir internamente qué herramienta usar.

### ¿Por qué no se usó Workflow?

No se implementó un workflow porque las consultas del auditor no siguen un orden predecible. Un auditor puede empezar por duplicados, luego saltar a Benford, luego investigar un proveedor específico. Un workflow forzaría un flujo lineal que no refleja cómo trabaja un auditor en la práctica.

---

## 🔧 Herramientas del Agente

| # | Herramienta | Función | Cuándo la usa el agente |
|---|------------|---------|------------------------|
| 1 | `resumen_general` | Visión ejecutiva del dataset | "Dame un resumen", "¿Cuántas transacciones hay?" |
| 2 | `detectar_duplicados` | Facturas duplicadas y pagos dobles | "Busca duplicados", "¿Hay pagos dobles?" |
| 3 | `detectar_fuera_de_horario` | Transacciones en horarios inusuales | "Transacciones en madrugada", "Actividad en fin de semana" |
| 4 | `analizar_proveedores` | Proveedores fantasma y scoring de sospecha | "Proveedores sospechosos", "Investiga al proveedor X" |
| 5 | `detectar_fraccionamiento` | Compras divididas para evadir controles | "¿Hay fraccionamiento?", "Compras divididas" |
| 6 | `detectar_montos_atipicos` | Outliers y sobrefacturación | "Montos inusuales", "Sobrefacturación" |
| 7 | `analizar_autorizadores` | Conflictos de interés y auto-aprobación | "Revisa autorizadores", "¿Hay auto-aprobación?" |
| 8 | `analisis_benford` | Ley de Benford para manipulación de cifras | "Aplica Benford", "Análisis estadístico" |
| 9 | `analizar_notas_credito` | Notas de crédito sin soporte | "Revisa notas de crédito", "Devoluciones sospechosas" |
| 10 | `generar_reporte_ejecutivo` | Reporte consolidado con recomendaciones | "Genera reporte", "Dame el informe final" |

---

## 🛡️ Controles Implementados

| Control | Implementación |
|---------|---------------|
| Validación de entrada | Verifica que la consulta no esté vacía antes de procesar |
| Verificación de datos cargados | Si no hay dataset cargado, informa al usuario antes de ejecutar |
| Manejo de errores en herramientas | Cada herramienta tiene try/catch y retorna mensajes claros si falla |
| Control de dominio | El system prompt instruye al agente a rechazar temas fuera de auditoría |
| Respuesta por falta de información | Si una herramienta no encuentra resultados, lo comunica claramente |
| Mensaje de fallback | Si el agente no puede resolver, sugiere alternativas o reformulación |
| Límite de resultados | Las herramientas limitan el output para no saturar al LLM |

---

## 💻 Tecnologías Utilizadas

| Componente | Tecnología |
|-----------|-----------|
| Modelo LLM | OpenAI GPT-4o |
| Framework de agente | LangChain (`create_agent`) |
| Lenguaje | Python 3.10+ |
| Interfaz | Streamlit |
| Voz | Web Speech API (STT + TTS) |
| Visualizaciones | Plotly |
| Datos | Pandas / NumPy |
| Memoria persistente | PostgreSQL en Cloud SQL (opcional) |
| Checkpointer | LangGraph `PostgresSaver` (opcional) |
| Infraestructura | Google Cloud (Cloud Run + Cloud SQL) |
| Dataset | Sintético (8,991 transacciones con 10 tipos de fraude) |

---

## 🚀 Instalación y Ejecución

### Requisitos previos

- Python 3.10 o superior
- API Key de OpenAI (con acceso a GPT-4o)
- Google Chrome (recomendado, para funciones de voz)

### Paso 1: Clonar el repositorio

```bash
git clone https://github.com/janslopez/forensia.git
cd forensia
```

### Paso 2: Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
```

### Paso 3: Instalar dependencias

```bash
pip install -r requirements.txt
```

Para memoria persistente con PostgreSQL (opcional):
```bash
pip install langgraph-checkpoint-postgres "psycopg[binary,pool]==3.2.6"
```

### Paso 4: Configurar variables de entorno

```bash
cp env.example .env
```

Edita el archivo `.env`:

```
OPENAI_API_KEY=sk-tu-api-key-aqui
DATABASE_URL=postgresql://usuario:password@host:5432/basededatos  # Opcional
```

### Paso 5: Ejecutar la aplicación

```bash
streamlit run "app (1).py"
```

Se abrirá automáticamente en tu navegador en `http://localhost:8501`.

---

## 🎬 Demo y Uso

### Inicio

1. Abre la aplicación en el navegador (Chrome recomendado).
2. Ingresa tu API Key de OpenAI en el panel lateral.
3. Marca "Usar datos de demostración" y presiona **"Iniciar FORENSIA"**.

### Interacción por texto

```
Auditor: "Dame un resumen general del dataset"
FORENSIA: [Usa herramienta resumen_general] → Muestra KPIs principales

Auditor: "Busca transacciones duplicadas"
FORENSIA: [Usa herramienta detectar_duplicados] → Identifica 50 alertas, S/. 381,185 en riesgo

Auditor: "Analiza proveedores sospechosos"
FORENSIA: [Usa herramienta analizar_proveedores] → Detecta 10 proveedores con patrones inusuales

Auditor: "Genera un reporte ejecutivo completo"
FORENSIA: [Usa herramienta generar_reporte_ejecutivo] → Consolida todos los hallazgos
```

### Interacción por voz

1. Presiona el botón **🎤 micrófono** (se pone rojo).
2. Habla en español: "Busca transacciones duplicadas".
3. FORENSIA transcribe tu voz y envía la consulta automáticamente.
4. Si el toggle **🔊 Respuestas con voz** está activo, FORENSIA lee su respuesta en voz alta.

### Dashboard

La pestaña **"Panel Analítico"** muestra visualizaciones interactivas con Plotly:
- KPIs principales
- Timeline de transacciones por mes
- Heatmap de actividad por hora y día
- Análisis de Benford
- Top proveedores por monto
- Distribución por método de pago
- Treemap de gasto por departamento
- Scatter de outliers
- Concentración por autorizador

---

## ⚠️ Limitaciones

1. **Datos sintéticos:** El dataset es generado, no proviene de una empresa real.
2. **No reemplaza al auditor:** FORENSIA es un asistente, no un sustituto del juicio profesional.
3. **Voz requiere Chrome:** El reconocimiento de voz funciona mejor en Google Chrome.
4. **Sin integración directa a ERPs:** No se conecta directamente a SAP, Oracle u otros sistemas empresariales.
5. **Umbrales estáticos:** Los umbrales de detección están predefinidos y pueden requerir ajuste por empresa.
6. **Dependencia de API:** Requiere conexión a internet y una API Key de OpenAI válida.

---

## 🚀 Mejoras Futuras

1. **Integración con ERPs:** Conexión directa a SAP vía RFC (`pyrfc`) o APIs OData en S/4HANA para obtener datos en tiempo real.
2. **RAG con normativa:** Incorporar búsqueda semántica sobre normas de auditoría (NIA, SOX, COSO) para que el agente cite la normativa aplicable.
3. **Alertas automáticas:** Sistema de monitoreo continuo que ejecute análisis periódicos y envíe alertas por correo.
4. **Multi-empresa:** Soporte para analizar múltiples empresas con diferentes configuraciones.
5. **LangSmith:** Integración de trazabilidad para monitorear el comportamiento del agente en producción.
6. **Deploy completo en la nube:** Despliegue productivo en Cloud Run con escalamiento automático.

---

## 💭 Reflexión Técnica

Este proyecto me permitió comprender la diferencia práctica entre un **agente**, un **workflow** y una **arquitectura híbrida**. La clave estuvo en analizar cómo trabaja realmente un auditor: no sigue un flujo fijo, sino que navega entre diferentes análisis según lo que va encontrando. Eso hizo que la arquitectura basada en agente fuera la elección natural.

El principio de **mínima complejidad** fue fundamental. Inicialmente consideré agregar un dispatcher para clasificar las consultas, pero al reflexionar, el agente ReAct ya tiene esa capacidad incorporada. Agregar un dispatcher habría sido complejidad innecesaria sin valor real.

La implementación de la **memoria conversacional dual** demostró su valor: la memoria en sesión permite análisis progresivo durante una auditoría, mientras que la memoria persistente con PostgreSQL permite retomar investigaciones entre sesiones, algo crítico en auditorías reales que pueden durar días.

La integración de **voz** fue un diferenciador importante: permite al auditor interactuar con FORENSIA de forma natural durante la exposición de hallazgos al comité de auditoría, sin necesidad de estar escribiendo consultas.

Como auditor forense con más de 15 años de experiencia, puedo afirmar que herramientas como FORENSIA tienen el potencial de transformar la práctica de auditoría, no eliminando al auditor, sino potenciando su capacidad analítica y permitiéndole enfocarse en lo que realmente importa: el juicio profesional y la investigación de hallazgos críticos.

---

## 📁 Estructura del Proyecto

```
forensia/
├── data/
│   ├── transacciones_empresa_2024.csv    # Dataset para demo
│   ├── catalogo_proveedores.csv          # Catálogo de proveedores
│   └── catalogo_empleados.csv            # Catálogo de empleados
├── app (1).py                            # Interfaz Streamlit + Voz
├── agent.py                              # Agente ReAct con memoria dual
├── tools.py                              # 10 herramientas de detección
├── config.py                             # Configuración y system prompt
├── visualizations.py                     # Gráficos con Plotly
├── generate_dataset.py                   # Generador de datos sintéticos
├── requirements.txt                      # Dependencias
├── env.example                           # Template de variables de entorno
└── README.md                             # Este archivo
```

---

## 📄 Licencia

Proyecto académico desarrollado para la Especialización en IA Generativa — Módulo 2.

---

*Desarrollado con 🤖 por Jans López — Auditor Interno | Auditor Forense | Gestor de Riesgos*
