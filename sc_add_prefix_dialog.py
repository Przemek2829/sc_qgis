import os
import re

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt import uic
import sys

from .sc_url_validator import SCUrlValidator as url_validator

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_add_prefix_dialog.ui'), resource_suffix='')


class AddPrefixDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(AddPrefixDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.prefix_input.textChanged.connect(self.validateForm)
        self.uri_input.textChanged.connect(self.validateForm)
        self.prefix_input.setFocus()
        self.form_is_valid = False

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.form_widget.resize(width - 20, height - 60)
        self.button_box.move(width - 175, height - 40)

    def validateForm(self):
        prefix = self.prefix_input.text().strip()
        uri = self.uri_input.text()
        prefix_valid = re.match('^[a-zA-Z0-9_]+$', prefix)
        if prefix_valid:
            self.prefix_input.setStyleSheet('color: rgb(0, 0, 0);')
        else:
            self.prefix_input.setStyleSheet('color: rgb(255, 0, 0);')
        uri_valid = url_validator.validateUrl(uri, self.uri_input) is not None
        self.form_is_valid = prefix_valid and uri_valid
