from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

class Sidebar(QWidget):
    def __init__(self):
        super().__init__()

        # self.setFixedWidth(200)
        self.setFixedWidth(0)
