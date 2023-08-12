import re
import uuid
from datetime import datetime

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

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

from database import crear_nuevo_canal
from database import eliminar_canal
from database import crear_msg_programado
from database import obtener_msg_programado
from database import actualizar_mensaje_bienvenida
from database import obtener_mensaje_bienvenida
from database import obtener_todos_grupos

from aps import scheduler
from aps import programar_reenvio

from groups import crear_grupo, eliminar_grupo
from groups import ver_info
from groups import regresar
from groups import navegar_grupos
from groups import ver_canales_para_agregar
from groups import seleccionar_canal
from groups import deseleccionar_canal

from utils import modify_data

STATE_1, STATE_2, STATE_3, STATE_4 = range(4)

init(autoreset=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """inicia la interacción con el bot"""

    user_id = update.effective_user.id
    name = update.effective_user.first_name

    if user_id in ADMINS:
        await context.bot.set_my_commands(
            commands=[
                BotCommand("start", "iniciar el bot"),
                BotCommand("add", "agregar canal"),
                BotCommand("del", "eliminar canal"),
                BotCommand("id", "obtener id del grupo"),
                BotCommand("check", "ver mensajes programados"),
                BotCommand("msg", "establecer mensaje de bienvenida"),
                BotCommand("addgroup", "crear un grupo"),
                BotCommand("delgroup", "eliminar un grupo"),
                BotCommand("cancel", "cancelar"),
            ],
            language_code="es",
        )

        grupos = obtener_todos_grupos()

        markup = [[InlineKeyboardButton("TODOS", callback_data="grupo-todos")]]

        for grupo in grupos:
            btn = InlineKeyboardButton(grupo.nombre, callback_data=f"grupo-{grupo.id}")
            markup.append([btn])

        await update.message.reply_text(
            f"👋 Bienvenido {name} reenvíe un mensaje para programarlo",
            reply_markup=InlineKeyboardMarkup(markup),
        )

    else:
        msg = obtener_mensaje_bienvenida()

        await update.message.reply_text(
            text=msg.replace("$NAME", name),
            parse_mode="html",
        )


async def agregar_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in ADMINS:
        if update.message.text == "/add":
            await update.message.reply_text(
                (
                    "ℹ️ Para agregar un canal debe usar el comando de esta "
                    "forma: <code>/add -1001234567</code>"
                ),
                parse_mode="html",
            )
            return

        chat_id = update.message.text.replace("/add ", "")

        try:
            bot = context.bot

            chat = await bot.get_chat(int(chat_id))

            chat_id = chat.id
            nombre = chat.title

            try:
                crear_nuevo_canal(chat_id, nombre)

            except:
                await update.message.reply_text(
                    f"✖️ el canal con id <code>{chat_id}</code> ya fue registrado.",
                    parse_mode="html",
                )
                return

            await update.message.reply_text("✅ guardado")

        except:
            await update.message.reply_text(
                (
                    "✖️ Primero asegúrate que el bot es administrador "
                    f"en el canal con id <code>{chat_id}</code> y luego intente de nuevo."
                ),
                parse_mode="html",
            )


async def borrar_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in ADMINS:
        if update.message.text == "/del":
            await update.message.reply_text(
                (
                    "ℹ️ Para borrar un canal debe usar el comando de esta "
                    "forma: <code>/del -1001234567</code>"
                ),
                parse_mode="html",
            )
            return

        chat_id = update.message.text.replace("/del ", "")

        try:
            if eliminar_canal(int(chat_id)):
                await update.message.reply_text("✅ eliminado")
                return

            await update.message.reply_text(
                f"✖️ el canal con id <code>{chat_id}</code> no fue encontrado en el registro.",
                parse_mode="html",
            )

        except Exception as err:
            print(err)
            await update.message.reply_text(
                f"✖️ el id <code>{chat_id}</code> no es un id válido.",
                parse_mode="html",
            )


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
            text=(
                "⏰ Ingrese la fecha para reenviar el mensaje\n\n"
                "(día-mes-año horas:minutos)\nEjemplo: "
                f"<code>{datetime.now().strftime('%d-%m-%Y %H:%M')}</code>"
            ),
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

        pattern_regex = r"^(0[1-9]|1[0-9]|2[0-9]|3[0-1])-(0[1-9]|1[0-2])-20[0-9][0-9] [0-9]{1,2}:[0-9]{1,2}$"

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

        if re.match(r"^[0-9]{1,4}$", text):
            context.user_data["eliminar"] = int(text)

            # Obtener todos los grupos

            grupos = obtener_todos_grupos()

            markup = []

            # Agregar grupo TODOS

            markup.append(
                [
                    InlineKeyboardButton(
                        text=f"TODOS",
                        callback_data=f"seleccionar-grupo-todos",
                    )
                ]
            )

            for grupo in grupos:
                markup.append(
                    [
                        InlineKeyboardButton(
                            text=grupo.nombre,
                            callback_data=f"seleccionar-grupo-{grupo.id}",
                        )
                    ]
                )

            await update.message.reply_text(
                text="📣 Seleccione los grupos",
                reply_markup=InlineKeyboardMarkup(markup),
            )

            return STATE_3

        await update.message.reply_text(
            text=(
                "✖️ Debe enviar solo la cantidad de minutos que durará "
                "la publicación puede ser de 1 minuto a 9999 minutos."
            ),
            parse_mode="html",
        )


async def seleccionar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """seleccionar los canales para publicar el mensaje"""

    data = update.callback_query.data.replace("seleccionar-grupo-", "")

    context.user_data["groups"] = modify_data(context.user_data.get("groups"), data)

    grupos = obtener_todos_grupos()

    markup = []

    # Agregar grupo TODOS
    if "todos" in context.user_data["groups"]:
        markup.append(
            [
                InlineKeyboardButton(
                    text=f"☑️ TODOS",
                    callback_data=f"seleccionar-grupo-todos",
                )
            ]
        )
    else:
        markup.append(
            [
                InlineKeyboardButton(
                    text=f"TODOS",
                    callback_data=f"seleccionar-grupo-todos",
                )
            ]
        )

    for grupo in grupos:
        if str(grupo.id) in context.user_data["groups"]:
            markup.append(
                [
                    InlineKeyboardButton(
                        text=f"☑️ {grupo.nombre}",
                        callback_data=f"seleccionar-grupo-{grupo.id}",
                    )
                ]
            )

        else:
            markup.append(
                [
                    InlineKeyboardButton(
                        text=grupo.nombre,
                        callback_data=f"seleccionar-grupo-{grupo.id}",
                    )
                ]
            )

    markup.append([InlineKeyboardButton(text="✅ aceptar", callback_data="aceptar")])

    await update.callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(markup),
    )


