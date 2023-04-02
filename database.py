from sqlalchemy import select
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy import create_engine

from sqlalchemy.orm import Session
from sqlalchemy.orm import declarative_base

from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Integer
from sqlalchemy import BigInteger

from config import DATABASE_URL

Base = declarative_base()

engine = create_engine(DATABASE_URL)


class Msg(Base):

    __tablename__ = "mensajes"

    id = Column(String, primary_key=True)
    msg_id = Column(BigInteger)
    chat_id = Column(BigInteger)
    fecha_reenvio = Column(String)
    duracion = Column(Integer)
    channels = Column(Text)

    def __init__(
        self,
        id: str,
        msg_id: int,
        chat_id: int,
        fecha_reenvio: str,
        duracion: int,
        channels: str,
    ):

        self.id = id
        self.msg_id = msg_id
        self.chat_id = chat_id
        self.fecha_reenvio = fecha_reenvio
        self.duracion = duracion
        self.channels = channels


class Canal(Base):

    __tablename__ = "canales"

    chat_id = Column(BigInteger, primary_key=True)
    nombre = Column(String)

    def __init__(self, chat_id: int, nombre: str) -> None:
        self.chat_id = chat_id
        self.nombre = nombre


class MsgAlert(Base):

    __tablename__ = "msgalert"

    id = Column(Integer, primary_key=True)
    text = Column(Text)

    def __init__(self, text: str):
        self.text = text


def actualizar_mensaje_alerta(text: str):

    with Session(engine) as session:

        data = session.execute(select(MsgAlert.id).where(MsgAlert.id == 1)).first()

        if data:

            session.execute(update(MsgAlert).where(MsgAlert.id == 1).values(text=text))

        else:

            msg = MsgAlert(text)
            session.add(msg)

        session.commit()


def obtener_mensaje_alerta():

    with Session(engine) as session:

        data = session.execute(select(MsgAlert.text).where(MsgAlert.id == 1)).first()

        text = data[0] if data else "Hola $NAME esto es un bot de uso privado."

        return text


def obtener_msg_programado(id: str):
    """retorna los datos de un mensaje"""

    with Session(engine) as session:

        data = session.execute(
            select(
                Msg.chat_id, Msg.msg_id, Msg.fecha_reenvio, Msg.duracion, Msg.channels
            ).where(Msg.id == id)
        ).first()

        return data


def gurdar_msg_programado(
    id: str, msg_id: int, chat_id: int, fecha_reenvio: str, duracion: int, channles: str
):
    """Agrega un nuevo mensaje"""

    with Session(engine) as session:

        new = Msg(id, msg_id, chat_id, fecha_reenvio, duracion, channles)
        session.add(new)
        session.commit()


def agregar_nuevo_canal(chat_id: int, nombre: str):
    """agrega un nuevo canal"""

    with Session(engine) as session:

        new = Canal(chat_id=chat_id, nombre=nombre)

        session.add(new)
        session.commit()


def seleccionar_canales():
    """selecciona los canales de la bd"""

    with Session(engine) as session:

        data = session.execute(select(Canal.chat_id, Canal.nombre)).all()

        return data


def eliminar_canal(chat_id: int):
    """eliminar canales de la bd"""

    with Session(engine) as session:

        session.execute(delete(Canal).where(Canal.chat_id == chat_id))
        session.commit()
