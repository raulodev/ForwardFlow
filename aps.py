import asyncio
import logging

from datetime import timedelta
from datetime import datetime
from telegram import Bot

from apscheduler.schedulers.background import BackgroundScheduler
from database import obtener_msg_programado
from config import DATABASE_URL, TOKEN, ADMINS


job_defaults = {"misfire_grace_time": 1000}

scheduler = BackgroundScheduler(job_defaults=job_defaults, timezone="America/Caracas")
scheduler.add_jobstore("sqlalchemy", url=DATABASE_URL)


def enviar(id: str, delete_date: datetime):
    mensaje, canales = obtener_msg_programado(id)

    async def run():
        bot = Bot(TOKEN)

        if isinstance(canales[0], tuple):
            list_channels = [canal[0] for canal in canales]
        else:
            list_channels = [canal.id for canal in canales]

        # cada mensaje programado a eliminarse
        # tiene una diferencia de 3 segundos
        interval = 0
        for canal in list_channels:
            try:
                msg = await bot.forward_message(
                    chat_id=canal,
                    from_chat_id=mensaje.chat_id,
                    message_id=mensaje.msg_id,
                )

                msg_id = msg.message_id
                chat_id = canal

                await bot.pin_chat_message(chat_id=chat_id, message_id=msg_id)

                await bot.delete_message(chat_id=chat_id, message_id=msg_id + 1)

                # programar eliminación
                scheduler.add_job(
                    eliminar,
                    "date",
                    run_date=delete_date + timedelta(seconds=interval),
                    args=[msg_id, chat_id],
                )

            except:
                for admin in ADMINS:
                    try:
                        await bot.send_message(
                            chat_id=admin,
                            text=f"⚠️ No puedo reenviar el mensaje al canal con id {canal}.",
                            parse_mode="html",
                        )

                    except:
                        logging.warning(
                            f"El admin con id {admin} no ha iniciado el bot."
                        )

            interval += 3

    asyncio.run(run())


def eliminar(msg_id: int, chat_id: int):
    async def run(msg_id, chat_id):
        bot = Bot(TOKEN)

        try:
            await bot.delete_message(chat_id, message_id=msg_id)

        except:
            for admin in ADMINS:
                chat_id = str(chat_id).replace("-100", "")

                await bot.send_message(
                    chat_id=admin,
                    text=(
                        f"⚠️ No se pudo eliminar <a href='https://t.me/c/{chat_id}/{msg_id}'>"
                        "este mensaje</a> del canal."
                    ),
                    parse_mode="html",
                )

    asyncio.run(run(msg_id, chat_id))


def programar_reenvio(id_msg_prg: str):
    # seleccionamos datos del mensaje
    mensaje, _ = obtener_msg_programado(id_msg_prg)

    fecha_reenvio = mensaje.fecha_reenvio.replace("-", " ").replace(":", " ").split()
    fecha_reenvio = [int(num) for num in fecha_reenvio]

    year = fecha_reenvio[2]
    mes = fecha_reenvio[1]
    dia = fecha_reenvio[0]
    hour = fecha_reenvio[3]
    minute = fecha_reenvio[4]

    duracion = mensaje.duracion

    send_date = datetime(year=year, month=mes, day=dia, hour=hour, minute=minute)

    delete_date = send_date + timedelta(minutes=duracion)

    # programamos
    scheduler.add_job(
        enviar,
        "date",
        run_date=send_date,
        args=[id_msg_prg, delete_date],
        id=id_msg_prg,
    )
