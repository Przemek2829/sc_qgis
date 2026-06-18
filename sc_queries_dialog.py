import os
import sys
from collections import OrderedDict
import json
import re

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon, QFont, QTextCursor
from qgis.PyQt.QtWidgets import QDialog, QTreeWidgetItem, QPushButton, QWidget, QHBoxLayout, QLabel, QMessageBox, \
    QInputDialog, QPlainTextEdit
from qgis.PyQt import uic
from qgis.core import *

from .sc_logger_mode import SCLoggerMode
from .sc_messenger import Messenger as msg
from .sc_sparqlhighlighter import SPARQLHighlighter

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_queries_dialog.ui'), resource_suffix='')
PASTE_ICON = QIcon(':/plugins/sc_qgis/paste.png')
EDIT_ICON = QIcon(':/plugins/sc_qgis/edit.png')
REMOVE_ICON = QIcon(':/plugins/sc_qgis/remove.png')
WIDGET_HEIGHT = 20


class QueriesDialog(QDialog, FORM_CLASS):
    def __init__(self, query_manager, logger, parent=None):
        """Constructor."""
        super(QueriesDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.qm = query_manager
        self.logger = logger
        self.queries_tree.itemClicked.connect(self.showQueryMetadata)
        try:
            with open(self.qm.queries_file) as file:
                self.queries = json.load(file)
        except:
            self.queries = {}
        self.fillQueries()

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.container_widget.resize(width - 20, height - 20)

    def fillQueries(self):
        self.queries_tree.clear()
        for query_name in self.queries.keys():
            query_item = QTreeWidgetItem(self.queries_tree)
            self.createItemWidget(query_item, query_name)

    def createItemWidget(self, query_item, query_name):
        container = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        query_label = QLabel(query_name)
        query_label.setObjectName('query_label')
        paste_button = self.createButton(PASTE_ICON, query_name, query_item)
        edit_button = self.createButton(EDIT_ICON, query_name, query_item)
        remove_button = self.createButton(REMOVE_ICON, query_name, query_item)
        layout.addWidget(query_label)
        layout.addWidget(paste_button)
        layout.addWidget(edit_button)
        layout.addWidget(remove_button)
        container.setLayout(layout)
        self.queries_tree.setItemWidget(query_item, 0, container)

    def createButton(self, icon, query_name, query_item):
        button = QPushButton(icon, '')
        button.setMaximumSize(QSize(20, 20))
        button.setMinimumSize(QSize(20, 20))
        if icon == PASTE_ICON:
            button.clicked.connect(lambda: self.pasteQuery(query_name))
        if icon == EDIT_ICON:
            button.clicked.connect(lambda: self.openEditQueryDialog(query_name, query_item))
        if icon == REMOVE_ICON:
            button.clicked.connect(lambda: self.removeQuery(query_name, query_item))
        return button

    def pasteQuery(self, query_name):
        write_query = True
        current_query = self.qm.dockwidget.query_text_edit.toPlainText().strip()
        if len(current_query) > 0:
            return_value = msg.createMessage("Overwrite query", QMessageBox.Question,
                                             "Query window not empty. Continue anyway?")
            write_query = return_value == QMessageBox.Ok
        if write_query:
            query_metadata = self.queries.get(query_name)
            query_text = query_metadata.get('query_text')
            self.qm.dockwidget.query_text_edit.setPlainText(query_text)
            self.qm.dockwidget.query_text_edit.moveCursor(QTextCursor.End)

    def openEditQueryDialog(self, query_name, item):
        dialog = QInputDialog()
        dialog.setModal(True)
        dialog.setWindowTitle('Change Query Name')
        dialog.setLabelText('Enter new query name')
        dialog.finished.connect(lambda accepted: self.editQuery(accepted, query_name, dialog, item))
        dialog.show()

    def editQuery(self, accepted, old_name, dialog, item):
        if accepted:
            new_name = dialog.textValue().strip()
            if new_name != '':
                if old_name != new_name:
                    query = self.queries.get(old_name)
                    del self.queries[old_name]
                    self.queries[new_name] = query
                    with open(self.qm.queries_file, 'w') as file:
                        json.dump(self.queries, file, ensure_ascii=False)
                    item_widget = self.queries_tree.itemWidget(item, 0)
                    item_widget.findChild(QLabel, 'query_label').setText(new_name)
                    self.createItemWidget(item, new_name)
                    self.showQueryMetadata(item, 0)
                    self.logger.logMessage('SC QGIS', 'Query name changed (%s -> %s)' % (old_name, new_name),
                                           Qgis.Success, SCLoggerMode.loud)
                else:
                    self.logger.logMessage('SC QGIS', 'Query name \"%s\" has not changed' % old_name, Qgis.Info,
                                           SCLoggerMode.quiet)
            else:
                dialog.show()

    def removeQuery(self, query_name, item):
        return_value = msg.createMessage("Remove query", QMessageBox.Question,
                                         "Action will cause permanent changes. Continue anyway?")
        if return_value == QMessageBox.Ok:
            del self.queries[query_name]
            with open(self.qm.queries_file, 'w') as file:
                json.dump(self.queries, file, ensure_ascii=False)
            idx = self.queries_tree.indexOfTopLevelItem(item)
            self.queries_tree.takeTopLevelItem(idx)
            self.metadata_label.setText('')
            self.metadata_tree.clear()

    def showQueryMetadata(self, item, column):
        item_widget = self.queries_tree.itemWidget(item, 0)
        query_name = item_widget.findChild(QLabel, 'query_label').text()
        query_metadata = self.queries.get(query_name)

        self.metadata_label.setText('Query: %s' % query_name)

        self.metadata_tree.clear()
        connection_group_item = QTreeWidgetItem(self.metadata_tree)
        connection_group_item.setText(0, 'Connection name')
        connection_item = QTreeWidgetItem(connection_group_item)
        connection_name = query_metadata.get('connection', 'Undefined').strip()
        connection_name = 'Undefined' if connection_name == '' else connection_name
        connection_item.setText(0, connection_name)
        query_text = query_metadata.get('query_text')
        select_where = re.sub('^select(.*)where\\s*{.*$', r'\1', query_text.replace('\n', ' '), flags=re.IGNORECASE)
        variables = set(re.findall('\\?[^\\s\t\r\n]+', select_where))
        variables_group_item = QTreeWidgetItem(self.metadata_tree)
        variables_group_item.setText(0, 'Variables')
        for variable in variables:
            variable_item = QTreeWidgetItem(variables_group_item)
            variable_item.setText(0, variable)
        query_group_item = QTreeWidgetItem(self.metadata_tree)
        query_group_item.setText(0, 'Query text')
        query_item = QTreeWidgetItem(query_group_item)
        query_plain_text = QPlainTextEdit()
        sparqlhighlight = SPARQLHighlighter(query_plain_text)
        query_plain_text.setPlainText(query_text)
        query_plain_text.setReadOnly(True)
        query_plain_text.setFont(QFont('Courier New'))
        self.metadata_tree.setItemWidget(query_item, 0, query_plain_text)
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
