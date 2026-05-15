import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from src.infrastructure.config import get_settings
from src.infrastructure.logging import setup_logging
from src.interfaces.services import get_interface_service

# ── CONFIGURACIÓN ──
setup_logging()
logger = logging.getLogger(__name__)
_settings = get_settings()
TOKEN = _settings.telegram_bot_token

# ── FSM PARA ENTRENADOR ──
class TrainerStates(StatesGroup):
    # Crear nuevo plan
    esperando_nombre_atleta = State()
    esperando_objetivo = State()
    esperando_nivel = State()
    esperando_edad = State()
    esperando_sexo = State()
    esperando_peso = State()
    esperando_talla = State()
    esperando_equipo = State()
    esperando_dias = State()
    esperando_lesiones = State()

    # Generar rutina semanal
    esperando_semana_rutina = State()

    # Datos actuales del atleta (almacenados en estado)
    datos_atleta_actual = {}

router = Router()

# ── HELPERS ──
def kb_inline(opciones: list) -> InlineKeyboardMarkup:
    """Crea teclado inline desde lista de (texto, callback_data)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c)] for t, c in opciones]
    )

def kb_semanas() -> InlineKeyboardMarkup:
    """Teclado para seleccionar semana (1-12)."""
    botones = []
    for i in range(0, 12, 3):
        fila = []
        for j in range(1, 4):
            semana = i + j
            if semana <= 12:
                fila.append(InlineKeyboardButton(text=f"Semana {semana}", callback_data=f"sem_{semana}"))
        botones.append(fila)
    return InlineKeyboardMarkup(inline_keyboard=botones)

# ════════════════════════════════════════════
# COMANDOS PRINCIPALES PARA ENTRENADOR
# ════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏋️ *RUTINATOR PARA ENTRENADORES*\n\n"
        "Herramienta profesional para generar planes de entrenamiento ATR "
        "y revistas nutricionales editoriales.\n\n"
        "*Comandos disponibles:*\n"
        "`/nuevoplan` - Crear nuevo plan para un atleta\n"
        "`/rutinasemanal` - Generar rutina semanal con feedback\n"
        "`/nutricion` - Generar revista nutricional editorial\n"
        "`/verdatos` - Ver datos del atleta actual\n"
        "`/limpiar` - Limpiar datos y empezar de nuevo",
        parse_mode="Markdown"
    )

@router.message(Command("nuevoplan"))
async def cmd_nuevo_plan(message: Message, state: FSMContext):
    await state.clear()
    await state.set_data({})  # Limpiar datos anteriores
    await message.answer(
        "📋 *CREAR NUEVO PLAN*\n\n"
        "Vamos a registrar los datos de tu atleta.\n\n"
        "*Nombre completo del atleta:*"
    )
    await state.set_state(TrainerStates.esperando_nombre_atleta)

@router.message(Command("rutinasemanal"))
async def cmd_rutina_semanal(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("atleta"):
        await message.answer(
            "⚠️ *Primero debes crear un plan con `/nuevoplan`*\n"
            "Necesito los datos del atleta para generar la rutina."
        )
        return

    await message.answer(
        f"📅 *GENERAR RUTINA SEMANAL*\n\n"
        f"Atleta: {data.get('atleta', 'No definido')}\n"
        f"Selecciona la semana a generar (1-12):\n\n"
        f"• *Acumulación*: Semanas 1-4 (Volumen Alto)\n"
        f"• *Transmutación*: Semanas 5-8 (Intensidad Alta)\n"
        f"• *Realización*: Semanas 9-12 (Intensidad Máxima)",
        reply_markup=kb_semanas(),
        parse_mode="Markdown"
    )
    await state.set_state(TrainerStates.esperando_semana_rutina)

@router.message(Command("nutricion"))
async def cmd_nutricion(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("atleta"):
        await message.answer(
            "⚠️ *Primero debes crear un plan con `/nuevoplan`*\n"
            "Necesito los datos del atleta para generar la revista nutricional."
        )
        return

    await message.answer("🥗 *Generando revista nutricional editorial...*")

    # Usar el servicio de interfaz (async, no bloquea el event loop)
    interface = get_interface_service()

    try:
        revista_buf = await interface.generar_pdf_nutricion_async(data)
        revista_file = BufferedInputFile(
            revista_buf.read(),
            filename=f"Nutricion_{data.get('atleta', 'Atleta')}.pdf"
        )

        await message.answer_document(
            revista_file,
            caption=f"✅ *REVISTA NUTRICIONAL EDITORIAL*\n"
                   f"Para: {data.get('atleta', 'Atleta')}\n"
                   f"Diseño oscuro con alimentos antiinflamatorios locales."
        )
    except Exception as e:
        logging.error(f"Error generando revista nutricional: {e}", exc_info=True)
        await message.answer("❌ Error al generar la revista nutricional. Intenta de nuevo.")

@router.message(Command("verdatos"))
async def cmd_ver_datos(message: Message, state: FSMContext):
    data = await state.get_data()
    interface = get_interface_service()
    respuesta = interface.formatear_datos_actuales(data)
    await message.answer(respuesta, parse_mode="Markdown")

@router.message(Command("limpiar"))
async def cmd_limpiar(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🧹 *Datos limpiados.*\nUsa `/nuevoplan` para comenzar con un nuevo atleta.")

# ════════════════════════════════════════════
# FLUJO DE CREACIÓN DE PLAN
# ════════════════════════════════════════════
@router.message(TrainerStates.esperando_nombre_atleta)
async def process_nombre_atleta(message: Message, state: FSMContext):
    await state.update_data(atleta=message.text)
    await message.answer(
        f"Atleta: *{message.text}* ✅\n\n"
        f"*¿Cuál es el objetivo principal del atleta?*",
        reply_markup=kb_inline([
            ("🔥 Quemar Grasa",        "obj_quemar"),
            ("💪 Ganar Músculo",        "obj_ganar"),
            ("⚖️ Recomposición Corporal","obj_recomp"),
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(TrainerStates.esperando_objetivo)

@router.callback_query(TrainerStates.esperando_objetivo)
async def process_obj(callback: CallbackQuery, state: FSMContext):
    mapa = {
        "obj_quemar": "Quemar Grasa",
        "obj_ganar":  "Ganar Músculo",
        "obj_recomp": "Recomposición Corporal",
    }
    obj = mapa[callback.data]
    await state.update_data(objetivo=obj)
    await callback.message.edit_text(
        f"Objetivo: *{obj}* ✅\n\n"
        f"*¿Cuál es el nivel de experiencia del atleta?*",
        reply_markup=kb_inline([
            ("🌱 Principiante (0–12 meses)", "lvl_p"),
            ("⚡ Intermedio (1–3 años)",      "lvl_i"),
            ("🏆 Avanzado (3+ años)",          "lvl_a"),
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(TrainerStates.esperando_nivel)

@router.callback_query(TrainerStates.esperando_nivel)
async def process_nivel(callback: CallbackQuery, state: FSMContext):
    mapa = {"lvl_p": "Principiante", "lvl_i": "Intermedio", "lvl_a": "Avanzado"}
    nivel = mapa[callback.data]
    await state.update_data(nivel=nivel)
    await callback.message.edit_text(
        f"Nivel: *{nivel}* ✅\n\n"
        f"*¿Cuántos años tiene el atleta?*"
    )
    await state.set_state(TrainerStates.esperando_edad)

@router.message(TrainerStates.esperando_edad)
async def process_edad(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (10 <= int(message.text) <= 100):
        return await message.answer("⚠️ Ingresa la edad en números (ej: 28).")
    await state.update_data(edad=int(message.text))
    await message.answer(
        "*¿Cuál es el sexo biológico del atleta?*",
        reply_markup=kb_inline([("👨 Masculino", "sex_m"), ("👩 Femenino", "sex_f")])
    )
    await state.set_state(TrainerStates.esperando_sexo)

@router.callback_query(TrainerStates.esperando_sexo)
async def process_sexo(callback: CallbackQuery, state: FSMContext):
    sexo = "Masculino" if callback.data == "sex_m" else "Femenino"
    await state.update_data(sexo=sexo)
    await callback.message.edit_text(
        f"Sexo: *{sexo}* ✅\n\n"
        f"*¿Cuánto pesa el atleta? (kg)*\nEj: 75"
    )
    await state.set_state(TrainerStates.esperando_peso)

@router.message(TrainerStates.esperando_peso)
async def process_peso(message: Message, state: FSMContext):
    try:
        peso = float(message.text.replace(",", "."))
        assert 30 <= peso <= 300
    except Exception:
        return await message.answer("⚠️ Ingresa el peso en kg (ej: 75 o 75.5).")
    await state.update_data(peso=peso)
    await message.answer("*¿Cuánto mide el atleta? (cm)*\nEj: 175")
    await state.set_state(TrainerStates.esperando_talla)

@router.message(TrainerStates.esperando_talla)
async def process_talla(message: Message, state: FSMContext):
    try:
        talla = float(message.text.replace(",", "."))
        assert 100 <= talla <= 250
    except Exception:
        return await message.answer("⚠️ Ingresa la talla en cm (ej: 175).")
    await state.update_data(talla=talla)
    await message.answer(
        "*¿Dónde entrena el atleta?*",
        reply_markup=kb_inline([
            ("🏋️ Gimnasio completo",    "eq_gym"),
            ("🏠 Casa con mancuernas",  "eq_casa"),
            ("🤸 Solo peso corporal",   "eq_body"),
        ])
    )
    await state.set_state(TrainerStates.esperando_equipo)

@router.callback_query(TrainerStates.esperando_equipo)
async def process_equipo(callback: CallbackQuery, state: FSMContext):
    mapa = {
        "eq_gym":  "Gimnasio completo",
        "eq_casa": "Casa con mancuernas",
        "eq_body": "Peso corporal",
    }
    equipo = mapa[callback.data]
    await state.update_data(equipamiento=equipo)
    await callback.message.edit_text(
        f"Equipamiento: *{equipo}* ✅\n\n"
        f"*¿Cuántos días por semana puede entrenar el atleta?*",
        reply_markup=kb_inline([
            ("2 días", "dias_2"), ("3 días", "dias_3"),
            ("4 días", "dias_4"), ("5 días", "dias_5"),
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(TrainerStates.esperando_dias)

@router.callback_query(TrainerStates.esperando_dias)
async def process_dias(callback: CallbackQuery, state: FSMContext):
    dias = callback.data.split("_")[1]
    await state.update_data(dias_semana=dias)
    await callback.message.edit_text(
        f"Días: *{dias}/semana* ✅\n\n"
        f"*¿El atleta tiene alguna lesión activa o zona de dolor?*\n"
        f"(Ej: rodilla derecha, lumbar, hombro izquierdo, o 'ninguna')",
        parse_mode="Markdown"
    )
    await state.set_state(TrainerStates.esperando_lesiones)

@router.message(TrainerStates.esperando_lesiones)
async def process_lesiones(message: Message, state: FSMContext):
    lesiones = message.text if message.text.strip().lower() != "ninguna" else "Ninguna"
    await state.update_data(lesiones=lesiones)

    data = await state.get_data()

    # Usar el servicio de interfaz para formatear
    interface = get_interface_service()
    resumen = interface.formatear_resumen(data)

    await message.answer(resumen, parse_mode="Markdown")

# ════════════════════════════════════════════
# GENERACIÓN DE RUTINA SEMANAL
# ════════════════════════════════════════════
@router.callback_query(TrainerStates.esperando_semana_rutina)
async def process_semana_rutina(callback: CallbackQuery, state: FSMContext):
    semana = int(callback.data.split("_")[1])
    data = await state.get_data()
    data["semana_actual"] = semana

    await callback.message.edit_text(f"⚙️ *Generando rutina para semana {semana}...*")

    # Usar el servicio de interfaz (async, no bloquea el event loop)
    interface = get_interface_service()

    try:
        rutina_buf = await interface.generar_pdf_rutina_semanal_async(data)
        rutina_file = BufferedInputFile(
            rutina_buf.read(),
            filename=f"Rutina_Semana{semana}_{data.get('atleta', 'Atleta')}.pdf"
        )

        # Determinar bloque ATR
        if 1 <= semana <= 4:
            bloque = "Acumulación"
        elif 5 <= semana <= 8:
            bloque = "Transmutación"
        else:
            bloque = "Realización"

        await callback.message.answer_document(
            rutina_file,
            caption=f"✅ *RUTINA SEMANAL CON FEEDBACK*\n"
                   f"Semana {semana} · Bloque {bloque}\n"
                   f"Atleta: {data.get('atleta', 'Atleta')}\n\n"
                   f"Incluye columnas para que el atleta registre:\n"
                   f"• Reps Logradas\n• Carga Real\n• Comentarios"
        )

        # Ofrecer generar otra semana
        await callback.message.answer(
            "¿Quieres generar otra semana?",
            reply_markup=kb_semanas()
        )

    except Exception as e:
        logging.error(f"Error generando rutina semanal: {e}", exc_info=True)
        await callback.message.answer("❌ Error al generar la rutina semanal. Intenta de nuevo.")

# ════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════
async def main():
    bot = Bot(token=TOKEN)
    dp  = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
