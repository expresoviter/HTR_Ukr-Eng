from PyQt6.QtWidgets import *

class ScrollLabel(QScrollArea):
    """
    Клас поля з прокручуванням

    ---

    Атрибути
    --------
    label   : Qlabel
        Текстове поле, яке має прокручуватися.

    Методи
    ------
    """

    def __init__(self):
        # Ініціалізуємо віджет области з прокручуванням
        QScrollArea.__init__(self)

        # Віджет автоматично змінює розмір відповідно до умов
        self.setWidgetResizable(True)

        content = QWidget(self)
        self.setWidget(content)

        lay = QVBoxLayout(content)

        # Створюємо текстове поле і дозволяємо перенос слів
        self.label = QLabel(content)
        self.label.setWordWrap(True)
        lay.addWidget(self.label)
