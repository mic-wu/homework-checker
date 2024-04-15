import sys
from PyQt5.QtWidgets import QApplication, QWidget, QHBoxLayout

from circuitEditor import CircuitEditor
from sidebar import Sidebar



class MyWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle('Homework Checker')

        self.initUI()

    def initUI(self):
        # scuffed
        self.setObjectName("main")
        self.setGeometry(100, 100, 800, 600)
        self.setStyleSheet("""
                            #main { background-color: white; }
                           """)
                            # * { color: black; }

        # top level hbox
        layout = QHBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)
        self.setLayout(layout)

        self.circuit_drawer = CircuitEditor()
        self.sidebar = Sidebar()

        layout.addWidget(self.circuit_drawer)
        layout.addWidget(self.sidebar)


    def on_button_clicked(self):
        pass

if __name__ == '__main__':
    app = QApplication(sys.argv)

    window = MyWindow()
    window.show()
    sys.exit(app.exec_())
