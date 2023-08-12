import re
from telegram.ext import ContextTypes
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from database import crear_nuevo_grupo, eliminar_un_grupo
from database import obtener_todos_grupos
from database import obtener_todos_canales
from database import obtener_grupo
from database import agregar_canal_en_grupo
from database import eliminar_canal_del_grupo
from paginator import Paginator
from config import ADMINS


async def seleccionar_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    canal_id, grupo_id, page_number = re.findall(
        r"(-?\d{8,}|\d+)", update.callback_query.data
    )

    agregar_canal_en_grupo(int(grupo_id), int(canal_id))

    await editar_mesaje(update, grupo_id, page_number)


async def deseleccionar_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    canal_id, grupo_id, page_number = re.findall(
        r"(-?\d{8,}|\d+)", update.callback_query.data
    )

    eliminar_canal_del_grupo(int(grupo_id), int(canal_id))

    await editar_mesaje(update, grupo_id, page_number)


async def ver_canales_para_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    grupo_id, page_number = re.findall(r"(\d+)", update.callback_query.data)

    await editar_mesaje(update, grupo_id, page_number)


async def editar_mesaje(update, grupo_id, page_number):
    grupo, _ = obtener_grupo(int(grupo_id))

    canales_del_grupo = [ch.id for ch in grupo.canales]

    paginator = Paginator(obtener_todos_canales())
    page = paginator.page(int(page_number))

    markup = []

    if not page.data:
        await update.callback_query.answer(
            "ℹ️No hay canales agregados", show_alert=True
        )
        return

    for canal in page.data:
        if canal.id in canales_del_grupo:
            markup.append(
                [
                    InlineKeyboardButton(
                        f"☑️ {canal.nombre}",
                        callback_data=f"eliminar-{canal.id}-en-{grupo_id}|{page_number}",
                    )
                ]
            )
        else:
            markup.append(
                [
                    InlineKeyboardButton(
                        f"{canal.nombre}",
                        callback_data=f"agregar-{canal.id}-en-{grupo_id}|{page_number}",
                    )
                ]
            )

    button_next = InlineKeyboardButton(
        text="➡️ siguiente",
        callback_data=f"navegar-para-agregar{grupo_id}|{page.next_page}",
    )

    button_back = InlineKeyboardButton(
        text="⬅️ atrás",
        callback_data=f"navegar-para-agregar{grupo_id}|{page.prev_page}",
    )

    if page.has_next_page and page.has_prev_page:
        markup.append([button_back, button_next])

    elif page.has_next_page:
        markup.append([button_next])

    elif page.has_prev_page:
        markup.append([button_back])

    markup.append(
        [InlineKeyboardButton(text="🔙 regresar", callback_data=f"grupo-{grupo_id}")]
    )

    await update.callback_query.edit_message_text(
        f"📋 Seleccione los canales que desea agregar en <b>{grupo.nombre}</b>\n\n📄 página {page.number}",
        reply_markup=InlineKeyboardMarkup(markup),
        parse_mode="html",
    )


async def ver_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    id_group = update.callback_query.data.replace("grupo-", "")

    if id_group == "todos":
        """Ver la lista de todos los canales"""
        canales = obtener_todos_canales()

        if not canales:
            await update.callback_query.answer(
                "ℹ️No hay canales agregados", show_alert=True
            )
            return

        paginator = Paginator(canales)
        page = paginator.page(1)

        markup = []

        for canal in page.data:
            canal_nombre = canal[1]

            markup.append(
                [InlineKeyboardButton(canal_nombre, callback_data="solo-lectura")]
            )

        if page.has_next_page:
            markup.append(
                [
                    InlineKeyboardButton(
                        text="➡️ siguiente",
                        callback_data="navegar-grupo-todos|2",
                    )
                ]
            )

        markup.append(
            [InlineKeyboardButton(text="🔙 regresar", callback_data="regresar")]
        )

        await update.callback_query.edit_message_text(
            f"📋Nombre del grupo: <b>TODOS</b>\n\n📄 página {page.number}",
            reply_markup=InlineKeyboardMarkup(markup),
            parse_mode="html",
        )

    else:
        grupo, _ = obtener_grupo(int(id_group))

        markup = [
            [
                InlineKeyboardButton(
                    "agregar canal", callback_data=f"navegar-para-agregar{id_group}|1"
                )
            ],
            [
                InlineKeyboardButton(
                    "ver canales", callback_data=f"navegar-grupo-{id_group}|1"
                )
            ],
            [InlineKeyboardButton(text="🔙 regresar", callback_data="regresar")],
        ]

        await update.callback_query.edit_message_text(
            f"🚩Opciones para el grupo: <b>{grupo.nombre}</b>",
            parse_mode="html",
            reply_markup=InlineKeyboardMarkup(markup),
        )


