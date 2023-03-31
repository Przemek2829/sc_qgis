import os
import sys
import re

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLineEdit, QMessageBox
from qgis.PyQt import uic

from .sc_url_validator import SCUrlValidator as url_validator
from .sc_add_prefix_dialog import AddPrefixDialog
from .sc_prefix_db_dialog import PrefixDbDialog
from .sc_messenger import Messenger as msg

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_prefixes_dialog.ui'), resource_suffix='')
REMOVE_ICON = QIcon(':/plugins/sc_qgis/remove.png')
EDIT_ICON = QIcon(':/plugins/sc_qgis/edit.png')


class PrefixesDialog(QDialog, FORM_CLASS):
    def __init__(self, prefixes, logger, parent=None):
        """Constructor."""
        super(PrefixesDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.prefixes = prefixes
        self.logger = logger
        self.fillPrefixes()
        self.add_prefix_button.clicked.connect(self.openAddPrefixDialog)
        self.prefixes_button.clicked.connect(self.openPrefixDbDialog)

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.container_widget.resize(width - 10, height - 5)

    def fillPrefixes(self):
        self.prefix_tree.clear()
        for prefix, uri in self.prefixes.items():
            list_item = QTreeWidgetItem(self.prefix_tree)
            container = QWidget()
            layout = QHBoxLayout()
            layout.setContentsMargins(1, 1, 1, 1)
            uri_line_edit = self.createLineEdit('%s: <%s>' % (prefix, uri))
            remove_button = self.createButton(REMOVE_ICON, prefix, list_item)
            edit_button = self.createButton(EDIT_ICON, prefix, uri_line_edit)
            layout.addWidget(uri_line_edit)
            layout.addWidget(edit_button)
            layout.addWidget(remove_button)
            container.setLayout(layout)
            self.prefix_tree.setItemWidget(list_item, 0, container)

    def createLineEdit(self, uri):
        uri_line_edit = QLineEdit(uri, objectName='uri_edit')
        uri_line_edit.setPlaceholderText('Enter valid uri here (e.g. http://www.uri.net/sample#Feature)')
        uri_line_edit.setEnabled(False)
        return uri_line_edit

    def createButton(self, icon, prefix, uri_item):
        button = QPushButton(icon, '')
        button.setMaximumSize(QSize(20, 20))
        button.setMinimumSize(QSize(20, 20))
        if icon == REMOVE_ICON:
            button.clicked.connect(lambda: self.removeItem(prefix, uri_item))
        if icon == EDIT_ICON:
            button.clicked.connect(lambda: self.openEditPrefixDialog(uri_item))
        return button

    def removeItem(self, prefix, item):
        return_value = msg.createMessage("Remove prefix", QMessageBox.Question,
                                         "Action will cause permanent changes. Continue anyway?")
        if return_value == QMessageBox.Ok:
            del self.prefixes[prefix]
            idx = self.prefix_tree.indexOfTopLevelItem(item)
            self.prefix_tree.takeTopLevelItem(idx)

    def openEditPrefixDialog(self, uri_item):
        prefix = uri_item.text()
        regexp = '(.*): <(.*)>'
        prefix_alias = re.sub(regexp, r'\1', prefix)
        prefix_uri = re.sub(regexp, r'\2', prefix)
        edit_prefix_dialog = AddPrefixDialog()
        edit_prefix_dialog.prefix_input.setText(prefix_alias)
        edit_prefix_dialog.uri_input.setText(prefix_uri)
        edit_prefix_dialog.finished.connect(lambda accepted: self.editPrefix(accepted, edit_prefix_dialog, uri_item))
        edit_prefix_dialog.setModal(True)
        edit_prefix_dialog.show()

    def editPrefix(self, accepted, dialog, uri_item):
        if accepted:
            if dialog.form_is_valid:
                prefix = dialog.prefix_input.text().strip()
                uri = dialog.uri_input.text()
                uri_item.setText('%s: <%s>' % (prefix, uri))
                self.prefixes[prefix] = uri
            else:
                dialog.show()

    def openAddPrefixDialog(self):
        add_prefix_dialog = AddPrefixDialog()
        add_prefix_dialog.finished.connect(lambda accepted: self.addPrefix(accepted, add_prefix_dialog))
        add_prefix_dialog.setModal(True)
        add_prefix_dialog.show()

    def addPrefix(self, accepted, dialog):
        if accepted:
            if dialog.form_is_valid:
                self.prefixes[dialog.prefix_input.text().strip()] = dialog.uri_input.text()
                self.fillPrefixes()
            else:
                dialog.show()

    def openPrefixDbDialog(self):
        prefix_db_dialog = PrefixDbDialog(self, self.logger)
        prefix_db_dialog.setModal(True)
        prefix_db_dialog.show()
