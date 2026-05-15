# RUTINATOR — Documentación Técnica

> Bot de Telegram para generación de programas de entrenamiento y nutrición personalizados, basado en evidencia científica y principios de periodización deportiva real.

---

## Índice

1. [Arquitectura general](#arquitectura-general)
2. [Instalación y configuración](#instalación-y-configuración)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [bot_telegram.py](#bot_telegrampy)
   - [Estados FSM](#estados-fsm-onboardingstates)
   - [Flujo de conversación](#flujo-de-conversación-5-pasos)
   - [Handlers](#handlers)
   - [Helpers](#helpers)
5. [logic_processor.py](#logic_processorpy)
   - [Carga del DataFrame](#carga-del-dataframe)
   - [Funciones de cálculo](#funciones-de-cálculo)
   - [construir_programa()](#construir_programa)
   - [Las 8 tablas de datos](#las-8-tablas-de-datos)
   - [Motor de periodización](#motor-de-periodización)
   - [Gráficos](#gráficos-matplotlib)
   - [Generadores PDF](#generadores-pdf)
6. [Base de datos de ejercicios](#base-de-datos-de-ejercicios-ejercicioscsvs)
7. [Dependencias](#dependencias)
8. [Variables de entorno](#variables-de-entorno)
9. [Principios del coach](#principios-del-coach)
10. [Progresión de carga](#progresión-de-carga)

---

## Arquitectura general

```
Usuario (Telegram)
       │
       ▼
  bot_telegram.py              ← Capa de interfaz (FSM + handlers)
       │
       ▼
  logic_processor.py           ← Capa de lógica y generación
       │
       ├── DF_EJERCICIOS            ← DataFrame Pandas (cargado al importar)
       │       └── ejercicios.csv  ← 48 ejercicios con 9 columnas
       │
       ├── construir_programa()    → 8 tablas de datos estructurados
       │       └── _construir_entrenamiento()  ← Motor de periodización
       │               ├── _filtrar_df()       ← Filtros Pandas por lesión/equipo
       │               ├── _seleccionar_ejercicios()  ← Selección por patrón
       │               └── _aplicar_periodizacion()   ← Reglas RIR/series/deload
       │
       ├── generar_pdf_rutina()    → PDF 1: Plan de entrenamiento (12 semanas)
       └── generar_revista_nutricional() → PDF 2: Guía nutricional
```

El bot usa **aiogram 3.x** con arquitectura asíncrona. La conversación se gestiona mediante una **Máquina de Estados Finitos (FSM)**. Al finalizar, `logic_processor.py` construye el programa completo leyendo `ejercicios.csv` con Pandas, aplica las reglas de periodización y genera dos PDFs en memoria (`BytesIO`) sin escribir archivos en disco.

---

## Instalación y configuración

```bash
# 1. Clonar el repositorio
git clone <repo>
cd RUTINATOR-MVP

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar el token
# Editar .env y reemplazar con tu token de @BotFather
TELEGRAM_BOT_TOKEN=tu_token_aqui

# 4. Ejecutar
python src/bot_telegram.py
```

---

## Estructura del proyecto

```
RUTINATOR-MVP/
├── .env                    # Token de Telegram (no commitear)
├── .env.example            # Plantilla de variables de entorno
├── .gitignore
├── requirements.txt
├── DOCS.md                 # Este archivo
├── data/
│   └── ejercicios.csv      # Base de datos de ejercicios (48 filas, 9 columnas)
└── src/
    ├── bot_telegram.py     # Bot, FSM y handlers
    └── logic_processor.py  # Motor de periodización y generación de PDFs
```

---

## bot_telegram.py

Punto de entrada del bot. Gestiona toda la interacción con el usuario vía Telegram.

### Estados FSM (`OnboardingStates`)

La clase `OnboardingStates(StatesGroup)` define 16 estados que representan cada punto de la conversación:

| Estado | Paso | Descripción |
|---|---|---|
| `esperando_objetivo` | 1 | Selección de objetivo principal |
| `esperando_nivel` | 1 | Nivel de experiencia en el gym |
| `esperando_edad` | 2 | Edad del usuario (texto libre, validado 10–100) |
| `esperando_sexo` | 2 | Sexo biológico (botones inline) |
| `esperando_peso` | 2 | Peso en kg (texto libre, validado 30–300) |
| `esperando_talla` | 2 | Talla en cm (texto libre, validado 100–250) |
| `esperando_equipo` | 3 | Tipo de equipamiento disponible |
| `esperando_dias` | 3 | Días de entrenamiento por semana (2–5) |
| `esperando_enfermedades` | 4 | ¿Tiene enfermedades crónicas? (Sí/No) |
| `esperando_detalle_enfermedades` | 4 | Descripción de la condición (si aplica) |
| `esperando_lesiones` | 4 | ¿Tiene lesiones activas? (Sí/No) |
| `esperando_detalle_lesiones` | 4 | Descripción de la lesión (si aplica) |
| `esperando_embarazo` | 4 | ¿Está embarazada? (solo mujeres) |
| `esperando_deporte_paralelo` | 4 | Deporte o actividad adicional |
| `esperando_preferencias` | 5 | Ejercicios que no quiere hacer |
| `esperando_resultados_test` | 5 | Resultados del test de condición física |

### Flujo de conversación (5 pasos)

```
/start
  │
  ├─ Paso 1: Objetivo (quemar grasa / ganar músculo / recomposición)
  │          Nivel (principiante / intermedio / avanzado)
  │
  ├─ Paso 2: Edad → Sexo → Peso → Talla
  │
  ├─ Paso 3: Equipamiento → Días/semana
  │
  ├─ Paso 4: Enfermedades → [detalle] → Lesiones → [detalle]
  │          → [Embarazo si es mujer] → Deporte paralelo
  │
  └─ Paso 5: Preferencias → Test de condición física
                                    │
                                    ▼
                          generar_pdf_rutina()
                          generar_revista_nutricional()
                                    │
                                    ▼
                          Envío de 2 PDFs por Telegram
```

### Handlers

| Función | Trigger | Descripción |
|---|---|---|
| `cmd_start` | `/start` | Limpia el estado y arranca el onboarding |
| `process_obj` | `CallbackQuery` en `esperando_objetivo` | Guarda objetivo y nombre del usuario |
| `process_nivel` | `CallbackQuery` en `esperando_nivel` | Guarda nivel de experiencia |
| `process_edad` | `Message` en `esperando_edad` | Valida y guarda edad (10–100) |
| `process_sexo` | `CallbackQuery` en `esperando_sexo` | Guarda sexo biológico |
| `process_peso` | `Message` en `esperando_peso` | Valida y guarda peso (30–300 kg) |
| `process_talla` | `Message` en `esperando_talla` | Valida y guarda talla (100–250 cm) |
| `process_equipo` | `CallbackQuery` en `esperando_equipo` | Guarda tipo de equipamiento |
| `process_dias` | `CallbackQuery` en `esperando_dias` | Guarda días disponibles por semana |
| `process_enf` | `CallbackQuery` en `esperando_enfermedades` | Ramifica según respuesta Sí/No |
| `process_det_enf` | `Message` en `esperando_detalle_enfermedades` | Guarda detalle + disclaimer médico |
| `process_les` | `CallbackQuery` en `esperando_lesiones` | Ramifica según respuesta Sí/No |
| `process_det_les` | `Message` en `esperando_detalle_lesiones` | Guarda detalle de lesión |
| `_siguiente_tras_lesiones` | Helper interno | Decide si preguntar embarazo o ir a deporte |
| `process_emb` | `CallbackQuery` en `esperando_embarazo` | Guarda estado de embarazo + aviso |
| `process_deporte` | `Message` en `esperando_deporte_paralelo` | Guarda deporte adicional |
| `process_preferencias` | `Message` en `esperando_preferencias` | Guarda preferencias y muestra test |
| `process_final` | `Message` en `esperando_resultados_test` | Genera y envía los 2 PDFs |

### Helpers

#### `kb_inline(opciones: list) → InlineKeyboardMarkup`
Crea un teclado inline a partir de una lista de tuplas `(texto, callback_data)`. Cada opción ocupa una fila independiente.

#### `get_yes_no_kb(prefix: str) → InlineKeyboardMarkup`
Genera un teclado de Sí/No con callbacks `{prefix}_si` y `{prefix}_no` en la misma fila.

#### Test adaptativo según perfil

| Condición | Test aplicado |
|---|---|
| Edad ≥ 60 | Senior Fitness Test (silla + flexiones en 30s) |
| Principiante | AMRAP 60s: sentadillas, flexiones, plancha |
| Intermedio | RM estimado en sentadilla y press banca |
| Avanzado | RM real en sentadilla, press banca y peso muerto |

---

## logic_processor.py

Capa de lógica de negocio. Sin dependencias de Telegram. Recibe un `dict` con los datos del usuario y devuelve buffers de PDF listos para enviar.

### Carga del DataFrame

```python
DF_EJERCICIOS: pd.DataFrame = _cargar_df()
```

El DataFrame se carga **una sola vez al importar el módulo** (singleton). La función `_cargar_df()` lee `data/ejercicios.csv`, normaliza los nombres de columnas y convierte `Es_Compuesto` a booleano. Si el archivo no existe, lanza `RuntimeError` con la ruta esperada.

---

### Funciones de cálculo

#### `calcular_imc(peso_kg, altura_cm) → float`
Fórmula: `peso / (altura_m)²`. Retorna 0.0 en caso de error.

#### `estimar_grasa(edad, sexo, imc) → float`
Fórmula de Deurenberg simplificada:
```
%Grasa = (1.20 × IMC) + (0.23 × edad) - (10.8 × sexo_val) - 5.4
```
`sexo_val = 1` masculino, `0` femenino. Resultado acotado entre 5% y 50%.

#### `estimar_agua(grasa) → float`
Estimación: `100 - grasa - 40`.

#### `calcular_macros(objetivo, peso_kg) → dict`

| Objetivo | Proteína | Carbohidratos | Grasas |
|---|---|---|---|
| Quemar Grasa | 2.2g/kg (35%) | 2.0g/kg (40%) | 0.9g/kg (25%) |
| Ganar Músculo | 2.0g/kg (30%) | 3.5g/kg (45%) | 1.0g/kg (25%) |
| Recomposición | 2.1g/kg (33%) | 2.5g/kg (42%) | 1.0g/kg (25%) |

Retorna: `{prot_g, carb_g, gras_g, prot_p, carb_p, gras_p}`

#### `calcular_gasto(nivel, objetivo) → dict`

| Nivel | TMB | NEAT | Ejercicio | TEF |
|---|---|---|---|---|
| Principiante | 65% | 18% | 8% | 9% |
| Intermedio | 60% | 20% | 11% | 9% |
| Avanzado | 55% | 22% | 14% | 9% |

---

### `construir_programa(d: dict) → dict`

Función central. Recibe el dict completo del usuario, llama a todas las funciones de cálculo y al motor de periodización.

**Entrada:** `atleta`, `objetivo`, `nivel`, `sexo`, `edad`, `peso`, `talla`, `lesiones`, `equipamiento`, `dias_semana`, `deporte_paralelo`.

**Salida:** dict con 8 tablas + `_meta` (datos calculados para uso interno en el PDF).

---

### Las 8 tablas de datos

Esquema estricto compatible con exportación a Excel.

| # | Clave | Descripción |
|---|---|---|
| 1 | `atleta` | Título del plan, nombre, objetivo e introducción personalizada |
| 2 | `biometria` | Peso, altura, IMC, % masa muscular, % agua, % grasa visceral |
| 3 | `entrenamiento` | Macrociclo completo: Mes, Semana, Sesión, Ejercicio, Series_Reps, Carga, Objetivo_Tecnico |
| 4 | `nutricion_texto` | Estrategia nutricional en texto según objetivo |
| 5 | `macros` | Distribución de macros en % y colores para gráfico |
| 6 | `neat_texto` | Explicación del NEAT personalizada al objetivo |
| 7 | `neat_estrategias` | Lista de 5 estrategias para aumentar el NEAT diario |
| 8 | `gasto_energetico` | Distribución del gasto energético en % y colores para gráfico |

**Contrato de la Tabla 3 (entrenamiento):**
```json
{
  "Mes": 1,
  "Titulo_Mes": "Adaptación Anatómica",
  "Semana": 1,
  "Semana_Label": "Semana 1",
  "Sesion": "Día 1: Full Body A",
  "Ejercicio": "Sentadilla Libre",
  "Series_Reps": "3 x 12-15",
  "Carga": "RIR 4",
  "Objetivo_Tecnico": "Pecho arriba rodillas sobre pies pausa 1s abajo"
}
```

---

## Motor de periodización

El motor implementa una estructura de **Macrociclo → Mesociclo → Microciclo** completa.

### Constantes de configuración

#### `_SPLITS` — Distribución semanal por días disponibles

| Días | Sesiones del microciclo |
|---|---|
| 2 | Full Body A, Full Body B |
| 3 | Full Body A, Full Body B, Full Body C |
| 4 | Torso, Pierna, Torso, Pierna |
| 5 | Empuje, Tracción, Pierna, Torso, Pierna |

#### `_PATRONES_SESION` — Patrones de movimiento por tipo de sesión

| Sesión | Patrones cubiertos |
|---|---|
| Full Body A | Sentadilla, Empuje_Horizontal, Tracción_Horizontal, Core, Unilateral |
| Full Body B | Bisagra_Cadera, Empuje_Vertical, Tracción_Vertical, Core, Unilateral |
| Full Body C | Sentadilla, Empuje_Horizontal, Tracción_Vertical, Core, Bisagra_Cadera |
| Torso | Empuje_Horizontal, Empuje_Vertical, Tracción_Horizontal, Tracción_Vertical, Core |
| Pierna | Sentadilla, Bisagra_Cadera, Unilateral, Core |
| Empuje | Empuje_Horizontal, Empuje_Vertical, Core |
| Tracción | Tracción_Horizontal, Tracción_Vertical, Core |

#### `_MESOCICLOS` — Configuración de los 3 meses

| Mes | Título | RIR base | Series base | Reps |
|---|---|---|---|---|
| 1 | Adaptación Anatómica | RIR 4 | 3 | 12-15 |
| 2 | Sobrecarga Progresiva | RIR 3 | 4 | 10-12 |
| 3 | Intensificación | RIR 2 | 4 | 6-8 |

#### `_SEMANAS_DELOAD = {4, 8, 12}`
Semanas donde se aplica deload automático (última semana de cada mes).

---

### `_filtrar_df(lesiones, equipo) → DataFrame`

Aplica filtros de seguridad sobre `DF_EJERCICIOS` usando Pandas:

**Filtro de equipamiento:**
```python
# Si equipo contiene: "casa", "sin", "cuerpo", "bodyweight", "peso corporal"
df = df[df["Equipamiento"].isin(["Peso Corporal", "Mancuerna"])]
```

**Filtros de lesión por zona:**

| Zona | Keywords detectadas | Filtro aplicado |
|---|---|---|
| Lumbar | `lumbar`, `espalda`, `hernia`, `disco` | Excluye `Flag_Lesion == "Evitar_Lumbar"` |
| Rodilla | `rodilla`, `menisco`, `ligamento` | Excluye `Flag_Lesion == "Evitar_Rodilla"` |
| Hombro | `hombro`, `manguito`, `rotador` | Excluye `Flag_Lesion == "Evitar_Hombro"` |

---

### `_seleccionar_ejercicios(df, patrones, nivel, variante) → list`

Para cada patrón de movimiento requerido en la sesión, selecciona un ejercicio del DataFrame filtrado.

**Lógica de selección:**
1. Filtra candidatos por `Patron`
2. Prioriza el nivel del usuario; fallback a Principiante → Intermedio → Avanzado
3. Para patrones no-Core: prioriza ejercicios compuestos (`Es_Compuesto == True`)
4. Aplica `variante % len(candidatos)` como índice para generar variabilidad intra-semanal

El parámetro `variante` (0 o 1) garantiza que dos sesiones del mismo tipo en la misma semana (ej: dos "Torso" en split de 4 días) seleccionen ejercicios distintos.

---

### `_aplicar_periodizacion(ejercicios, mes_cfg, semana) → list`

Aplica las reglas de carga a la lista de ejercicios de una sesión:

| Condición | Regla |
|---|---|
| Mes 2 o 3 + ejercicio compuesto | `series_base += 1` |
| Semana en `{4, 8, 12}` (deload) | `series = max(2, int(series * 0.7))`, `RIR = "RIR 4 (DELOAD)"`, `reps = "12-15"` |

**Ejemplo de progresión para un compuesto:**

| Semana | Mes | Series | RIR | Reps |
|---|---|---|---|---|
| 1–3 | 1 (Adaptación) | 3 | RIR 4 | 12-15 |
| 4 | 1 (Deload) | 2 | RIR 4 (DELOAD) | 12-15 |
| 5–7 | 2 (Sobrecarga) | 5 (4+1) | RIR 3 | 10-12 |
| 8 | 2 (Deload) | 3 | RIR 4 (DELOAD) | 12-15 |
| 9–11 | 3 (Intensificación) | 5 (4+1) | RIR 2 | 6-8 |
| 12 | 3 (Deload) | 3 | RIR 4 (DELOAD) | 12-15 |

---

### `_construir_entrenamiento(nivel, objetivo, lesiones, equipo, dias_semana) → list`

Función orquestadora del macrociclo. Itera sobre los 3 mesociclos × 4 semanas × N sesiones del split y construye la lista completa de filas para la Tabla 3.

**Volumen generado (ejemplo 3 días/semana):**
- 12 semanas × 3 sesiones × 5 ejercicios = **180 filas**
- 3 semanas de deload con volumen reducido (semanas 4, 8, 12)

---

### Gráficos Matplotlib

#### `_grafico_dona(labels, sizes, hex_colors, titulo) → BytesIO`
Genera un donut chart. Backend `Agg` (sin pantalla), DPI 150, leyenda inferior en 2 columnas.

#### `_grafico_macros(macros_tabla) → BytesIO`
Wrapper para distribución de macronutrientes.

#### `_grafico_gasto(gasto_tabla) → BytesIO`
Wrapper para distribución del gasto energético.

---

### Generadores PDF

#### `generar_pdf_rutina(datos_usuario: dict) → BytesIO`

**Página 1 — Portada y Biometría**
- Título + objetivo + texto introductorio personalizado
- Tabla de biometría calculada

**Página 2 — Programa de Entrenamiento (12 semanas)**
- Agrupado por Mes → Semana → Sesión
- Semanas de deload marcadas en amarillo (`⚡ DELOAD`)
- Cada sesión tiene su propio encabezado de color oscuro
- Columnas: Ejercicio / Series-Reps / Carga / Objetivo Técnico

**Página 3 — Nutrición y NEAT**
- Estrategia nutricional en texto
- Gráfico de dona de macros + tabla de gramos lado a lado
- Explicación del NEAT + tabla de 5 estrategias
- Gráfico de dona de gasto energético

#### `generar_revista_nutricional(datos_usuario: dict) → BytesIO`
- Estrategia nutricional detallada por macronutriente
- Guía de compras semanal por categoría
- 5 reglas de oro nutricionales

Ambas funciones generan el PDF **en memoria** (`BytesIO`) sin escribir en disco.

---

## Base de datos de ejercicios (`ejercicios.csv`)

**48 ejercicios** organizados en 9 columnas:

| Columna | Tipo | Descripción |
|---|---|---|
| `ID_Ejercicio` | int | Identificador único |
| `Patron` | str | Patrón de movimiento (ver tabla abajo) |
| `Sesion_Tipo` | str | Tipo de sesión donde aplica (`Torso`, `Pierna`, `Full Body`) |
| `Nombre_ES` | str | Nombre del ejercicio en español |
| `Nivel` | str | `Principiante`, `Intermedio` o `Avanzado` |
| `Equipamiento` | str | `Barra`, `Mancuerna`, `Máquina`, `Polea`, `Peso Corporal`, `Accesorio` |
| `Flag_Lesion` | str | `Evitar_Lumbar`, `Evitar_Rodilla`, `Evitar_Hombro`, `Seguro_*` |
| `Objetivo_Tecnico` | str | Cue técnico principal para el ejercicio |
| `Es_Compuesto` | bool | `1` = compuesto (multi-articular), `0` = accesorio |

**Patrones de movimiento disponibles:**

| Patrón | Ejercicios incluidos |
|---|---|
| `Sentadilla` | Libre, Goblet, Búlgara, Hack, Prensa, Sumo |
| `Bisagra_Cadera` | Peso Muerto Convencional/Rumano/Sumo, Hip Thrust, Good Morning, Curl Femoral |
| `Empuje_Horizontal` | Press Banca Barra/Mancuernas, Flexiones, Press Inclinado, Aperturas |
| `Empuje_Vertical` | Press Militar Barra/Mancuernas, Elevaciones Laterales, Arnold Press |
| `Tracción_Horizontal` | Remo Mancuerna/Barra/Máquina/TRX/Invertido, Face Pull |
| `Tracción_Vertical` | Jalón al Pecho/Neutro, Dominadas/Asistidas, Pullover |
| `Core` | Plancha, Plancha Lateral/Dinámica, Ab Wheel, Dead Bug, Pallof Press |
| `Unilateral` | Zancada Caminando/Estática, Step Up, Extensión/Curl Unilateral |
| `Movilidad` | Cadera, Hombro, Torácica |

---

## Dependencias

| Librería | Versión mínima | Uso |
|---|---|---|
| `aiogram` | 3.0.0 | Framework async para bots de Telegram |
| `pandas` | 2.0.0 | Carga y filtrado del CSV de ejercicios |
| `reportlab` | 4.0.0 | Generación de PDFs |
| `matplotlib` | 3.7.0 | Gráficos de dona para los PDFs |
| `numpy` | 1.24.0 | Soporte numérico para matplotlib |
| `python-dotenv` | 1.0.0 | Carga de variables de entorno desde `.env` |
| `Pillow` | 10.0.0 | Procesamiento de imágenes (soporte reportlab) |

---

## Variables de entorno

| Variable | Descripción | Requerida |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Token del bot obtenido desde @BotFather | Sí |

El archivo `.env` está excluido del repositorio vía `.gitignore`. Usar `.env.example` como plantilla.

---

## Principios del coach

Codificados en `COACH_SYSTEM_PROMPT`:

1. **Prohibido inventar pesos** — Se usa RIR como indicador de carga relativa.
2. **Sin rutinas genéricas** — Cada plan se adapta a lesiones, equipamiento y nivel vía Pandas.
3. **Planes de 12 semanas** — Adaptación → Sobrecarga → Intensificación.
4. **Patrones de movimiento completos** — Empuje/tracción horizontal y vertical, dominante rodilla/cadera, core, unilateral en cada sesión.
5. **No llevar principiantes al fallo** — RIR mínimo de 2 incluso en el mes de intensificación.
6. **Deload obligatorio** — Semanas 4, 8 y 12 reducen volumen 30% y bajan a RIR 4 automáticamente.

---

## Progresión de carga

| Semanas | Mes | RIR | Series (compuesto) | Indicación |
|---|---|---|---|---|
| 1–3 | 1 Adaptación | RIR 4 | 3 | Técnica primero. No progresar carga hasta dominar el patrón. |
| 4 | Deload | RIR 4 | 2 | Reducción de volumen. Mantener técnica. |
| 5–7 | 2 Sobrecarga | RIR 3 | 5 | Si completas todas las reps, subir 2.5–5% la siguiente sesión. |
| 8 | Deload | RIR 4 | 3 | Recuperación activa. |
| 9–11 | 3 Intensificación | RIR 2 | 5 | Progresión semanal de +2.5kg en ejercicios principales. |
| 12 | Deload | RIR 4 | 3 | Cierre del macrociclo. Evaluar resultados. |

> **RIR (Reps In Reserve):** repeticiones que podrías hacer antes del fallo. RIR 4 = muy conservador. RIR 2 = cerca del límite con técnica intacta.
