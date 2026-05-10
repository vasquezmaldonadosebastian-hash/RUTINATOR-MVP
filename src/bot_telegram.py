import asyncio
import logging
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

# Importar lógica local
from logic_processor import generar_pdf_rutina, generar_revista_nutricional

# --- CONFIGURACIÓN ---
TOKEN = "TU_TELEGRAM_BOT_TOKEN"
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# --- FSM AVANZADO (SPRINT 5) ---
class OnboardingStates(StatesGroup):
    esperando_objetivo = State()
    esperando_edad = State()
    esperando_sexo = State()
    esperando_peso = State()
    esperando_talla = State()
    esperando_enfermedades = State()
    esperando_detalle_enfermedades = State()
    esperando_lesiones = State()
    esperando_detalle_lesiones = State()
    esperando_embarazo = State()
    esperando_nivel = State()
    esperando_resultados_test = State()

router = Router()

# --- HELPER KEYBOARDS ---
def get_yes_no_kb(prefix: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Sí", callback_data=f"{prefix}_si"),
         InlineKeyboardButton(text="❌ No", callback_data=f"{prefix}_no")]
    ])

# --- HANDLERS ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Quemar Grasa", callback_data="obj_quemar")],
        [InlineKeyboardButton(text="💪 Ganar Músculo", callback_data="obj_ganar")]
    ])
    await message.answer("¡Bienvenido a **RUTINATOR**! Iniciamos tu anamnesis clínica y deportiva.\n\n¿Cuál es tu objetivo?", reply_markup=kb)
    await state.set_state(OnboardingStates.esperando_objetivo)

@router.callback_query(OnboardingStates.esperando_objetivo)
async def process_obj(callback: CallbackQuery, state: FSMContext):
    obj = "Quemar Grasa" if callback.data == "obj_quemar" else "Ganar Músculo"
    await state.update_data(objetivo=obj, atleta=callback.from_user.full_name)
    await callback.message.edit_text(f"Objetivo: {obj}. ¿Cuál es tu **edad**?")
    await state.set_state(OnboardingStates.esperando_edad)

@router.message(OnboardingStates.esperando_edad)
async def process_edad(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Por favor, introduce tu edad en números.")
    await state.update_data(edad=int(message.text))
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Masculino", callback_data="sex_m"),
         InlineKeyboardButton(text="Femenino", callback_data="sex_f")]
    ])
    await message.answer("Selecciona tu sexo:", reply_markup=kb)
    await state.set_state(OnboardingStates.esperando_sexo)

@router.callback_query(OnboardingStates.esperando_sexo)
async def process_sexo(callback: CallbackQuery, state: FSMContext):
    sexo = "Masculino" if callback.data == "sex_m" else "Femenino"
    await state.update_data(sexo=sexo)
    await callback.message.edit_text(f"Sexo: {sexo}. Dime tu **peso (kg)**:")
    await state.set_state(OnboardingStates.esperando_peso)

@router.message(OnboardingStates.esperando_peso)
async def process_peso(message: Message, state: FSMContext):
    await state.update_data(peso=message.text)
    await message.answer("Dime tu **talla (cm)**:")
    await state.set_state(OnboardingStates.esperando_talla)

@router.message(OnboardingStates.esperando_talla)
async def process_talla(message: Message, state: FSMContext):
    await state.update_data(talla=message.text)
    await message.answer("¿Padeces alguna **enfermedad crónica**?", reply_markup=get_yes_no_kb("enf"))
    await state.set_state(OnboardingStates.esperando_enfermedades)

@router.callback_query(OnboardingStates.esperando_enfermedades)
async def process_enf(callback: CallbackQuery, state: FSMContext):
    if callback.data == "enf_si":
        await callback.message.edit_text("Por favor, detalla tu condición médica:")
        await state.set_state(OnboardingStates.esperando_detalle_enfermedades)
    else:
        await state.update_data(enfermedades="Ninguna")
        await callback.message.edit_text("¿Tienes alguna **lesión** actual?", reply_markup=get_yes_no_kb("les"))
        await state.set_state(OnboardingStates.esperando_lesiones)

@router.message(OnboardingStates.esperando_detalle_enfermedades)
async def process_det_enf(message: Message, state: FSMContext):
    await state.update_data(enfermedades=message.text)
    await message.answer("⚠️ **DISCLAIMER MÉDICO:** Al tener una condición crónica, te recomendamos consultar con un médico antes de iniciar este plan.\n\n¿Tienes alguna **lesión** actual?", reply_markup=get_yes_no_kb("les"))
    await state.set_state(OnboardingStates.esperando_lesiones)

