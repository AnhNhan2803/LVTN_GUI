from PyQt5 import QtCore, QtWidgets

class LoginPopup(QtWidgets.QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
        self.setAutoFillBackground(True)
        self.setStyleSheet('''
            LoginPopup {
                background: rgba(64, 64, 64, 64);
            }
            QWidget#container {
                border: 2px solid darkGray;
                border-radius: 4px;
                background: rgb(64, 64, 64);
            }
            QWidget#container > QLabel {
                color: white;
            }
            QLabel#title {
                font-size: 20pt;
            }
            QPushButton#close {
                color: white;
                font-weight: bold;
                background: none;
                border: 1px solid gray;
            }
        ''')

        fullLayout = QtWidgets.QVBoxLayout(self)

        self.container = QtWidgets.QWidget(
            autoFillBackground=True, objectName='container')
        fullLayout.addWidget(self.container, alignment=QtCore.Qt.AlignCenter)
        self.container.setSizePolicy(
            QtWidgets.QSizePolicy.Maximum, QtWidgets.QSizePolicy.Maximum)

        buttonSize = self.fontMetrics().height()
        self.closeButton = QtWidgets.QPushButton(
            '×', self.container, objectName='close')
        self.closeButton.setFixedSize(buttonSize, buttonSize)
        self.closeButton.clicked.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self.container)
        layout.setContentsMargins(
            buttonSize * 2, buttonSize, buttonSize * 2, buttonSize)

        title = QtWidgets.QLabel(
            'Enter an email address', 
            objectName='title', alignment=QtCore.Qt.AlignCenter)
        layout.addWidget(title)

        layout.addWidget(QtWidgets.QLabel('EMAIL'))
        self.emailEdit = QtWidgets.QLineEdit()
        layout.addWidget(self.emailEdit)
        layout.addWidget(QtWidgets.QLabel('PASSWORD'))
        self.passwordEdit = QtWidgets.QLineEdit(
            echoMode=QtWidgets.QLineEdit.Password)
        layout.addWidget(self.passwordEdit)

        buttonBox = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttonBox)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.okButton = buttonBox.button(buttonBox.Ok)
        self.okButton.setEnabled(False)

        self.emailEdit.textChanged.connect(self.checkInput)
        self.passwordEdit.textChanged.connect(self.checkInput)
        self.emailEdit.returnPressed.connect(lambda:
                self.passwordEdit.setFocus())
        self.passwordEdit.returnPressed.connect(self.accept)

        parent.installEventFilter(self)

        self.loop = QtCore.QEventLoop(self)
        self.emailEdit.setFocus()

    def checkInput(self):
        self.okButton.setEnabled(bool(self.email() and self.password()))

    def email(self):
        return self.emailEdit.text()

    def password(self):
        return self.passwordEdit.text()

    def accept(self):
        if self.email() and self.password():
            self.loop.exit(True)

    def reject(self):
        self.loop.exit(False)

    def close(self):
        self.loop.quit()

    def showEvent(self, event):
        self.setGeometry(self.parent().rect())

    def resizeEvent(self, event):
        r = self.closeButton.rect()
        r.moveTopRight(self.container.rect().topRight() + QtCore.QPoint(-5, 5))
        self.closeButton.setGeometry(r)

    def eventFilter(self, source, event):
        if event.type() == event.Resize:
            self.setGeometry(source.rect())
        return super().eventFilter(source, event)

    def exec_(self):
        self.show()
        self._raise()
        res = self.loop.exec_()
        self.hide()
        return res


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        button = QtWidgets.QPushButton('LOG IN')
        layout.addWidget(button)
        button.clicked.connect(self.showDialog)
        self.setMinimumSize(640, 480)

    def showDialog(self):
        dialog = LoginPopup(self)
        if dialog.exec_():
            print(dialog.email(), dialog.password())

import sys
app = QtWidgets.QApplication(sys.argv)
w = MainWindow()
w.show()
sys.exit(app.exec_())