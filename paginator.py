from math import ceil
import json
from config import PAGINATION


class Page:
    def __init__(
        self,
        number: int = None,
        data: list = None,
        next_page: int = None,
        prev_page: int = None,
    ):
        self.number = number
        self.data = data
        self.next_page = next_page
        self.prev_page = prev_page

    def default(self, obj_list: list):
        return [str(obj) for obj in obj_list]

    def __str__(self) -> str:
        return str(
            json.dumps(
                {
                    "_": self.__class__.__name__,
                    "number": self.number,
                    "data": self.default(self.data),
                    "next_page": self.next_page,
                    "prev_page": self.prev_page,
                    "is_exist": self.is_exist,
                },
                indent=4,
            )
        )

    @property
    def is_exist(self):
        return self.number is not None

    @property
    def has_next_page(self):
        return bool(self.next_page)

    @property
    def has_prev_page(self):
        return bool(self.prev_page)


class Paginator:
    def __init__(
        self,
        object_list: list,
        items: int = PAGINATION,
    ):
        self.object_list = object_list
        self.items = items
        self.number = None
        self.list_pages = self.__create_pages()

    def page(self, number: int) -> Page:
        if number > self.total_pages or number <= 0:
            return Page()

        self.number = number - 1

        return Page(
            number=self.number + 1,
            data=self.list_pages[self.number],
            next_page=self.number + 2 if self.has_next else None,
            prev_page=self.number if self.has_prev else None,
        )

    @property
    def total_objects(self) -> int:
        """Retorna el número de objetos en total"""
        return len(self.object_list)

    @property
    def total_pages(self) -> int:
        "Retorna la cantidad de páginas en total"
        return ceil(self.total_objects / self.items)

    def __create_pages(self):
        pages = []
        for i in range(0, self.total_objects, self.items):
            page = self.object_list[i : i + self.items]
            pages.append(page)
        return pages

    @property
    def has_next(self):
        return self.number in range(self.total_pages - 1)

    @property
    def has_prev(self):
        return self.number - 1 in range(self.total_pages - 1)