@router.callback_query(OnboardingStates.esperando_lesiones)
async def process_les(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if callback.data == "les_si":
        await callback.message.edit_text("Detalla tu lesión:")
        await state.set_state(OnboardingStates.esperando_detalle_lesiones)
    else:
        await state.update_data(lesiones="Ninguna")
        if data['sexo'] == "Femenino":
            await callback.message.edit_text("¿Estás en periodo de **embarazo**?", reply_markup=get_yes_no_kb("emb"))
            await state.set_state(OnboardingStates.esperando_embarazo)
        else:
            await state.update_data(embarazo="No aplica")
            await ir_a_nivel(callback.message, state)

@router.message(OnboardingStates.esperando_detalle_lesiones)
async def process_det_les(message: Message, state: FSMContext):
    await state.update_data(lesiones=message.text)
    data = await state.get_data()
    if data['sexo'] == "Femenino":
        await message.answer("¿Estás en periodo de **embarazo**?", reply_markup=get_yes_no_kb("emb"))
        await state.set_state(OnboardingStates.esperando_embarazo)
    else:
        await state.update_data(embarazo="No aplica")
        await ir_a_nivel(message, state)

@router.callback_query(OnboardingStates.esperando_embarazo)
async def process_emb(callback: CallbackQuery, state: FSMContext):
    res = "Sí" if callback.data == "emb_si" else "No"
    await state.update_data(embarazo=res)
    if res == "Sí":
        await callback.message.answer("⚠️ **AVISO:** Este plan debe ser supervisado por tu obstetra.")
    await ir_a_nivel(callback.message, state)

async def ir_a_nivel(message: Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌱 Principiante (0-1 año)", callback_data="lvl_p")],
        [InlineKeyboardButton(text="⚡ Intermedio (1-2 años)", callback_data="lvl_i")],
        [InlineKeyboardButton(text="🏆 Avanzado (3+ años)", callback_data="lvl_a")]
    ])
    await message.answer("¿Cuál es tu **nivel de experiencia**?", reply_markup=kb)
    await state.set_state(OnboardingStates.esperando_nivel)

@router.callback_query(OnboardingStates.esperando_nivel)
async def process_nivel(callback: CallbackQuery, state: FSMContext):
    niveles = {"lvl_p": "Principiante", "lvl_i": "Intermedio", "lvl_a": "Avanzado"}
    nivel = niveles[callback.data]
    await state.update_data(nivel=nivel)
    data = await state.get_data()
    
    # LÓGICA DE RAMIFICACIÓN DE TEST (SPRINT 5)
    edad = data['edad']
    
    if edad >= 60:
        instrucciones = "📋 **Senior Fitness Test:** Realiza el test de levantarse de la silla (30s) y flexión de brazos (30s). Ingresa tus resultados:"
    elif nivel == "Principiante":
        instrucciones = "📋 **Test Básico:** Realiza AMRAP de 60s de: Sentadillas, Flexiones y Plancha. Ingresa resultados (ej: 30, 20, 45s):"
    elif nivel == "Intermedio":
        instrucciones = "📋 **Test Intermedio:** Ingresa tu RM estimado en Sentadilla y Press Banca, o tu puntaje FMS (1-21):"
    else: # Avanzado
        instrucciones = "📋 **Test Avanzado:** Ingresa tu RM real de los 3 grandes (SQ, BP, DL) y tu puntaje FMS:"
        
    await callback.message.edit_text(instrucciones)
    await state.set_state(OnboardingStates.esperando_resultados_test)

@router.message(OnboardingStates.esperando_resultados_test)
async def process_final(message: Message, state: FSMContext):
    await state.update_data(resultados_test=message.text)
    data = await state.get_data()
    
    msg_wait = await message.answer("🚀 Procesando tu perfil clínico y deportivo. Generando Pack...")
    
    try:
        # Generar y enviar documentos
        rutina_buf = generar_pdf_rutina(data)
        rutina_file = BufferedInputFile(rutina_buf.read(), filename="1_Rutina_Personalizada.pdf")
        revista_buf = generar_revista_nutricional(data)
        revista_file = BufferedInputFile(revista_buf.read(), filename="2_Revista_Nutricional.pdf")
        
        await message.answer_document(rutina_file, caption="✅ Tu Plan con Screening Clínico.")
        await message.answer_document(revista_file, caption="📖 Tu Revista Nutricional.")
        await msg_wait.delete()
        await message.answer("¡Anamnesis completada! Revisa tus documentos.")
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("Error al generar el plan.")
    
    await state.clear()

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
