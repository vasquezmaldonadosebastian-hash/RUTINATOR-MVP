import asyncio
import logging
import os
import sys
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BufferedInputFile
)
from dotenv import load_dotenv
from logic_processor import generar_pdf_rutina, generar_revista_nutricional

# ── CONFIGURACIÓN ──
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# ── FSM ──
class OnboardingStates(StatesGroup):
    # Paso 1: Objetivo + experiencia
    esperando_objetivo = State()
    esperando_nivel    = State()
    # Paso 2: Datos físicos
    esperando_edad     = State()
    esperando_sexo     = State()
    esperando_peso     = State()
    esperando_talla    = State()
    # Paso 3: Equipamiento + disponibilidad
    esperando_equipo   = State()
    esperando_dias     = State()
    # Paso 4: Lesiones + deporte paralelo
    esperando_enfermedades         = State()
    esperando_detalle_enfermedades = State()
    esperando_lesiones             = State()
    esperando_detalle_lesiones     = State()
    esperando_embarazo             = State()
    esperando_deporte_paralelo     = State()
    # Paso 5: Preferencias + test
    esperando_preferencias    = State()
    esperando_resultados_test = State()

router = Router()

# ── HELPERS ──
def kb_inline(opciones: list) -> InlineKeyboardMarkup:
    """Crea teclado inline desde lista de (texto, callback_data)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=c)] for t, c in opciones]
    )

def get_yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Sí", callback_data=f"{prefix}_si"),
        InlineKeyboardButton(text="❌ No", callback_data=f"{prefix}_no")
    ]])

# ════════════════════════════════════════════
# PASO 1 — OBJETIVO + EXPERIENCIA
# ════════════════════════════════════════════
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Bienvenido a *RUTINATOR*\n\n"
        "Soy tu entrenador personal basado en evidencia científica.\n"
        "Voy a hacerte algunas preguntas para diseñar tu programa de 12 semanas.\n\n"
        "*¿Cuál es tu objetivo principal?*",
        reply_markup=kb_inline([
            ("🔥 Quemar Grasa",        "obj_quemar"),
            ("💪 Ganar Músculo",        "obj_ganar"),
            ("⚖️ Recomposición Corporal","obj_recomp"),
        ])
    )
    await state.set_state(OnboardingStates.esperando_objetivo)

@router.callback_query(OnboardingStates.esperando_objetivo)
async def process_obj(callback: CallbackQuery, state: FSMContext):
    mapa = {
        "obj_quemar": "Quemar Grasa",
        "obj_ganar":  "Ganar Músculo",
        "obj_recomp": "Recomposición Corporal",
    }
    obj = mapa[callback.data]
    await state.update_data(objetivo=obj, atleta=callback.from_user.full_name)
    await callback.message.edit_text(
        f"Objetivo: *{obj}* ✅\n\n*¿Cuál es tu nivel de experiencia en el gym?*",
        reply_markup=kb_inline([
            ("🌱 Principiante (0–12 meses)", "lvl_p"),
            ("⚡ Intermedio (1–3 años)",      "lvl_i"),
            ("🏆 Avanzado (3+ años)",          "lvl_a"),
        ])
    )
    await state.set_state(OnboardingStates.esperando_nivel)

@router.callback_query(OnboardingStates.esperando_nivel)
async def process_nivel(callback: CallbackQuery, state: FSMContext):
    mapa = {"lvl_p": "Principiante", "lvl_i": "Intermedio", "lvl_a": "Avanzado"}
    nivel = mapa[callback.data]
    await state.update_data(nivel=nivel)
    await callback.message.edit_text(
        f"Nivel: *{nivel}* ✅\n\n*¿Cuántos años tienes?*"
    )
    await state.set_state(OnboardingStates.esperando_edad)

# ════════════════════════════════════════════
# PASO 2 — DATOS FÍSICOS
# ════════════════════════════════════════════
@router.message(OnboardingStates.esperando_edad)
async def process_edad(message: Message, state: FSMContext):
    if not message.text.isdigit() or not (10 <= int(message.text) <= 100):
        return await message.answer("⚠️ Ingresa tu edad en números (ej: 28).")
    await state.update_data(edad=int(message.text))
    await message.answer(
        "*¿Cuál es tu sexo biológico?*",
        reply_markup=kb_inline([("👨 Masculino", "sex_m"), ("👩 Femenino", "sex_f")])
    )
    await state.set_state(OnboardingStates.esperando_sexo)

@router.callback_query(OnboardingStates.esperando_sexo)
async def process_sexo(callback: CallbackQuery, state: FSMContext):
    sexo = "Masculino" if callback.data == "sex_m" else "Femenino"
    await state.update_data(sexo=sexo)
    await callback.message.edit_text(f"Sexo: *{sexo}* ✅\n\n*¿Cuánto pesas? (kg)*\nEj: 75")
    await state.set_state(OnboardingStates.esperando_peso)

@router.message(OnboardingStates.esperando_peso)
async def process_peso(message: Message, state: FSMContext):
    try:
        peso = float(message.text.replace(",", "."))
        assert 30 <= peso <= 300
    except Exception:
        return await message.answer("⚠️ Ingresa tu peso en kg (ej: 75 o 75.5).")
    await state.update_data(peso=peso)
    await message.answer("*¿Cuánto mides? (cm)*\nEj: 175")
    await state.set_state(OnboardingStates.esperando_talla)

@router.message(OnboardingStates.esperando_talla)
async def process_talla(message: Message, state: FSMContext):
    try:
        talla = float(message.text.replace(",", "."))
        assert 100 <= talla <= 250
    except Exception:
        return await message.answer("⚠️ Ingresa tu talla en cm (ej: 175).")
    await state.update_data(talla=talla)
    await message.answer(
        "*¿Dónde entrenas?*",
        reply_markup=kb_inline([
            ("🏋️ Gimnasio completo",    "eq_gym"),
            ("🏠 Casa con mancuernas",  "eq_casa"),
            ("🤸 Solo peso corporal",   "eq_body"),
        ])
    )
    await state.set_state(OnboardingStates.esperando_equipo)

# ════════════════════════════════════════════
# PASO 3 — EQUIPAMIENTO + DISPONIBILIDAD
# ════════════════════════════════════════════
@router.callback_query(OnboardingStates.esperando_equipo)
async def process_equipo(callback: CallbackQuery, state: FSMContext):
    mapa = {
        "eq_gym":  "Gimnasio completo",
        "eq_casa": "Casa con mancuernas",
        "eq_body": "Peso corporal",
    }
    equipo = mapa[callback.data]
    await state.update_data(equipamiento=equipo)
    await callback.message.edit_text(
        f"Equipamiento: *{equipo}* ✅\n\n*¿Cuántos días por semana puedes entrenar?*",
        reply_markup=kb_inline([
            ("2 días", "dias_2"), ("3 días", "dias_3"),
            ("4 días", "dias_4"), ("5 días", "dias_5"),
        ])
    )
    await state.set_state(OnboardingStates.esperando_dias)

@router.callback_query(OnboardingStates.esperando_dias)
async def process_dias(callback: CallbackQuery, state: FSMContext):
    dias = callback.data.split("_")[1]
    await state.update_data(dias_semana=dias)
    await callback.message.edit_text(
        f"Días: *{dias}/semana* ✅\n\n*¿Padeces alguna enfermedad crónica?*\n"
        "(Diabetes, hipertensión, cardiopatía, etc.)",
        reply_markup=get_yes_no_kb("enf")
    )
    await state.set_state(OnboardingStates.esperando_enfermedades)

# ════════════════════════════════════════════
# PASO 4 — SALUD + LESIONES + DEPORTE
# ════════════════════════════════════════════
@router.callback_query(OnboardingStates.esperando_enfermedades)
async def process_enf(callback: CallbackQuery, state: FSMContext):
    if callback.data == "enf_si":
        await callback.message.edit_text("Detalla tu condición médica:")
        await state.set_state(OnboardingStates.esperando_detalle_enfermedades)
    else:
        await state.update_data(enfermedades="Ninguna")
        await callback.message.edit_text(
            "*¿Tienes alguna lesión activa o zona de dolor?*",
            reply_markup=get_yes_no_kb("les")
        )
        await state.set_state(OnboardingStates.esperando_lesiones)

@router.message(OnboardingStates.esperando_detalle_enfermedades)
async def process_det_enf(message: Message, state: FSMContext):
    await state.update_data(enfermedades=message.text)
    await message.answer(
        "⚠️ *Disclaimer médico:* Con una condición crónica, consulta a tu médico antes de iniciar.\n\n"
        "*¿Tienes alguna lesión activa o zona de dolor?*",
        reply_markup=get_yes_no_kb("les")
    )
    await state.set_state(OnboardingStates.esperando_lesiones)

@router.callback_query(OnboardingStates.esperando_lesiones)
async def process_les(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "les_si":
        await callback.message.edit_text(
            "Describe tu lesión o zona de dolor:\n(Ej: rodilla derecha, lumbar, hombro izquierdo)"
        )
        await state.set_state(OnboardingStates.esperando_detalle_lesiones)
    else:
        await state.update_data(lesiones="Ninguna")
        await _siguiente_tras_lesiones(callback.message, state, data)

@router.message(OnboardingStates.esperando_detalle_lesiones)
async def process_det_les(message: Message, state: FSMContext):
    await state.update_data(lesiones=message.text)
    data = await state.get_data()
    await _siguiente_tras_lesiones(message, state, data)

async def _siguiente_tras_lesiones(message: Message, state: FSMContext, data: dict):
    if data.get("sexo") == "Femenino":
        await message.answer(
            "*¿Estás en periodo de embarazo o postparto reciente?*",
            reply_markup=get_yes_no_kb("emb")
        )
        await state.set_state(OnboardingStates.esperando_embarazo)
    else:
        await state.update_data(embarazo="No aplica")
        await message.answer(
            "*¿Practicas algún deporte o actividad física adicional?*\n"
            "(Ej: fútbol, ciclismo, natación, artes marciales, o ninguno)"
        )
        await state.set_state(OnboardingStates.esperando_deporte_paralelo)

@router.callback_query(OnboardingStates.esperando_embarazo)
async def process_emb(callback: CallbackQuery, state: FSMContext):
    res = "Sí" if callback.data == "emb_si" else "No"
    await state.update_data(embarazo=res)
    if res == "Sí":
        await callback.message.answer(
            "⚠️ *Aviso:* Este plan debe ser supervisado por tu obstetra o médico tratante."
        )
    await callback.message.answer(
        "*¿Practicas algún deporte o actividad física adicional?*\n"
        "(Ej: fútbol, ciclismo, natación, o ninguno)"
    )
    await state.set_state(OnboardingStates.esperando_deporte_paralelo)

@router.message(OnboardingStates.esperando_deporte_paralelo)
async def process_deporte(message: Message, state: FSMContext):
    await state.update_data(deporte_paralelo=message.text)
    await message.answer(
        "*¿Tienes alguna preferencia o ejercicio que NO quieras hacer?*\n"
        "(Ej: no me gustan las sentadillas, prefiero no correr, etc. — o escribe 'ninguna')"
    )
    await state.set_state(OnboardingStates.esperando_preferencias)

# ════════════════════════════════════════════
# PASO 5 — PREFERENCIAS + TEST FINAL
# ════════════════════════════════════════════
@router.message(OnboardingStates.esperando_preferencias)
async def process_preferencias(message: Message, state: FSMContext):
    await state.update_data(preferencias=message.text)
    data = await state.get_data()
    nivel = data.get("nivel", "Principiante")
    edad  = data.get("edad", 25)

    if edad >= 60:
        instrucciones = (
            "📋 *Senior Fitness Test*\n\n"
            "Realiza estos dos tests y anota tus resultados:\n"
            "1️⃣ Levantarse de la silla en 30s (¿cuántas veces?)\n"
            "2️⃣ Flexiones de brazos en 30s (¿cuántas?)\n\n"
            "Escribe tus resultados (ej: *12, 8*)"
        )
    elif nivel == "Principiante":
        instrucciones = (
            "📋 *Test de Condición Básica*\n\n"
            "Realiza AMRAP en 60 segundos de cada uno:\n"
            "1️⃣ Sentadillas con peso corporal\n"
            "2️⃣ Flexiones (rodillas si es necesario)\n"
            "3️⃣ Plancha (segundos aguantados)\n\n"
            "Escribe tus resultados (ej: *25, 15, 40s*)"
        )
    elif nivel == "Intermedio":
        instrucciones = (
            "📋 *Test Intermedio*\n\n"
            "Ingresa tu RM estimado (peso máximo para 1 rep) en:\n"
            "1️⃣ Sentadilla\n"
            "2️⃣ Press Banca\n\n"
            "Si no sabes tu RM, ingresa el peso que usas para 8-10 reps.\n"
            "Escribe tus resultados (ej: *80kg, 60kg*)"
        )
    else:
        instrucciones = (
            "📋 *Test Avanzado*\n\n"
            "Ingresa tu RM real en los 3 grandes:\n"
            "1️⃣ Sentadilla\n"
            "2️⃣ Press Banca\n"
            "3️⃣ Peso Muerto\n\n"
            "Escribe tus resultados (ej: *120kg, 90kg, 150kg*)"
        )

    await message.answer(instrucciones)
    await state.set_state(OnboardingStates.esperando_resultados_test)

# ════════════════════════════════════════════
# GENERACIÓN FINAL
# ════════════════════════════════════════════
@router.message(OnboardingStates.esperando_resultados_test)
async def process_final(message: Message, state: FSMContext):
    await state.update_data(resultados_test=message.text)
    data = await state.get_data()

    msg_wait = await message.answer(
        "⚙️ *Procesando tu perfil...*\n\n"
        "Analizando biometría, historial y objetivos.\n"
        "Generando tu programa personalizado de 12 semanas. Un momento..."
    )

    try:
        rutina_buf  = generar_pdf_rutina(data)
        revista_buf = generar_revista_nutricional(data)

        rutina_file  = BufferedInputFile(rutina_buf.read(),  filename="RUTINATOR_Plan_12_Semanas.pdf")
        revista_file = BufferedInputFile(revista_buf.read(), filename="RUTINATOR_Nutricion.pdf")

        await message.answer_document(
            rutina_file,
            caption="✅ *Tu Programa de Entrenamiento — 12 Semanas*\nIncluye biometría, ejercicios por mes y estrategia NEAT."
        )
        await message.answer_document(
            revista_file,
            caption="🥗 *Tu Guía Nutricional Personalizada*\nMacros, alimentos recomendados y reglas de oro."
        )
        await msg_wait.delete()
        await message.answer(
            "🎯 *¡Listo, {nombre}!*\n\n"
            "Tienes tu pack completo. Recuerda:\n"
            "• Sigue el plan al menos 4 semanas antes de juzgar resultados.\n"
            "• La progresión es gradual: si completas todas las reps, sube 2.5–5% de carga.\n"
            "• El descanso y la nutrición son tan importantes como el entrenamiento.\n\n"
            "¡A entrenar! 💪".format(nombre=data.get("atleta", ""))
        )

    except Exception as e:
        logging.error(f"Error generando PDFs: {e}", exc_info=True)
        await msg_wait.delete()
        await message.answer(
            "❌ Hubo un error al generar tu plan. Por favor escribe /start para intentarlo de nuevo."
        )

    await state.clear()


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