async def navegar_grupos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navegar entre los canales que pertenecen a los grupos"""
    numbers = re.findall(r"(\d+)", update.callback_query.data)

    if len(numbers) == 1:  # solo hay un número cuando se trata del grupo general
        grupo_id = "todos"
        page_number = int(numbers[0])
        nombre_grupo = "TODOS"
        canales = obtener_todos_canales()

    else:
        grupo_id = numbers[0]
        page_number = int(numbers[1])
        grupo, canales = obtener_grupo(int(grupo_id))
        nombre_grupo = grupo.nombre

    if not canales:
        await update.callback_query.answer(
            "ℹ️Este grupo no posee canales.", show_alert=True
        )
        return

    paginator = Paginator(canales)

    page = paginator.page(page_number)

    markup = []

    for canal in page.data:
        canal_nombre = canal[1]

        markup.append(
            [InlineKeyboardButton(canal_nombre, callback_data="solo-lectura")]
        )

    button_next = InlineKeyboardButton(
        text="➡️ siguiente", callback_data=f"navegar-grupo-{grupo_id}|{page.next_page}"
    )

    button_back = InlineKeyboardButton(
        text="⬅️ atrás", callback_data=f"navegar-grupo-{grupo_id}|{page.prev_page}"
    )

    if page.has_next_page and page.has_prev_page:
        markup.append([button_back, button_next])

    elif page.has_next_page:
        markup.append([button_next])

    elif page.has_prev_page:
        markup.append([button_back])

    markup.append(
        [InlineKeyboardButton(text="🔙 regresar", callback_data=f"grupo-{grupo_id}")]
    )

    await update.callback_query.edit_message_text(
        f"📋Nombre del grupo: <b>{nombre_grupo}</b>\n\n📄 página {page.number}",
        reply_markup=InlineKeyboardMarkup(markup),
        parse_mode="html",
    )


async def crear_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in ADMINS:
        if update.message.text == "/addgroup":
            await update.message.reply_text(
                (
                    "ℹ️ Para agregar un grupo debe usar el comando de esta"
                    " forma: <code>/addgroup Grupo Favorito</code>"
                ),
                parse_mode="html",
            )
            return

        nombre_del_grupo = update.message.text.replace("/addgroup ", "")

        crear_nuevo_grupo(nombre_del_grupo)

        await update.message.reply_text("✅ grupo creado")


async def eliminar_grupo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in ADMINS:
        if update.message.text == "/delgroup":
            await update.message.reply_text(
                (
                    "ℹ️ Para eliminar un grupo debe usar el comando de esta"
                    " forma: <code>/delgroup Grupo Favorito</code>"
                ),
                parse_mode="html",
            )
            return

        nombre_del_grupo = update.message.text.replace("/delgroup ", "")

        eliminar_un_grupo(nombre_del_grupo)

        await update.message.reply_text("✅ grupo eliminado")


async def regresar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name

    grupos = obtener_todos_grupos()

    markup = [[InlineKeyboardButton("TODOS", callback_data="grupo-todos")]]

    for grupo in grupos:
        btn = InlineKeyboardButton(grupo.nombre, callback_data=f"grupo-{grupo.id}")
        markup.append([btn])

    await update.callback_query.edit_message_text(
        f"👋 Bienvenido {name} reenvíe un mensaje para programarlo",
        reply_markup=InlineKeyboardMarkup(markup),
    )
