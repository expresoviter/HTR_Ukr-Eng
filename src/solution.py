from engRecognition import EnglishRecognition
from PyQt6.QtWidgets import *
from docx import Document
from database import *
from datetime import date
import pandas as pd
from ukrRecognition import UkrainianRecognition

class Solution:
    """
        Клас взаємодії інтерфейсу з методи розв'язку задачі.

        ---

        Атрибути
        --------
        window: interface.MainWindow
            Екземпляр вікна інтерфейсу, з яким відбувається взаємодія
        coding: str
            Кодування для запису у файл.


        Методи
        ------
        getParameters()
            Отримання заданих параметрів і запуск розпізнавання тексту.
        showResult(int lang, int coding, str path, str[] recognized)
            Виведення результатів розпізнавання в інтерфейс.
        databaseSaving()
            Збереження результату до БД.
        savingFile()
            Збереження результату до файлу.
        historyPageUpdate()
            Оновлення сторінки історії під час роботи програми.
        getItem(QTableWidgetItem item)
            Отримання інформації про запис в історії за подвійним натисканням.
    """

    def __init__(self, window):
        self.window = window

    def getParameters(self):
        path = self.window.filename_edit.displayText()
        language = self.window.ukrLang.isChecked()
        coding = self.window.asciiCoding.isChecked()
        if path != "":
            if language:
                recognized = UkrainianRecognition().main(path)
            else:
                recognized = EnglishRecognition().main({"mode":"infer","img_file":path})
            self.showResult(language,coding,path,recognized)

    def showResult(self, lang, coding, path, recognized):
        self.window.filename2.setText(path)
        if lang:
            self.window.language2.setText("Ukrainian")
        else:
            self.window.language2.setText("English")
        if coding:
            self.window.coding2.setText("ASCII")
            self.coding = "ascii"
        else:
            self.window.coding2.setText("UTF-8")
            self.coding = "utf-8"
        self.window.resultText.label.setText(recognized[0])
        self.window.result3.label.setText(recognized[0])
        self.window.stackedWidget.setCurrentIndex(1)

    def databaseSaving(self):
        file = self.window.filename2.text()
        file = file[file.rfind("\\")+1:]
        record = Record(date=date.today(), file=file,
                      language=self.window.language2.text(),
                      coding=self.window.coding2.text(),
                      result=self.window.resultText.label.text())
        self.window.session.add(record)
        self.window.session.commit()
        self.window.stackedWidget.setCurrentIndex(2)

    def savingFile(self):
        try:
            reply = self.window.msg.exec()
            path = self.window.saveFile.displayText()
            text = self.window.result3.label.text()
            if path[-4:] == "docx":
                doc = Document()
                p = doc.add_paragraph(text)
                doc.save(path)
            else:
                with open(path, "w", encoding=self.coding) as file:
                    file.write(text)
            if reply == QMessageBox.StandardButton.Yes:
                self.window.stackedWidget.setCurrentIndex(0)
        except Exception as e:
            print(f"Error: {e}")

    def historyPageUpdate(self):
        a = pd.read_sql("select * from records", self.window.engine)
        a = a.sort_values(by=["id"], ascending=False)
        self.window.tableWidget.setRowCount(a.shape[0])
        self.window.tableWidget.setColumnCount(6)
        self.window.tableWidget.setHorizontalHeaderLabels(["Id", "Date", "File", "Language", "Coding","Result"])

        # Заповнення таблиці історії
        for i in range(a.shape[0]):
            for j in range(6):
                item = QTableWidgetItem(str(a.iat[i, j]))
                self.window.tableWidget.setItem(i, j, item)

        # Ресайз колонок, щоб підігнати під зміст
        self.window.tableWidget.resizeColumnsToContents()
        self.window.tableWidget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.window.tableWidget.itemDoubleClicked.connect(self.getItem)

        self.window.stackedWidget.setCurrentIndex(3)

    def getItem(self, item):
        a = pd.read_sql("select * from records", self.window.engine)
        a = a.sort_values(by=["id"], ascending=False)
        res = a.iloc[item.row()]

        self.coding = res.coding
        self.window.result3.label.setText(res.result)
        self.window.stackedWidget.setCurrentIndex(2)