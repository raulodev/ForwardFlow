import re
from telegram import InlineKeyboardButton


class BuildMarkup:
    pattern_lines = r"\{[^\}]+\}"
    pattern_rows = r"\[([^\[\]]+)\s*-\s*([^\[\]]+)\]"

    def __init__(self, text: str):
        self.text = text

    def markup(self):
        """Retorna solo el markup del texto"""
        return self.__markup()

    def message(self):
        """Retorna solo el mensaje del texto"""
        self.__message: str
        sections = re.split(self.pattern_lines, self.text)
        for section in sections:
            if section.strip() != "":
                self.__message = section.strip()

        return self.__message

    def __lines(self):
        self.lines = re.findall(self.pattern_lines, self.text)
        return self.lines

    def __rows(self):
        self.__lines()
        self.rows = []
        for r in self.lines:
            row = re.findall(self.pattern_rows, r)
            self.rows.append(row)
        return self.rows

    def __markup(self):
        self.__rows()
        self.markup = []
        for r in self.rows:
            buttons = []
            for row in r:
                btn = InlineKeyboardButton(text=row[0].strip(), url=row[1].strip())
                buttons.append(btn)
            self.markup.append(buttons)

        return self.markup
