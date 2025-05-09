import os
import logging
import threading
from functools import wraps

from aiohttp import web
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    BotCommand,
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    Filters,
    CallbackContext,
)

# ——— Конфигурация ———
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не задан в окружении")
PORT = int(os.getenv("PORT", 8000))  # Render автоматически ставит этот порт
ALLOWED_USERNAME = "R0FJlan4K"

MENTIONS = [
    "@ROFJlan4K",
    "@hyiablo",
    "@sitiss_amoriss",
    "@Katefak",
    "@Teranixs",
    "@AlSerTim",
]

ASKING_TEXT = 1
pending_announcements = {}

def restricted(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user = update.effective_user
        if not user or user.username != ALLOWED_USERNAME:
            return
        return func(update, context, *args, **kwargs)
    return wrapped

@restricted
def start(update: Update, context: CallbackContext):
    if 'last_msg' in context.chat_data:
        try:
            context.bot.delete_message(update.effective_chat.id, context.chat_data['last_msg'])
        except:
            pass

    msg = update.message.reply_text(
        "Привет! Выбери действие:",
        reply_markup=ReplyKeyboardMarkup(
            [["❗ Создать оповещение"], ["❓ Помощь"]],
            resize_keyboard=True
        )
    )
    context.chat_data['last_msg'] = msg.message_id

@restricted
def help_command(update: Update, context: CallbackContext):
    if 'last_msg' in context.chat_data:
        try:
            context.bot.delete_message(update.effective_chat.id, context.chat_data['last_msg'])
        except:
            pass

    text = (
        "Команды и кнопки:\n"
        "/start — главное меню\n"
        "/help — эта справка\n\n"
        "Кнопки:\n"
        "❗ Создать оповещение — напиши текст, подтвердишь — и всех упомянем"
    )
    msg = update.message.reply_text(text)
    context.chat_data['last_msg'] = msg.message_id

@restricted
def announce_start(update: Update, context: CallbackContext):
    if 'last_msg' in context.chat_data:
        try:
            context.bot.delete_message(update.effective_chat.id, context.chat_data['last_msg'])
        except:
            pass

    msg = update.message.reply_text("Напиши, пожалуйста, текст оповещения:")
    context.chat_data['last_msg'] = msg.message_id
    return ASKING_TEXT

@restricted
def receive_text(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text.strip()
    pending_announcements[chat_id] = text

    if 'last_msg' in context.chat_data:
        try:
            context.bot.delete_message(chat_id, context.chat_data['last_msg'])
        except:
            pass

    preview = update.message.reply_text(
        f"Вот что будет отправлено:\n\n<i>{text}</i>\n\n"
        "Нажми кнопку, чтобы отправить его всем участникам.",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🚀 Оповестить всех", callback_data="notify_all")]]
        ),
        parse_mode="HTML"
    )
    context.chat_data['last_msg'] = preview.message_id
    return ConversationHandler.END

@restricted
def button_notify(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    chat_id = query.message.chat.id

    try:
        context.bot.delete_message(chat_id, query.message.message_id)
    except:
        pass

    text = pending_announcements.pop(chat_id, None)
    if not text:
        return

    full_msg = f"{text}\n\n{' '.join(MENTIONS)}"
    context.bot.send_message(chat_id=chat_id, text=full_msg)

def run_http():
    """Запускаем aiohttp-сервер для health checks."""
    async def health(request):
        return web.Response(text="OK")
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/healthz", health)
    web.run_app(app, host="0.0.0.0", port=PORT)

def main():
    # 1) стартуем HTTP-сервер в фоне
    t = threading.Thread(target=run_http, daemon=True)
    t.start()

    # 2) настраиваем и запускаем бот
    updater = Updater(TOKEN, use_context=True)
    updater.bot.delete_webhook(drop_pending_updates=True)

    dp = updater.dispatcher
    updater.bot.set_my_commands([
        BotCommand("start", "Показать главное меню"),
        BotCommand("help", "Справка по функциям"),
    ])

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("announce", announce_start),
            MessageHandler(Filters.regex("^❗ Создать оповещение$"), announce_start),
        ],
        states={ASKING_TEXT: [
            MessageHandler(Filters.text & ~Filters.command, receive_text)
        ]},
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(conv)
    dp.add_handler(CallbackQueryHandler(button_notify, pattern="^notify_all$"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: None))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
