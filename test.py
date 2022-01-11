import sys
from PyQt5 import QtCore, QtWidgets


def restart():
    QtCore.QCoreApplication.quit()
    status = QtCore.QProcess.startDetached(sys.executable, sys.argv)
    print(status)


def main():
    app = QtWidgets.QApplication(sys.argv)

    print("[PID]:", QtCore.QCoreApplication.applicationPid())

    window = QtWidgets.QMainWindow()
    window.show()

    button = QtWidgets.QPushButton("Restart")
    button.clicked.connect(restart)

    window.setCentralWidget(button)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()