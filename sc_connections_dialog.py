import os
import sys
import json

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLabel, QMessageBox
from qgis.PyQt import uic
from qgis.core import *

from .sc_add_connection_dialog import AddConnectionDialog
from .sc_messenger import Messenger as msg

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_connections_dialog.ui'), resource_suffix='')
EDIT_ICON = QIcon(':/plugins/sc_qgis/edit.png')
REMOVE_ICON = QIcon(':/plugins/sc_qgis/remove.png')
WIDGET_HEIGHT = 20


class ConnectionsDialog(QDialog, FORM_CLASS):
    def __init__(self, connections_manager, parent=None):
        """Constructor."""
        super(ConnectionsDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.cm = connections_manager
        self.fillConnections()
        self.connections_tree.itemClicked.connect(self.showConnectionMetadata)

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.container_widget.resize(width - 20, height - 20)

    def fillConnections(self):
        self.connections_tree.clear()
        for connection_name, connection_metadata in self.cm.connections.items():
            connection_item = QTreeWidgetItem(self.connections_tree)
            self.createItemWidget(connection_item, connection_name)

    def createItemWidget(self, connection_item, connection_name):
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        connection_label = QLabel(connection_name)
        connection_label.setObjectName('connection_label')
        edit_button = self.createButton(EDIT_ICON, connection_name, connection_item)
        remove_button = self.createButton(REMOVE_ICON, connection_name, connection_item)
        layout.addWidget(connection_label)
        layout.addWidget(edit_button)
        layout.addWidget(remove_button)
        container.setLayout(layout)
        self.connections_tree.setItemWidget(connection_item, 0, container)

    def createButton(self, icon, connection_name, connection_item):
        button = QPushButton(icon, '')
        button.setMaximumSize(QSize(20, 20))
        button.setMinimumSize(QSize(20, 20))
        if icon == EDIT_ICON:
            button.clicked.connect(lambda: self.openEditConnectionDialog(connection_name, connection_item))
        if icon == REMOVE_ICON:
            button.clicked.connect(lambda: self.removeConnection(connection_name, connection_item))
        return button

    def removeConnection(self, connection_name, item):
        return_value = msg.createMessage("Remove connection", QMessageBox.Question,
                                         "Action will cause permanent changes. Continue anyway?")
        if return_value == QMessageBox.Ok:
            del self.cm.connections[connection_name]
            with open(self.cm.connections_file, 'w') as connections_file:
                json.dump(self.cm.connections, connections_file, ensure_ascii=False)
            idx = self.connections_tree.indexOfTopLevelItem(item)
            self.connections_tree.takeTopLevelItem(idx)
            self.cm.loadConnections()
            self.metadata_label.setText('')
            self.metadata_tree.clear()

    def openEditConnectionDialog(self, connection_name, connection_item):
        edit_connection_dialog = AddConnectionDialog(self.cm)
        edit_connection_dialog.setWindowTitle('Edit Connection')
        connections_info = self.cm.connections.get(connection_name)
        edit_connection_dialog.name_input.setText(connection_name)
        edit_connection_dialog.type_combo.setCurrentText(self.cm.connection_types_map.get(connections_info.get('type')))
        edit_connection_dialog.url_input.setText(connections_info.get('url'))
        credentials = connections_info.get('credentials')
        if len(credentials) == 2:
            edit_connection_dialog.use_authentication_check.setCheckState(2)
            edit_connection_dialog.user_input.setText(credentials[0])
            edit_connection_dialog.password_input.setText(credentials[1])
        for prefix, uri in connections_info.get('prefixes').items():
            edit_connection_dialog.prefixes[prefix] = uri
        edit_connection_dialog.setModal(True)
        edit_connection_dialog.finished.connect(
            lambda accepted: self.editConnection(accepted, edit_connection_dialog, connection_name, connection_item))
        edit_connection_dialog.show()

    def editConnection(self, accepted, edit_connection_dialog, old_connection_name, connection_item):
        if accepted:
            if edit_connection_dialog.form_is_valid:
                connection_name = edit_connection_dialog.name_input.text()
                if old_connection_name != connection_name:
                    del self.cm.connections[old_connection_name]
                connection_type = self.cm.connection_types_map.get(edit_connection_dialog.type_combo.currentText())
                connection_url = edit_connection_dialog.url_input.text()
                credentials = []
                if edit_connection_dialog.use_authentication_check.checkState() == 2:
                    connection_user = edit_connection_dialog.user_input.text()
                    connection_password = edit_connection_dialog.password_input.text()
                    credentials = [connection_user, connection_password]
                self.cm.connections[connection_name] = {"type": connection_type,
                                                        "url": connection_url,
                                                        "credentials": credentials,
                                                        "prefixes": edit_connection_dialog.prefixes}
                with open(self.cm.connections_file, 'w') as connections_file:
                    json.dump(self.cm.connections, connections_file, ensure_ascii=False)
                item_widget = self.connections_tree.itemWidget(connection_item, 0)
                item_widget.findChild(QLabel, 'connection_label').setText(connection_name)
                self.createItemWidget(connection_item, connection_name)
                self.cm.loadConnections()
                self.showConnectionMetadata(connection_item, 0)
            else:
                edit_connection_dialog.show()

    def showConnectionMetadata(self, item, column):
        item_widget = self.connections_tree.itemWidget(item, 0)
        connection_name = item_widget.findChild(QLabel, 'connection_label').text()
        connection_metadata = self.cm.connections.get(connection_name)

        self.metadata_label.setText('Connection: %s' % connection_name)

        self.metadata_tree.clear()
        type_group_item = QTreeWidgetItem(self.metadata_tree)
        type_group_item.setText(0, 'Connection type')
        type_item = QTreeWidgetItem(type_group_item)
        type_item.setText(0, self.cm.connection_types_map.get(connection_metadata.get('type')))
        url_group_item = QTreeWidgetItem(self.metadata_tree)
        url_group_item.setText(0, 'URL')
        url_item = QTreeWidgetItem(url_group_item)
        url_item.setText(0, connection_metadata.get('url'))
        prefixes = connection_metadata.get('prefixes', [])
        if len(prefixes) > 0:
            prefixes_item = QTreeWidgetItem(self.metadata_tree)
            prefixes_item.setText(0, 'Prefixes')
            for prefix_name, prefix_uri in prefixes.items():
                prefix_item = QTreeWidgetItem(prefixes_item)
                prefix_item.setText(0, '%s: <%s>' % (prefix_name, prefix_uri))
        self.expandAndChangeSizeHint()

    def expandAndChangeSizeHint(self):
        root_item = self.metadata_tree.invisibleRootItem()
        for i in range(0, root_item.childCount()):
            group_item = root_item.child(i)
            group_item.setSizeHint(0, QSize(1, WIDGET_HEIGHT))
            self.metadata_tree.expandItem(group_item)
            for j in range(0, group_item.childCount()):
                value_item = group_item.child(j)
                value_item.setSizeHint(0, QSize(1, WIDGET_HEIGHT))
