from typing import List, Tuple
import json
from sqlalchemy import Table, select
from sqlalchemy import delete
from sqlalchemy import update
from sqlalchemy import create_engine


from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import BigInteger
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import Session
from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import declarative_base

from config import DATABASE_URL

Base = declarative_base()

engine = create_engine(DATABASE_URL)


asociacion_grupo_mensajes = Table(
    "asociacion_grupo_mensajes",
    Base.metadata,
    Column("grupo_id", Integer, ForeignKey("tabla_grupo.id")),
    Column("mensaje_id", Integer, ForeignKey("tabla_mensaje.id")),
)

asociacion_grupo_canal = Table(
    "asociacion_grupo_canal",
    Base.metadata,
    Column("grupo_id", ForeignKey("tabla_grupo.id"), primary_key=True),
    Column("canal_id", ForeignKey("tabla_canal.id"), primary_key=True),
)


class Grupo(Base):
    __tablename__ = "tabla_grupo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str]
    canales: Mapped[List["Canal"]] = relationship(
        secondary=asociacion_grupo_canal, back_populates="grupos"
    )
    mensajes: Mapped[List["Mensaje"]] = relationship(
        secondary=asociacion_grupo_mensajes, back_populates="grupos"
    )

    def default(self, obj_list: list):
        return [str(obj) for obj in obj_list]

    def __init__(self, nombre: str):
        self.nombre = nombre

    def __str__(self):
        return str(
            json.dumps(
                {
                    "_": self.__class__.__name__,
                    "id": self.id,
                    "nombre": self.nombre,
                    "canales": self.default(self.canales),
                },
                indent=4,
            )
        )


class Canal(Base):
    __tablename__ = "tabla_canal"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    nombre: Mapped[str]
    grupos: Mapped[List["Grupo"]] = relationship(
        secondary=asociacion_grupo_canal, back_populates="canales"
    )

    def __init__(self, id: int, nombre: str):
        self.id = id
        self.nombre = nombre

    def __str__(self):
        return str(
            {
                "_": self.__class__.__name__,
                "id": self.id,
                "nombre": self.nombre,
            }
        )


class Mensaje(Base):
    __tablename__ = "tabla_mensaje"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    msg_id: Mapped[int]
    chat_id: Mapped[int]
    fecha_reenvio: Mapped[str]
    duracion: Mapped[int]
    grupos: Mapped[List["Grupo"]] = relationship(
        secondary=asociacion_grupo_mensajes, back_populates="mensajes"
    )

    def __init__(
        self,
        id: str,
        msg_id: int,
        chat_id: int,
        fecha_reenvio: str,
        duracion: int,
        grupos: list,
    ):
        self.id = id
        self.msg_id = msg_id
        self.chat_id = chat_id
        self.fecha_reenvio = fecha_reenvio
        self.duracion = duracion
        self.grupos = grupos


class MsgAlert(Base):
    __tablename__ = "msgalert"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str]

    def __init__(self, text: str):
        self.text = text


def obtener_grupo(id: int) -> Tuple[Grupo, List[Tuple[int, str]]]:
    with Session(engine) as session:
        grupo = session.query(Grupo).filter_by(id=id).first()

        canales = [(canal.id, canal.nombre) for canal in grupo.canales]
        return grupo, canales


def obtener_todos_grupos() -> List[Grupo]:
    with Session(engine) as session:
        grupos = session.query(Grupo).all()
        return grupos


def crear_nuevo_grupo(nombre: str):
    with Session(engine) as session:
        group = Grupo(nombre=nombre)
        session.add(group)
        session.commit()


def eliminar_un_grupo(nombre: str):
    with Session(engine) as session:
        session.execute(delete(Grupo).where(Grupo.nombre == nombre))
        session.commit()


def actualizar_mensaje_bienvenida(text: str):
    with Session(engine) as session:
        data = session.execute(select(MsgAlert.id).where(MsgAlert.id == 1)).first()

        if data:
            session.execute(update(MsgAlert).where(MsgAlert.id == 1).values(text=text))

        else:
            msg = MsgAlert(text)
            session.add(msg)

        session.commit()


def obtener_mensaje_bienvenida():
    with Session(engine) as session:
        data = session.execute(select(MsgAlert.text).where(MsgAlert.id == 1)).first()
        text = data[0] if data else "Hola $NAME esto es un bot de uso privado."
        return text


def obtener_msg_programado(id: str):
    """retorna los datos de un mensaje"""

    with Session(engine) as session:
        mensaje = session.query(Mensaje).filter_by(id=id).first()

        if not mensaje:
            return None, None

        if not mensaje.grupos:
            canales = obtener_todos_canales()

        else:
            canales = []
            for grupo in mensaje.grupos:
                canales.extend(grupo.canales)

        return mensaje, list(set(canales))


def crear_msg_programado(
    id: str,
    msg_id: int,
    chat_id: int,
    fecha_reenvio: str,
    duracion: int,
    grupos: list,
):
    """Agrega un nuevo mensaje"""

    with Session(engine) as session:
        if "todos" in grupos:
            grupos = []

        else:
            grupos = (
                session.query(Grupo)
                .filter(Grupo.id.in_([int(grupo) for grupo in grupos]))
                .all()
            )

        new = Mensaje(id, msg_id, chat_id, fecha_reenvio, duracion, grupos)
        session.add(new)
        session.commit()


def crear_nuevo_canal(chat_id: int, nombre: str):
    """agrega un nuevo canal"""

    with Session(engine) as session:
        new = Canal(id=chat_id, nombre=nombre)

        session.add(new)
        session.commit()


def obtener_todos_canales():
    """selecciona los canales de la bd"""

    with Session(engine) as session:
        data = session.execute(select(Canal.id, Canal.nombre)).all()

        return data


def eliminar_canal(chat_id: int):
    """eliminar canales de la bd"""

    with Session(engine) as session:
        is_exist = session.execute(select(Canal).where(Canal.id == chat_id)).fetchone()

        if is_exist is None:
            return False

        session.execute(delete(Canal).where(Canal.id == chat_id))
        session.commit()

        return True


def agregar_canal_en_grupo(grupo_id: int, canal_id: int):
    with Session(engine) as session:
        grupo = session.query(Grupo).filter_by(id=grupo_id).first()
        canal = session.query(Canal).filter_by(id=canal_id).first()

        grupo.canales.append(canal)
        session.commit()


def eliminar_canal_del_grupo(grupo_id: int, canal_id: int):
    with Session(engine) as session:
        grupo = session.query(Grupo).filter_by(id=grupo_id).first()
        canal = session.query(Canal).filter_by(id=canal_id).first()

        grupo.canales.remove(canal)
        session.commit()
