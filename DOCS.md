# RUTINATOR — Documentación Técnica v2.0

> Bot de Telegram para **entrenadores** que genera programas de entrenamiento con periodización ATR y revistas nutricionales editoriales personalizadas.
>
> **v2.0** — Arquitectura limpia completa. Monolito `logic_processor.py` eliminado.

---

## Índice

1. [Arquitectura general](#arquitectura-general)
2. [Instalación y configuración](#instalación-y-configuración)
3. [Estructura del proyecto](#estructura-del-proyecto)
4. [Flujo de trabajo del entrenador](#flujo-de-trabajo-del-entrenador)
5. [Comandos disponibles](#comandos-disponibles)
6. [Capas de la arquitectura](#capas-de-la-arquitectura)
   - [domain/](#domain)
   - [application/](#application)
   - [infrastructure/](#infrastructure)
   - [interfaces/](#interfaces)
7. [Periodización ATR](#periodización-atr)
8. [Motor de anti-monotonía](#motor-de-anti-monotonía)
9. [Generadores PDF](#generadores-pdf)
10. [Base de datos de ejercicios](#base-de-datos-de-ejercicios)
11. [Tests](#tests)
12. [Dependencias](#dependencias)
13. [Variables de entorno](#variables-de-entorno)

---

## Arquitectura general

```
Entrenador (Telegram)
       │
       ▼
  src/main.py                  ← Punto de entrada único
       │
       ▼
  src/bot_telegram.py          ← FSM + handlers (interfaces layer)
       │
       ▼
  src/interfaces/services.py   ← Glue async: handlers → application
       │
       ▼
  src/application/             ← Casos de uso y orquestación
  ├── training_generator_service.py   ← Orquestador principal
  ├── periodization_service.py        ← Motor ATR + anti-monotonía
  └── nutrition_service.py            ← Macros y planes nutricionales
       │
       ▼
  src/domain/                  ← Reglas puras, sin I/O
  ├── models.py                ← Pydantic v2: Athlete, TrainingContext, etc.
  └── rules.py                 ← Cálculos fisiológicos y lógica ATR pura
       │
  src/infrastructure/          ← Repositorios, PDFs, config, async bridge
  ├── repositories/
  │   └── exercise_repository.py     ← Reemplaza DF_EJERCICIOS global
  ├── generators/
  │   ├── pdf_rutina.py              ← PDF plan completo 12 semanas
  │   ├── pdf_semanal.py             ← PDF rutina semanal con feedback
  │   └── pdf_nutricion.py          ← PDF revista nutricional editorial
  ├── async_bridge.py                ← ThreadPoolExecutor para pandas/reportlab
  ├── config.py                      ← pydantic-settings (.env)
  └── logging.py                     ← Logging estructurado
```

**Principio clave:** El event loop de aiogram **nunca se bloquea**. Toda operación con pandas, matplotlib o reportlab se ejecuta en thread pool via `async_bridge.py`.

---

## Instalación y configuración

```bash
# 1. Clonar el repositorio
git clone <repo>
cd RUTINATOR-MVP

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar el token
cp .env.example .env
# Editar .env y reemplazar con tu token de @BotFather
TELEGRAM_BOT_TOKEN=tu_token_aqui

# 4. Ejecutar
python src/main.py
```

---

## Estructura del proyecto

```
RUTINATOR-MVP/
├── .env                        # Token de Telegram (no commitear)
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── pyproject.toml              # Configuración de ruff, mypy, pytest
├── requirements.txt
├── DOCS.md                     # Este archivo
├── MIGRATION_GUIDE.md          # Guía del proceso de refactorización
├── data/
│   └── ejercicios.csv          # Base de datos de ejercicios (48 filas, 9 cols)
├── src/
│   ├── main.py                 # Punto de entrada único
│   ├── bot_telegram.py         # Bot, FSM y handlers
│   ├── domain/
│   │   ├── models.py           # Modelos Pydantic v2
│   │   └── rules.py            # Reglas de negocio puras
│   ├── application/
│   │   ├── training_generator_service.py
│   │   ├── periodization_service.py
│   │   └── nutrition_service.py
│   ├── infrastructure/
│   │   ├── config.py           # pydantic-settings
│   │   ├── logging.py          # Logging estructurado
│   │   ├── async_bridge.py     # ThreadPoolExecutor
│   │   ├── repositories/
│   │   │   └── exercise_repository.py
│   │   └── generators/
│   │       ├── base.py
│   │       ├── pdf_rutina.py
│   │       ├── pdf_semanal.py
│   │       └── pdf_nutricion.py
│   └── interfaces/
│       └── services.py         # Glue async entre bot y application
└── tests/
    ├── test_models.py          # 7 tests — modelos Pydantic
    ├── test_rules.py           # 47 tests — reglas de dominio
    └── test_services.py        # 21 tests — servicios de aplicación
```

---

## Flujo de trabajo del Entrenador

```
/nuevoplan
  │
  ├─ Nombre del atleta
  ├─ Objetivo (Quemar Grasa / Ganar Músculo / Recomposición)
  ├─ Nivel (Principiante / Intermedio / Avanzado)
  ├─ Edad
  ├─ Sexo
  ├─ Peso (kg)
  ├─ Talla (cm)
  ├─ Equipamiento (Gimnasio completo / Casa con mancuernas / Peso corporal)
  ├─ Días/semana (2-5)
  └─ Lesiones (libre texto)
        │
        ▼
  Datos almacenados en estado FSM
        │
        ├─→ /rutinasemanal → Seleccionar semana (1-12) → PDF con feedback
        │
        └─→ /nutricion → PDF revista nutricional editorial
```

---

## Comandos disponibles

| Comando | Descripción |
|---|---|
| `/start` | Muestra menú de comandos disponibles |
| `/nuevoplan` | Inicia flujo para registrar datos de un nuevo atleta |
| `/rutinasemanal` | Genera rutina semanal específica (1-12) con columnas de feedback |
| `/nutricion` | Genera revista nutricional editorial independiente |
| `/verdatos` | Muestra los datos del atleta actual almacenado |
| `/limpiar` | Limpia los datos y permite empezar con un nuevo atleta |

---

## Capas de la arquitectura

### domain/

Reglas puras sin I/O. Nunca importa de otras capas del proyecto.

#### `models.py` — Modelos Pydantic v2

| Modelo | Descripción |
|---|---|
| `Athlete` | Datos del atleta con validación de frontera |
| `Biometria` | IMC, masa muscular, agua, grasa visceral |
| `Macros` | Gramos y porcentajes de macronutrientes |
| `GastoEnergetico` | TMB, NEAT, ejercicio, TEF |
| `ATRConfig` | Configuración de un bloque ATR |
| `Ejercicio` | Ejercicio con series, reps y carga |
| `SesionEntrenamiento` | Una sesión con lista de ejercicios |
| `SemanaEntrenamiento` | Una semana con bloque ATR y sesiones |
| `NutricionPlan` | Estrategia, macros, guía de compras, reglas |
| `ProgramaCompleto` | Programa completo del atleta |

#### `rules.py` — Reglas de negocio puras

| Función | Descripción |
|---|---|
| `calcular_imc(peso, altura)` | Fórmula IMC estándar |
| `estimar_grasa(edad, sexo, imc)` | Fórmula de Deurenberg |
| `estimar_agua(grasa)` | Estimación de agua corporal |
| `calcular_macros(objetivo, peso)` | Macros según objetivo |
| `calcular_gasto(nivel)` | Desglose energético según nivel |
| `obtener_bloque_desde_semana(semana)` | Mapeo semana → BloqueATR |
| `es_semana_deload(semana)` | True para semanas 4, 8, 12 |
| `obtener_config_semana(semana)` | ATRConfig con deload aplicado |
| `obtener_split(dias)` | Lista de sesiones según días |
| `obtener_patrones_sesion(nombre)` | Patrones de movimiento por sesión |
| `generar_estrategia_nutricional(objetivo, macros)` | NutricionPlan completo |
| `generar_intro_neat(objetivo)` | Texto introductorio NEAT |
| `generar_estrategias_neat()` | Lista de 5 estrategias NEAT |

---

### application/

Casos de uso. Orquesta domain + infrastructure. Sin lógica de presentación.

#### `training_generator_service.py`

Orquestador principal. Recibe datos crudos (dict o `AthleteData`) y devuelve `ProgramaCompleto`.

```python
service = get_training_generator_service()

# Desde dict (compatibilidad con bot)
programa = service.generar_programa_desde_dict(datos_dict)

# Desde dataclass tipado
datos = AthleteData(nombre="Juan", objetivo="Quemar Grasa", ...)
programa = service.generar_programa_completo(datos)
programa = service.generar_programa_completo(datos, semana=5)  # semana específica
```

#### `periodization_service.py`

Motor ATR con anti-monotonía. Genera `list[SemanaEntrenamiento]`.

- Filtra ejercicios por equipamiento y lesiones via `ExerciseRepository`
- Aplica configuración ATR (series, reps, RIR) por semana
- Rota ejercicios accesorios al cambiar de bloque (anti-monotonía)
- Marca deloads automáticamente en semanas 4, 8, 12

#### `nutrition_service.py`

Calcula macros y genera planes nutricionales según objetivo.

---

### infrastructure/

Implementaciones concretas. Nunca importada por domain.

#### `repositories/exercise_repository.py`

Reemplaza el `DF_EJERCICIOS` global del monolito original.

```python
repo = get_exercise_repository()
df = repo.filtrar_completo(equipamiento="Gimnasio completo", lesiones="rodilla")
ejercicios = repo.seleccionar_ejercicios_sesion(df, patrones, nivel, variante=0)
```

- Carga el CSV una sola vez (singleton con caché)
- Thread-safe para uso en thread pool
- Filtros por equipamiento y lesiones separados y componibles

#### `async_bridge.py`

Garantiza que el event loop de aiogram nunca se bloquee.

```python
# Uso via AsyncPDFGenerator (recomendado)
pdf_gen = get_async_pdf_generator()
buffer = await pdf_gen.generate_rutina_semanal(datos)

# Uso via decorador
@run_in_executor
def operacion_bloqueante():
    return pandas_heavy_operation()

result = await operacion_bloqueante()
```

#### `config.py`

Configuración centralizada via pydantic-settings. Lee `.env` automáticamente.

```python
settings = get_settings()
settings.telegram_bot_token   # str
settings.data_dir             # Path
settings.ejercicios_csv_path  # Path
settings.log_level            # str (default: "INFO")
settings.pdf_margin           # float (default: 0.6)
settings.pdf_dpi              # int (default: 150)
```

#### `generators/`

Los 3 generadores PDF son funciones síncronas ejecutadas en thread pool.

| Generador | Función | Descripción |
|---|---|---|
| `pdf_rutina.py` | `generar_pdf_rutina_sync(datos)` | Plan completo 12 semanas |
| `pdf_semanal.py` | `generar_rutina_semanal_sync(datos)` | Semana específica con feedback |
| `pdf_nutricion.py` | `generar_revista_nutricional_sync(datos)` | Revista editorial oscura |

Todos devuelven `io.BytesIO`.

---

### interfaces/

Capa de presentación. Solo conoce application, nunca domain directamente.

#### `services.py` — InterfaceService

Glue entre handlers del bot y los servicios de aplicación.

```python
interface = get_interface_service()

# PDFs async (no bloquean el event loop)
buffer = await interface.generar_pdf_rutina_semanal_async(data)
buffer = await interface.generar_pdf_nutricion_async(data)

# Formateo de mensajes
texto = interface.formatear_resumen(data)
texto = interface.formatear_datos_actuales(data)
```

---

## Periodización ATR

El sistema implementa el modelo ATR (Acumulación, Transmutación, Realización) de 12 semanas:

| Bloque | Semanas | Volumen | Intensidad | RIR | Series Base | Reps |
|---|---|---|---|---|---|---|
| **Acumulación** | 1-4 | Alto | Media | RIR 3 | 4 | 10-12 |
| **Transmutación** | 5-8 | Medio | Alta | RIR 2 | 3 | 8-10 |
| **Realización** | 9-12 | Bajo | Máxima | RIR 1 | 2 | 6-8 |

### Semanas de DELOAD

Las semanas 4, 8 y 12 tienen reducción automática del 30% en volumen:
- Series reducidas: `series_base × 0.7` (mínimo 2)
- RIR: "RIR 4 (DELOAD)"
- Reps: "12-15"

### Splits de entrenamiento

| Días | Split |
|---|---|
| 2 | Full Body A, Full Body B |
| 3 | Full Body A, Full Body B, Full Body C |
| 4 | Torso, Pierna, Torso, Pierna |
| 5 | Empuje, Tracción, Pierna, Torso, Pierna |

---

## Motor de anti-monotonía

Al cambiar de bloque ATR (ej: Acumulación → Transmutación):
- Ejercicios **compuestos** (`Es_Compuesto == True`) se mantienen — son la base del programa
- Ejercicios **accesorios** rotan automáticamente — evitan adaptación y monotonía

El historial de ejercicios por bloque se mantiene en memoria durante la generación del programa completo.

---

## Generadores PDF

### PDF 1: Plan Completo (`pdf_rutina.py`)

Genera el plan de 12 semanas completo. Secciones:
- Portada con datos del atleta e introducción personalizada
- Biometría (IMC, masa muscular, agua, grasa visceral)
- Programa de entrenamiento agrupado por mes → semana → sesión
- Estrategia nutricional con gráfico de macros (dona matplotlib)
- NEAT con estrategias y gráfico de gasto energético

### PDF 2: Rutina Semanal (`pdf_semanal.py`)

Genera una semana específica con columnas para feedback del atleta:

| Columna | Descripción |
|---|---|
| `Ejercicio` | Nombre del ejercicio |
| `Series/Reps Objetivo` | Prescripción del entrenador |
| `Carga Sugerida` | RIR objetivo |
| `Reps Logradas` | **Vacío — completa el atleta** |
| `Carga Real` | **Vacío — completa el atleta** |
| `Comentarios` | **Vacío — completa el atleta** |

Incluye instrucciones de feedback y objetivo del bloque actual.

### PDF 3: Revista Nutricional (`pdf_nutricion.py`)

Diseño editorial oscuro (fondo `#0E1113`). Dos partes:
- **Parte A — Genérica:** Tabla de alimentos antiinflamatorios locales (Maqui, Murta, Jurel, Salmón, Quinua, Cúrcuma, Brócoli)
- **Parte B — Específica:** Macros del atleta, guía de compras semanal adaptada al objetivo, reglas de oro nutricionales

---

## Base de datos de ejercicios (`ejercicios.csv`)

**48 ejercicios** organizados en 9 columnas:

| Columna | Tipo | Descripción |
|---|---|---|
| `ID_Ejercicio` | int | Identificador único |
| `Patron` | str | Patrón de movimiento |
| `Sesion_Tipo` | str | Tipo de sesión donde aplica |
| `Nombre_ES` | str | Nombre del ejercicio en español |
| `Nivel` | str | Principiante, Intermedio o Avanzado |
| `Equipamiento` | str | Barra, Mancuerna, Máquina, Polea, Peso Corporal |
| `Flag_Lesion` | str | Evitar_Lumbar, Evitar_Rodilla, Evitar_Hombro, Seguro_* |
| `Objetivo_Tecnico` | str | Cue técnico principal |
| `Es_Compuesto` | bool | 1 = compuesto, 0 = accesorio |

---

## Tests

```bash
# Ejecutar todos los tests
python -m pytest tests/ -v

# Solo domain
python -m pytest tests/test_models.py tests/test_rules.py -v

# Solo servicios
python -m pytest tests/test_services.py -v
```

**Cobertura actual: 75 tests, 100% passing**

| Archivo | Tests | Cobertura |
|---|---|---|
| `test_models.py` | 7 | Validación Pydantic, rangos, normalización |
| `test_rules.py` | 47 | IMC, grasa, macros, gasto, ATR completo, NEAT |
| `test_services.py` | 21 | Servicios de aplicación, filtros, splits, deloads |

---

## Dependencias

| Librería | Uso |
|---|---|
| `aiogram` 3.x | Framework async para bots de Telegram |
| `pandas` 2.x | Carga y filtrado del CSV de ejercicios |
| `reportlab` 4.x | Generación de PDFs |
| `matplotlib` 3.x | Gráficos de dona |
| `numpy` | Soporte numérico |
| `python-dotenv` | Carga de variables de entorno |
| `Pillow` | Procesamiento de imágenes |
| `pydantic` 2.x | Modelos de dominio y validación |
| `pydantic-settings` 2.x | Configuración desde .env |
| `pytest` | Tests unitarios |
| `ruff` | Linting y formateo |
| `mypy` | Type checking |

---

## Variables de entorno

| Variable | Requerida | Descripción |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Token del bot de @BotFather |
| `LOG_LEVEL` | ❌ | Nivel de logging (default: INFO) |
| `DATA_DIR` | ❌ | Ruta al directorio de datos |
| `PDF_MARGIN` | ❌ | Margen de PDFs en pulgadas (default: 0.6) |
| `PDF_DPI` | ❌ | DPI de gráficos en PDFs (default: 150) |

El archivo `.env` está excluido del repositorio. Usar `.env.example` como plantilla.
