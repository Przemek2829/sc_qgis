import os

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon, QBrush
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLineEdit
from qgis.core import *
import sys

from .sc_url_validator import SCUrlValidator as url_validator

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_rdf_types_dialog.ui'), resource_suffix='')
REMOVE_ICON = QIcon(':/plugins/sc_qgis/remove.png')


class RdfTypesDialog(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(RdfTypesDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.add_uri_button.clicked.connect(lambda: self.addUri())
        self.layer_id = None
        config_metadata = None
        self.config_metadata_key = None

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.container_widget.resize(width - 20, height - 20)

    def addUri(self, uri='http://'):
        uri_item = QTreeWidgetItem(self.uri_tree)
        uri_item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled)
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        uri_line_edit = self.createLineEdit(uri)
        remove_button = self.createButton(uri_item)
        layout.addWidget(uri_line_edit)
        layout.addWidget(remove_button)
        container.setLayout(layout)
        self.uri_tree.setItemWidget(uri_item, 0, container)
        uri_line_edit.setFocus()

    def createLineEdit(self, uri):
        uri_line_edit = QLineEdit(uri, objectName='uri_edit')
        uri_line_edit.setPlaceholderText('Enter valid uri here (e.g. http://www.uri.net/sample#Feature)')
        uri_line_edit.setClearButtonEnabled(True)
        uri_line_edit.textEdited.connect(lambda uri: url_validator.validateUrl(uri, uri_line_edit))
        return uri_line_edit

    def createButton(self, uri_item):
        button = QPushButton(REMOVE_ICON, '')
        button.setMaximumSize(QSize(20, 20))
        button.setMinimumSize(QSize(20, 20))
        button.clicked.connect(lambda: self.removeItem(uri_item))
        return button

    def removeItem(self, item):
        idx = self.uri_tree.indexOfTopLevelItem(item)
        self.uri_tree.takeTopLevelItem(idx)
