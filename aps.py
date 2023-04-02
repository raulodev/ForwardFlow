import asyncio

from datetime import timedelta
from datetime import datetime

from telegram import Bot
from telegram.error import BadRequest

from apscheduler.schedulers.background import BackgroundScheduler
from database import obtener_msg_programado
from config import DATABASE_URL, TOKEN, ADMINS


job_defaults = {"misfire_grace_time": 600}

scheduler = BackgroundScheduler(job_defaults=job_defaults, timezone="America/Caracas")
scheduler.add_jobstore("sqlalchemy", url=DATABASE_URL)


def enviar(id: str, delete_date: datetime):

    data = obtener_msg_programado(id)

    async def run():

        bot = Bot(TOKEN)

        list_channels = [
            int(canal_id) for canal_id in data[4].split(",") if canal_id != ""
        ]

        # cada mensaje programado a eliminarse
        # tiene una diferencia de 2 segundos
        interval = 0
        for canal in list_channels:

            try:

                msg = await bot.forward_message(
                    chat_id=canal, from_chat_id=data[0], message_id=data[1]
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

            except BadRequest as error:

                for admin in ADMINS:

                    await bot.send_message(
                        chat_id=admin,
                        text=f"chat ID {data[0]}, msg ID {data[1]}: {error}",
                    )

            interval += 3

    asyncio.run(run())


def eliminar(msg_id: int, chat_id: int):
    async def run():

        bot = Bot(TOKEN)

        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)

        except BadRequest as error:

            for admin in ADMINS:

                await bot.send_message(
                    chat_id=admin, text=f"chat ID {chat_id}, msg ID {msg_id}: {error}"
                )

    asyncio.run(run())


def programar_reenvio(id_msg_prg: str):

    # seleccionamos datos del mensaje
    data = obtener_msg_programado(id_msg_prg)

    fecha_reenvio = data[2].replace("-", " ").replace(":", " ").split()
    fecha_reenvio = [int(num) for num in fecha_reenvio]

    year = fecha_reenvio[2]
    mes = fecha_reenvio[1]
    dia = fecha_reenvio[0]
    hour = fecha_reenvio[3]
    minute = fecha_reenvio[4]

    duracion = data[3]

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
