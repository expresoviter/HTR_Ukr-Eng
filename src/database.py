from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Record(Base):
    """
        Клас таблиці records бази даних застосунку.

        Атрибути
        --------
        date : datetime.date
            Дата розпізнавання тексту.
        file  : string
            Назва файлу, з якого відбулося розпізнавання.
        language  : string
            Мова розпізнавання тексту.
        coding  : string
            Кодування запису у файл результату розпізнавання.
        result  : string
            Розпізнаний текст - результат.


        Методи
        ------
        """

    __tablename__ = 'records'
    id = Column(Integer, primary_key=True)
    date = Column(DATE)
    file = Column(String)
    language = Column(String)
    coding = Column(String)
    result = Column(String)

    def __init__(self, date, file, language, coding, result):
        self.date = date
        self.file = file
        self.language = language
        self.coding = coding
        self.result = result

    def __repr__(self):
        return self.file


