from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from pathlib import Path
from scrolllabel import ScrollLabel
from solution import Solution
from database import *
from sqlalchemy.orm import sessionmaker
class MainWindow(QMainWindow):
    """
        Клас, призначений для розпізнавання тексту англійською мовою.

        ---

        Атрибути
        --------
        engine: sqlalchemy.engine.base.Engine
            Рушій для підключення бази даних.
        session: sqlalchemy.orm.sessionmaker
            Сесія підключення до бази даних.
        solution: solution.Solution
            Екземпляр функціонального класу розв'язку.
        stackedWidget: QStackedWidget
            Віджет для можливості багатосторінковости одного вікна.
        firstPageWidget: QWidget
            Віджет першої сторінки програми - задання перетворення.
        filename_edit: QLineEdit
            Поле для введення шляху зображення для розпізнавання.
        ukrLang: QRadioButton
            Радіокнопка для вибору української мови як параметру мови.
        engLang: QRadioButton
            Радіокнопка для вибору англійської мови як параметру мови.
        asciiCoding: QRadioButton
            Радіокнопка для вибору ASCII як параметру кодування тексту для запису у файл.
        utfCoding: QRadioButton
            Радіокнопка для вибору UTF-8 як параметру кодування тексту для запису у файл.
        secondPageWigdet: QWidget
            Віджет другої сторінки програми - перегляд результату.
        filename2: QLabel
            Текстова мітка з назвою файлу зображення.
        language2: QLabel
            Текстова мітка з мовою як параметром розпізнавання.
        coding2: QLabel
            Текстова мітка з мовою як кодуванням розпізнавання.
        resultText: scrolllabel.ScrollLabel
            Текстова мітка з прокручуванням з результуючим розпізнаним текстом.
        thirdPageWidget: QWidget
            Віджет другої сторінки програми - збереження результату.
        savefile: QLineEdit
            Поле для введення шляху збереження тексту у файл.
        result3: scrolllabel.ScrollLabel
            Текстова мітка з прокручуванням з результуючим розпізнаним текстом на сторінці збереження.
        msg: QMessageBox
            Вікно з повідомленням про збереження.
        historyPageWidget: QWidget
            Віджет сторінки історії - перегляд попередніх записів.
        tableWidget: QTableWidget
            Віджет таблиці з попередніми розпізнаваннями, записаними в базу даних.


        Методи
        ------
        firstPageInitialize()
            Ініціалізація першої сторінки програми.
        secondPageInitialize()
            Ініціалізація другої сторінки програми.
        thirdPageInitialize()
            Ініціалізація третьої сторінки програми.
        historyPageInitialize()
            Ініціалізація сторінки історії програми.
        openFileDialog(int page)
            Взаємодія з файловою системою для роботи з читанням\записом файлу.
    """

    def __init__(self):
        super().__init__()

        self.engine = create_engine('sqlite:///htr.db', echo=True)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        self.setWindowTitle("Handwritten to Printed Text Conversion")
        self.solution = Solution(self)
        self.firstPageInitialize()
        self.secondPageInitialize()
        self.thirdPageInitialize()
        self.historyPageInitialize()

        self.stackedWidget = QStackedWidget()
        self.stackedWidget.addWidget(self.firstPageWidget)
        self.stackedWidget.addWidget(self.secondPageWidget)
        self.stackedWidget.addWidget(self.thirdPageWidget)
        self.stackedWidget.addWidget(self.historyPageWidget)
        layout = QVBoxLayout()
        layout.addWidget(self.stackedWidget)

        menubar = self.menuBar()
        db_action = menubar.addAction("Convert!")
        db_action.triggered.connect(lambda : self.stackedWidget.setCurrentIndex(0))

        db_action1 = menubar.addAction("History")
        db_action1.triggered.connect(self.solution.historyPageUpdate)

        self.setFixedSize(QSize(500, 350))
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def firstPageInitialize(self):
        self.firstPageWidget = QWidget()
        fileLabel = QLabel()
        fileLabel.setText("Choose a file to convert from:")

        # вибір файлу
        file_browse = QPushButton('Browse')
        file_browse.clicked.connect(lambda : self.openFileDialog(1))
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("Don`t forget to choose!")

        browseLayout = QGridLayout()
        browseLayout.addWidget(QLabel('File:'), 0, 0)
        browseLayout.addWidget(self.filename_edit, 0, 1)
        browseLayout.addWidget(file_browse, 0, 2)

        conversionLabel = QLabel()
        conversionLabel.setText("Choose conversion parameters:")

        langLayout = QVBoxLayout()
        langLayout.addWidget(QLabel("Language:"))

        # група радіокнопок з вибору мови
        langGroup = QButtonGroup()
        self.ukrLang = QRadioButton("Ukrainian")
        self.ukrLang.setChecked(True)
        langLayout.addWidget(self.ukrLang)
        langGroup.addButton(self.ukrLang)
        self.engLang = QRadioButton("English")

        langLayout.addWidget(self.engLang)
        langGroup.addButton(self.engLang)

        codingLayout = QVBoxLayout()
        codingLayout.addWidget(QLabel("Coding:"))

        # група радіокнопок з вибору кодування
        codingGroup = QButtonGroup()
        self.asciiCoding = QRadioButton("ASCII")
        self.asciiCoding.setChecked(True)
        codingLayout.addWidget(self.asciiCoding)
        codingGroup.addButton(self.asciiCoding)

        self.utfCoding = QRadioButton("UTF-8")
        codingLayout.addWidget(self.utfCoding)
        codingGroup.addButton(self.utfCoding)

        parametersLayout = QHBoxLayout()
        parametersLayout.addLayout(langLayout)
        parametersLayout.addLayout(codingLayout)

        continue0Button = QPushButton("Continue")
        continue0Button.clicked.connect(self.solution.getParameters)

        outerLayout = QVBoxLayout()
        outerLayout.addWidget(fileLabel)
        outerLayout.addLayout(browseLayout)
        outerLayout.addWidget(conversionLabel)
        outerLayout.addLayout(parametersLayout)
        outerLayout.addWidget(continue0Button)

        self.firstPageWidget.setLayout(outerLayout)

    def secondPageInitialize(self):
        self.secondPageWidget = QWidget()
        chosenLabel = QLabel()
        chosenLabel.setText("Chosen parameters:")

        self.filename2 = QLabel()
        self.language2 = QLabel()
        self.coding2 = QLabel()

        # Виведені параметри перетворення
        parametersLayout = QGridLayout()
        parametersLayout.addWidget(QLabel('File:'), 0, 0)
        parametersLayout.addWidget(self.filename2, 0, 1)
        parametersLayout.addWidget(QLabel('Language:'), 1, 0)
        parametersLayout.addWidget(self.language2, 1, 1)
        parametersLayout.addWidget(QLabel('Coding:'), 2, 0)
        parametersLayout.addWidget(self.coding2, 2, 1)

        self.resultText = ScrollLabel()

        retry1Button = QPushButton("Retry")
        retry1Button.clicked.connect(lambda : self.stackedWidget.setCurrentIndex(0))
        continue1Button = QPushButton("Save")
        continue1Button.clicked.connect(self.solution.databaseSaving)

        buttonsLayout = QHBoxLayout()
        buttonsLayout.addWidget(retry1Button)
        buttonsLayout.addWidget(continue1Button)

        outerLayout = QVBoxLayout()
        outerLayout.addWidget(chosenLabel)
        outerLayout.addLayout(parametersLayout)
        outerLayout.addWidget(self.resultText)
        outerLayout.addLayout(buttonsLayout)

        self.secondPageWidget.setLayout(outerLayout)

    def thirdPageInitialize(self):
        self.thirdPageWidget = QWidget()
        saveDirectoryLabel = QLabel()
        saveDirectoryLabel.setText("Choose a directory to save:")

        # вибір файлу для запису
        file_browse = QPushButton('Browse')
        file_browse.clicked.connect(lambda: self.openFileDialog(3))
        self.saveFile = QLineEdit()

        browseLayout = QGridLayout()
        browseLayout.addWidget(QLabel('File:'), 0, 0)
        browseLayout.addWidget(self.saveFile, 0, 1)
        browseLayout.addWidget(file_browse, 0, 2)

        self.result3 = ScrollLabel()

        continue2Button = QPushButton("Confirm")
        continue2Button.clicked.connect(self.solution.savingFile)

        # встановлення повідомлення про збереження
        self.msg = QMessageBox()
        self.msg.setIcon(QMessageBox.Icon.Question)
        self.msg.setText("Return to the main page?")
        self.msg.setInformativeText("The file is saved. Do you want to return to conversion?")
        self.msg.setWindowTitle("Done")
        self.msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        outerLayout = QVBoxLayout()
        outerLayout.addWidget(saveDirectoryLabel)
        outerLayout.addLayout(browseLayout)
        outerLayout.addWidget(self.result3)
        outerLayout.addWidget(continue2Button)

        self.thirdPageWidget.setLayout(outerLayout)

    def historyPageInitialize(self):
        self.historyPageWidget = QWidget()
        historyLabel = QLabel()
        historyLabel.setText("Conversion history:")

        self.tableWidget = QTableWidget()
        outerLayout = QVBoxLayout()
        outerLayout.addWidget(historyLabel)
        outerLayout.addWidget(self.tableWidget)

        self.historyPageWidget.setLayout(outerLayout)


    def openFileDialog(self, page):
        # Вибір зображення для розпізнавання
        if page == 1:
            filename, ok = QFileDialog.getOpenFileName(
                self,
                "Select a File",
                "C:\\",
                "Images (*.png *.jpg)"
            )
            if filename:
                path = Path(filename)
                self.filename_edit.setText(str(path))
        # Вибір файлу для запису
        else:
            filename, ok = QFileDialog.getSaveFileName(
                self,
                "Select a File",
                "C:\\",
                "Text (*.txt *.docx)")
            if filename:
                path = Path(filename)
                self.saveFile.setText(str(path))



