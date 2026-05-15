# Guía de Migración - RUTINATOR v2.0

## Patrón: Strangler Fig

La migración se hace **sin perder funcionalidad** mediante el patrón Strangler Fig:
1. Nueva estructura funciona en paralelo
2. Handlers redireccionan gradualmente
3. Código legacy se elimina cuando tests pasan

---

## Checklist de Regresión

Antes de cada fase de eliminación de código legacy, verificar:

- [ ] `/start` - Bot responde con menú de comandos
- [ ] `/nuevoplan` - Flujo completo de 10 pasos funciona
- [ ] `/rutinasemanal` - PDF se genera y envía correctamente
- [ ] `/nutricion` - Revista nutricional se genera y envía
- [ ] `/verdatos` - Muestra datos del atleta actual
- [ ] `/limpiar` - Limpia estado FSM

---

## Paso 1: Verificar Ambiente (YA COMPLETO)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Verificar que todo importa
python -c "
from src.interfaces.services import get_interface_service
from src.application import get_training_generator_service
from src.infrastructure.repositories import get_exercise_repository
print('✅ OK')
"

# Verificar linting
python -m ruff check src/
python -m mypy src/ --ignore-missing-imports
```

---

## Paso 2: Migrar Generadores PDF (Semana 1)

**Objetivo:** Reimplementar generadores PDF usando los nuevos modelos Pydantic.

### 2.1 Actualizar pdf_rutina.py
```python
# Reemplazar la función actual con:
from src.application import get_training_generator_service

def generar_pdf_rutina_sync(datos_usuario: dict) -> io.BytesIO:
    """Genera PDF de rutina completa."""
    service = get_training_generator_service()
    programa = service.generar_programa_desde_dict(datos_usuario)
    
    # Usar los datos del programa para generar PDF
    # (reimplementar usando programa.athlete, programa.semanas, etc.)
```

### 2.2 Actualizar pdf_semanal.py y pdf_nutricion.py
imilar a 2.1

### 2.3 Verificar
```bash
python -c "
from src.infrastructure.generators.pdf_rutina import generar_pdf_rutina_sync
print('✅ PDF rutina OK')
"
```

---

## Paso 3: Eliminar DF_EJERCICIOS Global (Semana 2)

**Objetivo:** El código legacy usa el repositorio en lugar del DataFrame global.

### 3.1 Actualizar logic_processor.py
```python
# Reemplazar:
# DF_EJERCICIOS: pd.DataFrame = _cargar_df()

# Con:
from src.infrastructure.repositories import get_exercise_repository

def _filtrar_df(lesiones: str, equipo: str) -> pd.DataFrame:
    repo = get_exercise_repository()
    return repo.filtrar_completo(equipamiento, lesiones)
```

### 3.2 Verificar que todo funciona igual
```bash
python -c "
from src.logic_processor import construir_programa
datos_test = {
    'atleta': 'Test',
    'objetivo': 'Quemar Grasa',
    'nivel': 'Principiante',
    'edad': 30,
    'sexo': 'Masculino',
    'peso': 80,
    'talla': 180,
    'equipamiento': 'Gimnasio completo',
    'dias_semana': '3',
    'lesiones': 'Ninguna',
}
programa = construir_programa(datos_test)
print(f'✅ Programa generado: {len(programa[\"entrenamiento\"])} ejercicios')
"
```

---

## Paso 4: Migrar Handlers del Bot (Semana 3)

**Objetivo:** Handlers usan servicios de aplicación directamente.

### 4.1 Actualizar bot_telegram.py
```python
# Reemplazar uso de logic_processor con servicios
from src.interfaces.services import get_interface_service
from src.application import get_training_generator_service

# En cmd_nutricion:
interface = get_interface_service()
buffer = await interface.generar_pdf_nutricion_async(data)
```

### 4.2 Verificar
Ejecutar todos los comandos del checklist de regresión.

---

## Paso 5: Eliminar logic_processor.py Legacy (Semana 4)

**Objetivo:** Código completamente migrado a nueva arquitectura.

### 5.1 Verificar que nada dependa de logic_processor
```bash
grep -r "from logic_processor" src/
grep -r "import logic_processor" src/
```

### 5.2 Eliminar
```bash
rm src/logic_processor.py
```

### 5.3 Actualizar imports del bot
```python
# Eliminar línea legacy:
from logic_processor import generar_pdf_rutina, generar_revista_nutricional, generar_rutina_semanal

# Ya no es necesaria - los PDFs se generan via interface_service
```

---

## Paso 6: Tests Unitarios (Semana 5)

### 6.1 Crear tests para domain/rules.py
```python
# tests/test_rules.py
import pytest
from src.domain.rules import calcular_imc, estimar_grasa, calcular_macros

def test_calcular_imc():
    assert calcular_imc(70, 170) == 24.2

def test_estimar_grasa():
    assert estimar_grasa(30, "Masculino", 24.0) > 0

def test_calcular_macros_quemar_grasa():
    macros = calcular_macros("Quemar Grasa", 80)
    assert macros.prot_g > 0
    assert macros.carb_g > 0
```

### 6.2 Crear tests para application/services
```python
# tests/test_services.py
import pytest
from src.application import get_training_generator_service, AthleteData

def test_generar_programa_completo():
    service = get_training_generator_service()
    datos = AthleteData(
        nombre="Test",
        objetivo="Quemar Grasa",
        nivel="Principiante",
        edad=30,
        sexo="Masculino",
        peso=80,
        talla=180,
        equipamiento="Gimnasio completo",
        dias_semana=3,
    )
    programa = service.generar_programa_completo(datos)
    
    assert programa.athlete.nombre == "Test"
    assert len(programa.semanas) == 12
```

### 6.3 Ejecutar tests
```bash
pytest tests/ -v
```

---

## Checklist Final de Migración

- [ ] Todos los tests pasan
- [ ] ruff no muestra errores
- [ ] mypy muestra errores solo en código legacy
- [ ] Bot funciona con todos los comandos
- [ ] PDFs se generan correctamente
- [ ] No hay DF_EJERCICIOS global
- [ ] Código cumple SRP (<150 líneas por archivo)

---

## Notas Importantes

### Mantener Compatibilidad
- Las funciones `generar_pdf_rutina_sync`, `generar_rutina_semanal_sync`, `generar_revista_nutricional_sync` deben mantener su firma original
- El parámetro `datos_usuario: dict` no debe cambiar

### Thread Safety
- Todo código de generación de PDF debe ejecutarse en thread pool via `async_bridge.py`
- Nunca bloquear el event loop con operaciones pandas/matplotlib/reportlab

### Logging
- Usar `logging.getLogger(__name__)` en cada módulo
- Niveles: DEBUG para desarrollo, INFO para producción

### Errores
- Nunca dejar errores silenciosos - siempre loggear
- Usartry/except con logging en operaciones de I/O