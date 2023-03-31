import os
import sys
import json
from collections import OrderedDict

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QApplication, QFileDialog
from qgis.PyQt import uic
from qgis.core import *

from .sc_url_validator import SCUrlValidator as url_validator
from .sc_add_prefix_dialog import AddPrefixDialog
from .sc_prefixes_dialog import PrefixesDialog

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_add_connection_dialog.ui'), resource_suffix='')


class AddConnectionDialog(QDialog, FORM_CLASS):
    def __init__(self, connections_manager, parent=None):
        """Constructor."""
        super(AddConnectionDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.connections_manager = connections_manager
        self.name_input.setFocus()
        self.name_input.textChanged.connect(self.validateForm)
        self.type_combo.currentTextChanged.connect(self.changeConnectionType)
        self.url_input.textChanged.connect(self.validateForm)
        self.url_input.focusInEvent = self.selectLocalRDFSource
        self.use_authentication_check.stateChanged.connect(self.changeAuthWidgetsAvailibility)
        self.user_input.textChanged.connect(self.validateForm)
        self.password_input.textChanged.connect(self.validateForm)
        self.use_authentication_check.stateChanged.connect(self.validateForm)
        self.test_connection_button.clicked.connect(lambda: self.connections_manager.testConnection(self))
        self.add_prefix_button.clicked.connect(self.openAddPrefixDialog)
        self.show_prefixes_button.clicked.connect(self.openPrefixesDialog)
        self.form_is_valid = False
        self.prefixes = OrderedDict()

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.form_widget.resize(width - 20, height - 60)
        self.button_box.move(width - 175, height - 40)

    def changeConnectionType(self, type_text):
        if type_text == 'SPARQL Endpoint':
            self.url_label.setText('URL')
        elif type_text == 'Local File':
            self.url_label.setText('Path')
        self.validateForm()

    def selectLocalRDFSource(self, event):
        if self.url_label.text() == 'Path':
            path_widget = QApplication.focusWidget()
            if path_widget == self.url_input:
                path_widget.clearFocus()
                file_path = QFileDialog.getOpenFileName(self, "Select Local RDF Source")[0]
                if file_path != "":
                    path_widget.setText(file_path)

    def changeAuthWidgetsAvailibility(self, state):
        self.user_input.setEnabled(state == 2)
        self.password_input.setEnabled(state == 2)

    def validateForm(self):
        name = self.name_input.text().strip()
        url = self.url_input.text()
        use_authentication = self.use_authentication_check.checkState() == 2
        name_valid = name != ''
        if self.url_label.text() == 'URL':
            url_valid = url_validator.validateUrl(url, self.url_input) is not None
        else:
            url_valid = os.path.exists(url)
            if url_valid:
                self.url_input.setStyleSheet('color: rgb(0, 0, 0);')
            else:
                self.url_input.setStyleSheet('color: rgb(255, 0, 0);')
            if url.strip() == '':
                self.url_input.setStyleSheet('color: rgb(125, 125, 125);')
        if use_authentication:
            user = self.user_input.text()
            password = self.password_input.text()
            self.form_is_valid = name_valid and url_valid and user != '' and password != ''
        else:
            self.form_is_valid = name_valid and url_valid

    def openAddPrefixDialog(self):
        add_prefix_dialog = AddPrefixDialog()
        add_prefix_dialog.finished.connect(lambda accepted: self.addPrefix(accepted, add_prefix_dialog))
        add_prefix_dialog.setModal(True)
        add_prefix_dialog.show()

    def addPrefix(self, accepted, dialog):
        if accepted:
            if dialog.form_is_valid:
                self.prefixes[dialog.prefix_input.text().strip()] = dialog.uri_input.text()
            else:
                dialog.show()

    def openPrefixesDialog(self, connection_name=None):
        prefixes_dialog = PrefixesDialog(self.prefixes, self.connections_manager.logger)
        prefixes_dialog.setModal(True)
        if connection_name:
            prefixes_dialog.finished.connect(lambda accepted: self.editPrefixes(accepted, connection_name))
        prefixes_dialog.show()

    def editPrefixes(self, accepted, connection_name):
        connection = self.connections_manager.connections[connection_name]
        connection['prefixes'] = self.prefixes
        self.connections_manager.connections[connection_name] = connection
        with open(self.connections_manager.connections_file, 'w') as connections_file:
            json.dump(self.connections_manager.connections, connections_file, ensure_ascii=False)
