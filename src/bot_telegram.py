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

class OnboardingStates(StatesGroup):
    esperando_objetivo = State()
    esperando_nivel = State()
    esperando_peso = State()
    esperando_altura = State()

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Quemar Grasa", callback_data="obj_quemar")],
        [InlineKeyboardButton(text="💪 Ganar Músculo", callback_data="obj_ganar")]
    ])
    await message.answer("¡Bienvenido a **RUTINATOR**! ¿Cuál es tu objetivo?", reply_markup=kb)
    await state.set_state(OnboardingStates.esperando_objetivo)

@router.callback_query(OnboardingStates.esperando_objetivo)
async def process_obj(callback: CallbackQuery, state: FSMContext):
    obj = "Quemar Grasa" if callback.data == "obj_quemar" else "Ganar Músculo"
    await state.update_data(objetivo=obj, atleta=callback.from_user.full_name)
    await callback.message.edit_text(f"Objetivo: {obj}. Dime tu peso (kg):")
    await state.set_state(OnboardingStates.esperando_peso)

@router.message(OnboardingStates.esperando_peso)
async def process_peso(message: Message, state: FSMContext):
    await state.update_data(peso=message.text)
    await message.answer("Dime tu altura (cm):")
    await state.set_state(OnboardingStates.esperando_altura)

@router.message(OnboardingStates.esperando_altura)
async def process_final(message: Message, state: FSMContext):
    await state.update_data(altura=message.text)
    data = await state.get_data()
    
    msg_wait = await message.answer("🚀 Preparando tu Pack de Transformación...")
    
    try:
        rutina_buf = generar_pdf_rutina(data)
        rutina_file = BufferedInputFile(rutina_buf.read(), filename="1_Rutina_Entrenamiento.pdf")
        
        revista_buf = generar_revista_nutricional(data)
        revista_file = BufferedInputFile(revista_buf.read(), filename="2_Revista_Nutricional.pdf")
        
        await message.answer_document(rutina_file, caption="📋 Tu Plan de Entrenamiento.")
        await message.answer_document(revista_file, caption="📖 Tu Revista Nutricional.")
        await msg_wait.delete()
        
    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("Hubo un error. Intenta de nuevo.")
    
    await state.clear()

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
