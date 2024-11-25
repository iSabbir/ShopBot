import inspect
from aiogram import Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from callbacks import AdminAnnouncementCallback, AnnouncementType
from services.admin import AdminService
from utils.custom_filters import AdminIdFilter
from utils.localizator import BotEntity, Localizator
from utils.new_items_manager import NewItemsManager

admin_announcement_router = Router()


class AdminAnnouncementStates(StatesGroup):
    announcement_msg = State()


class AdminAnnouncementsConstants:
    confirmation_builder = InlineKeyboardBuilder()
    confirmation_builder.button(text=Localizator.get_text(BotEntity.COMMON, "confirm"),
                                callback_data=AdminAnnouncementCallback.create(3))
    confirmation_builder.button(text=Localizator.get_text(BotEntity.COMMON, "cancel"),
                                callback_data=AdminAnnouncementCallback.create(0))


async def announcement_menu(callback: CallbackQuery):
    msg, kb_builder = await AdminService.get_announcement_menu()
    await callback.message.edit_text(text=msg, reply_markup=kb_builder.as_markup())


async def send_everyone(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(Localizator.get_text(BotEntity.ADMIN, "receive_msg_request"))
    await state.set_state(AdminAnnouncementStates.announcement_msg)


@admin_announcement_router.message(AdminIdFilter(), StateFilter(AdminAnnouncementStates.announcement_msg))
async def receive_admin_message(message: Message, state: FSMContext):
    await state.clear()
    if message.text == "cancel":
        await message.answer(text=Localizator.get_text(BotEntity.ADMIN, "canceled"))
    else:
        await message.copy_to(message.chat.id,
                              reply_markup=AdminAnnouncementsConstants.confirmation_builder.as_markup())


async def send_generated_msg(callback: CallbackQuery):
    unpacked_cb = AdminAnnouncementCallback.unpack(callback.data)
    if unpacked_cb.type_of_announcement == AnnouncementType.RESTOCKING:
        msg = await NewItemsManager.generate_restocking_message()
        await callback.message.answer(msg, reply_markup=AdminAnnouncementsConstants.confirmation_builder.as_markup())
    else:
        msg = await NewItemsManager.generate_in_stock_message()
        await callback.message.answer(msg, reply_markup=AdminAnnouncementsConstants.confirmation_builder.as_markup())


async def send_confirmation(callback: CallbackQuery):
    msg = await AdminService.send_announcement(callback)
    if callback.message.caption:
        await callback.message.delete()
        await callback.message.answer(text=msg)
    elif callback.message.text:
        await callback.message.edit_text(text=msg)


@admin_announcement_router.callback_query(AdminIdFilter(), AdminAnnouncementCallback.filter())
async def admin_announcement_navigation(callback: CallbackQuery, state: FSMContext,
                                        callback_data: AdminAnnouncementCallback):
    current_level = callback_data.level

    levels = {
        0: announcement_menu,
        1: send_everyone,
        2: send_generated_msg,
        3: send_confirmation
    }

    current_level_function = levels[current_level]
    if inspect.getfullargspec(current_level_function).annotations.get("state") == FSMContext:
        await current_level_function(callback, state)
    else:
        await current_level_function(callback)
