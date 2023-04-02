import re
import uuid

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)
from colorama import Fore
from colorama import init

from config import TOKEN, ADMINS

from database import Base
from database import engine

from database import agregar_nuevo_canal
from database import seleccionar_canales
from database import eliminar_canal
from database import gurdar_msg_programado
from database import obtener_msg_programado
from database import actualizar_mensaje_alerta
from database import obtener_mensaje_alerta

from aps import scheduler
from aps import programar_reenvio

STATE_1, STATE_2, STATE_3, STATE_4 = range(4)

init(autoreset=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """inicia la interacción con el bot"""

    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if user_id in ADMINS:

        await update.message.reply_text(
            f"👋 Bienvenido {name} reenvíe un mensaje para programarlo"
        )

    else:

        msg = obtener_mensaje_alerta()

        await update.message.reply_text(
            text=msg.replace("$NAME", name),
            parse_mode="html",
        )


async def agregar_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """agrega un nuevo canal"""

    user_id = update.effective_user.id

    if user_id in ADMINS:

        chat_id = update.message.text.replace("/add ", "")

        try:
            bot = context.bot

            chat = await bot.get_chat(int(chat_id))

            chat_id = chat.id
            nombre = chat.title

            try:
                agregar_nuevo_canal(chat_id, nombre)

            except:

                await update.message.reply_text(f"✖️ el id {chat_id} ya existe")
                return

            await update.message.reply_text("✅ guardado")

        except:

            await update.message.reply_text(f"✖️ el id {chat_id} no fue encontrado")


async def borrar_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """elimina un canal de la bd"""

    user_id = update.effective_user.id

    if user_id in ADMINS:

        chat_id = update.message.text.replace("/del ", "")

        try:

            eliminar_canal(int(chat_id))

            await update.message.reply_text("✅ eliminado")
        except:

            await update.message.reply_text(f"✖️ el id {chat_id} no fue encontrado")


async def obtener_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """obtener datos de los mensages a reenviar"""

    user_id = update.effective_user.id

    if user_id in ADMINS:

        msg_id = update.message.forward_from_message_id

        try:

            chat_id = update.message.forward_from_chat.id

        except AttributeError:

            await update.message.reply_text(
                text="✖️ no se pudo obtener el id del autor del mensaje",
                parse_mode="html",
            )

            return

        context.user_data["msg_id"] = msg_id
        context.user_data["chat_id"] = chat_id

        await update.message.reply_text(
            text="⏰ Ingrese la fecha para reenviar el mensaje\n\nEjemplo: <code>5-03-2023 13:30</code>",
            parse_mode="html",
        )

        return STATE_1


async def fecha_reenvio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """obtener fecha a reenviar"""

    user_id = update.effective_user.id

    if user_id in ADMINS:

        text = update.message.text

        if text == "/cancel":

            await cancel(update, context)

            return ConversationHandler.END

        pattern_regex = r"^[0-9]{1,2}-[0-9]{1,2}-20[0-9][0-9] [0-9]{1,2}:[0-9]{1,2}$"

        if re.match(pattern_regex, text):

            context.user_data["reenvio"] = text

            await update.message.reply_text(
                text="⏰ Ingrese los minutos que debe durar el mensaje reenviado en los canales"
            )

            return STATE_2

        await update.message.reply_text(
            text=f"✖️ formato de fecha <code>{text}</code> no es correcto",
            parse_mode="html",
        )


async def fecha_eliminacion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """obtener fecha a reenviar"""

    user_id = update.effective_user.id

    if user_id in ADMINS:

        text = update.message.text

        if text == "/cancel":

            await cancel(update, context)

            return ConversationHandler.END

        if re.match(r"[0-9]{1,4}", text):

            context.user_data["eliminar"] = int(text)

            canales = seleccionar_canales()

            buttons = []
            for canal in canales:
                buttons.append(
                    [InlineKeyboardButton(text=canal[1], callback_data=str(canal[0]))]
                )

            buttons.append(
                [InlineKeyboardButton(text="✅ aceptar", callback_data="aceptar")]
            )

            if canales == []:

                await update.message.reply_text(
                    text="✖️ debe de agregar al menos 1 canal"
                )

                return

            await update.message.reply_text(
                text="📣 Seleccione los canales",
                reply_markup=InlineKeyboardMarkup(buttons),
            )

            return STATE_3

        await update.message.reply_text(
            text=f"✖️ formato <code>{text}</code> no es correcto",
            parse_mode="html",
        )


async def seleccionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """seleccionar los canales para publicar el mensaje"""

    data = update.callback_query.data

    canales = seleccionar_canales()

    try:
        if data in context.user_data["channels"]:

            context.user_data["channels"] = context.user_data["channels"].replace(
                data, ""
            )

        else:
            context.user_data["channels"] += f",{data}"

    except KeyError:

        context.user_data["channels"] = data

    buttons = []

    for canal in canales:
        channel_name = canal[1]
        if canal[0] in [
            int(id) for id in context.user_data["channels"].split(",") if id != ""
        ]:
            channel_name = "☑️ " + canal[1]

        buttons.append(
            [InlineKeyboardButton(text=channel_name, callback_data=str(canal[0]))]
        )

    buttons.append([InlineKeyboardButton(text="✅ aceptar", callback_data="aceptar")])

    await update.callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def aceptar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """seleccionar los canales para publicar el mensaje"""

    await update.callback_query.edit_message_text(
        text="Guardar mensaje programado",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="✅", callback_data="✅"),
                    InlineKeyboardButton(text="❌", callback_data="❌"),
                ]
            ]
        ),
    )

    return STATE_4