async def aceptar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """seleccionar los canales para publicar el mensaje"""

    await update.callback_query.edit_message_text(
        text="Guardar mensaje programado ?",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(text="si ✅", callback_data="✅"),
                    InlineKeyboardButton(text="no ❌", callback_data="❌"),
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

        msg_id = context.user_data.get("msg_id")
        chat_id = context.user_data.get("chat_id")
        fecha_reenvio = context.user_data.get("reenvio")
        duracion = context.user_data.get("eliminar")
        list_groups = context.user_data.get("groups")

        id = str(uuid.uuid4())

        # gurdar mensaje programado en la BD
        crear_msg_programado(id, msg_id, chat_id, fecha_reenvio, duracion, list_groups)

        # programamos el reenvio
        programar_reenvio(id)

        if context.user_data["groups"]:
            del context.user_data["groups"]

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

            data, _ = obtener_msg_programado(job_id)

            if data is None:
                continue

            fecha = data.fecha_reenvio

            chat_id = str(data.chat_id).replace("-100", "")
            msg_url = f"https://t.me/c/{chat_id}/{data.chat_id}"

            buttons.append(
                [
                    InlineKeyboardButton(text=f"{fecha}", url=msg_url),
                    InlineKeyboardButton(text="🗑", callback_data=job_id),
                ]
            )

        if not buttons:
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

    try:
        scheduler.remove_job(job_id=data)

        jobs = scheduler.get_jobs()

        buttons = []

        for job in jobs:
            job_id = job.id

            data, _ = obtener_msg_programado(job_id)

            if data is None:
                continue

            fecha = data.fecha_reenvio

            chat_id = str(data.chat_id).replace("-100", "")
            msg_url = f"https://t.me/c/{chat_id}/{data.msg_id}"

            buttons.append(
                [
                    InlineKeyboardButton(text=f"{fecha}", url=msg_url),
                    InlineKeyboardButton(text="🗑", callback_data=job_id),
                ]
            )

        if not buttons:
            await update.callback_query.edit_message_text(
                text="💬 No hay mensajes programados"
            )

            return

        await update.callback_query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(buttons)
        )

    except Exception as err:
        print(err)
        await update.callback_query.answer(
            text="💬 El mensaje que intenta borrar ya no existe.", show_alert=True
        )


