import os
import sys
import json

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLineEdit, QApplication
from qgis.PyQt import uic
from qgis.core import *

from .sc_logger_mode import SCLoggerMode

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_prefix_db_dialog.ui'), resource_suffix='')
COPY_ICON = QIcon(':/plugins/sc_qgis/copy.png')
CONNECTIONS_FILE = os.path.join(os.path.join(os.path.dirname(__file__), 'connections'), 'connections.json')


class PrefixDbDialog(QDialog, FORM_CLASS):
    def __init__(self, prefix_dialog, logger, parent=None):
        """Constructor."""
        super(PrefixDbDialog, self).__init__(parent)
        self.setupUi(self)
        self.logger = logger
        self.resizeEvent = self.adjustSize
        self.fillPrefixes()

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.container_widget.resize(width - 10, height - 5)

    def fillPrefixes(self):
        self.prefix_tree.clear()
        prefixes = set()
        if os.path.exists(CONNECTIONS_FILE):
            with open(CONNECTIONS_FILE) as connections_file:
                connections = json.load(connections_file)
                for connection_meta in connections.values():
                    for uri in connection_meta.get('prefixes').values():
                        prefixes.add(uri)
            for uri in prefixes:
                list_item = QTreeWidgetItem(self.prefix_tree)
                container = QWidget()
                layout = QHBoxLayout()
                layout.setContentsMargins(1, 1, 1, 1)
                uri_line_edit = self.createLineEdit(uri)
                copy_button = self.createButton(uri_line_edit)
                layout.addWidget(uri_line_edit)
                layout.addWidget(copy_button)
                container.setLayout(layout)
                self.prefix_tree.setItemWidget(list_item, 0, container)

    def createLineEdit(self, uri):
        uri_line_edit = QLineEdit(uri, objectName='uri_edit')
        uri_line_edit.setEnabled(False)
        return uri_line_edit

    def createButton(self, uri_item):
        button = QPushButton(COPY_ICON, '')
        button.setToolTip('Copy prefix')
        button.setMaximumSize(QSize(20, 20))
        button.setMinimumSize(QSize(20, 20))
        button.clicked.connect(lambda: self.copyPrefix(uri_item))
        return button

    def copyPrefix(self, uri_item):
        uri = uri_item.text()
        QApplication.clipboard().setText(uri)
        self.logger.logMessage('SC QGIS', 'URI <b>"%s"</b> copied to clipboard' % uri, Qgis.Success, SCLoggerMode.loud)
        self.close()