async def confirmar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """confirmar programación"""

    data = update.callback_query.data

    if data == "✅":

        await update.callback_query.edit_message_text(text="✅ Reenvío programado")

        msg_data = context.user_data

        msg_id = msg_data.get("msg_id")
        chat_id = msg_data.get("chat_id")
        fecha_reenvio = msg_data.get("reenvio")
        duracion = msg_data.get("eliminar")
        list_chats = msg_data.get("channels")

        id = str(uuid.uuid4())

        # gurdar mensaje programado en la BD
        gurdar_msg_programado(id, msg_id, chat_id, fecha_reenvio, duracion, list_chats)

        # programamos el reenvio
        programar_reenvio(id)

    else:

        await update.callback_query.edit_message_text(text="❌ Reenvío cancelado")

    return ConversationHandler.END


async def listar_mensajes_programados(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """listar los mensajes programados"""

    user_id = update.effective_user.id

    if user_id in ADMINS:
        jobs = scheduler.get_jobs()

        buttons = []

        for job in jobs:

            job_id = job.id

            data = obtener_msg_programado(job_id)

            fecha = data[2]

            chat_id = str(data[0]).replace("-100", "")
            msg_url = f"https://t.me/c/{chat_id}/{data[1]}"

            buttons.append(
                [
                    InlineKeyboardButton(text=f"{fecha}", url=msg_url),
                    InlineKeyboardButton(text="🗑", callback_data=job_id),
                ]
            )

        if buttons == []:

            await update.message.reply_text(text="💬 No hay mensajes programados")

            return

        await update.message.reply_text(
            text="💬 Mensajes programados", reply_markup=InlineKeyboardMarkup(buttons)
        )


async def eliminar_mensajes_programados(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    """eliminar mensajes programados"""

    data = update.callback_query.data

    scheduler.remove_job(job_id=data)

    jobs = scheduler.get_jobs()

    buttons = []

    for job in jobs:

        job_id = job.id

        data = obtener_msg_programado(job_id)

        fecha = data[2]

        chat_id = str(data[0]).replace("-100", "")
        msg_url = f"https://t.me/c/{chat_id}/{data[1]}"

        buttons.append(
            [
                InlineKeyboardButton(text=f"{fecha}", url=msg_url),
                InlineKeyboardButton(text="🗑", callback_data=job_id),
            ]
        )

    if buttons == []:

        await update.callback_query.edit_message_text(
            text="💬 No hay mensajes programados"
        )

        return

    await update.callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def obtener_id_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):

    chat_id = update.effective_chat.id

    await update.message.reply_text(
        text=f"El ID de este chat es: <code>{chat_id}</code>", parse_mode="html"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    await update.message.reply_text("🟢 Se ha cancelado la operación ")

    return ConversationHandler.END


async def agregar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:

    user_id = update.effective_user.id

    if user_id in ADMINS:

        text = update.message.text

        new_msg = text.replace("/msg ", "")

        try:

            await update.message.reply_text(
                text=f"🟢 Mensaje actualizado\n\n{new_msg}", parse_mode="html"
            )

            actualizar_mensaje_alerta(new_msg)

        except:

            await update.message.reply_text(text=f"🔴 Mensaje con mal formato")


def main():

    scheduler.start()

    Base.metadata.create_all(engine)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", agregar_canal))
    app.add_handler(CommandHandler("del", borrar_canal))
    app.add_handler(CommandHandler("id", obtener_id_grupo))
    app.add_handler(CommandHandler("check", listar_mensajes_programados))
    app.add_handler(CommandHandler("msg", agregar_mensaje))

    app.add_handler(
        CallbackQueryHandler(
            pattern=r"^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$",
            callback=eliminar_mensajes_programados,
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.FORWARDED, obtener_msg)],
            states={
                STATE_1: [MessageHandler(filters.TEXT, fecha_reenvio)],
                STATE_2: [MessageHandler(filters.TEXT, fecha_eliminacion)],
                STATE_3: [
                    CallbackQueryHandler(pattern=r"^-?[0-9]+$", callback=seleccionar),
                    CallbackQueryHandler(pattern=r"^aceptar$", callback=aceptar),
                ],
                STATE_4: [
                    CallbackQueryHandler(pattern=r"^(✅|❌)$", callback=confirmar),
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
    )

    app.run_polling()


if __name__ == "__main__":
    print(Fore.GREEN + "✔️", "🤖 bot activo")
    main()