async def obtener_id_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    await update.message.reply_text(
        text=f"El ID de este chat es: <code>{chat_id}</code>", parse_mode="html"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🟢 Se ha cancelado la operación ")
    if context.user_data["groups"]:
        del context.user_data["groups"]

    return ConversationHandler.END


async def agregar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    if user_id in ADMINS:
        text = update.message.text

        if update.message.text == "/msg":
            await update.message.reply_text(
                (
                    "ℹ️ Para establecer un mensaje de bienvenida debe usar el comando"
                    " de esta forma: <code>/msg 🤖 Saludos humano $NAME!</code>\n\n$NAME"
                    " se cambiará por el nombre del usuario."
                ),
                parse_mode="html",
            )
            return

        new_msg = text.replace("/msg ", "")

        try:
            await update.message.reply_text(
                text=f"🟢 Mensaje actualizado\n\n{new_msg}", parse_mode="html"
            )

            actualizar_mensaje_bienvenida(new_msg)

        except:
            await update.message.reply_text(text="🔴 Mensaje con mal formato")


async def solo_lectura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer("ℹ️ Solo lectura.", show_alert=True)


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
    app.add_handler(CommandHandler("addgroup", crear_grupo))
    app.add_handler(CommandHandler("delgroup", eliminar_grupo))

    app.add_handler(
        CallbackQueryHandler(
            pattern=r"^[a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12}$",
            callback=eliminar_mensajes_programados,
        )
    )

    # grupos
    app.add_handler(CallbackQueryHandler(pattern=r"^regresar$", callback=regresar))
    app.add_handler(
        CallbackQueryHandler(pattern=r"^grupo-(todos|\d+)$", callback=ver_info)
    )

    app.add_handler(
        CallbackQueryHandler(
            pattern=r"^navegar-grupo-(\d+|todos)\|\d+$", callback=navegar_grupos
        )
    )
    app.add_handler(
        CallbackQueryHandler(pattern=r"^solo-lectura$", callback=solo_lectura)
    )
    app.add_handler(
        CallbackQueryHandler(
            pattern=r"^navegar-para-agregar\d+\|\d+$", callback=ver_canales_para_agregar
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            pattern=r"^agregar--?\d+-en-\d+\|\d+$", callback=seleccionar_canal
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            pattern=r"^eliminar--?\d+-en-\d+\|\d+$", callback=deseleccionar_canal
        )
    )

    app.add_handler(
        ConversationHandler(
            entry_points=[MessageHandler(filters.FORWARDED, obtener_msg)],
            states={
                STATE_1: [MessageHandler(filters.TEXT, fecha_reenvio)],
                STATE_2: [MessageHandler(filters.TEXT, fecha_eliminacion)],
                STATE_3: [
                    CallbackQueryHandler(
                        pattern=r"^seleccionar-grupo-(\d+|todos)$", callback=seleccionar
                    ),
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
