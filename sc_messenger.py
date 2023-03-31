from qgis.PyQt.QtWidgets import QMessageBox


class Messenger:

    @staticmethod
    def createMessage(title, icon, text):
        msg_box = QMessageBox()
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        returnValue = msg_box.exec()
        return returnValue
