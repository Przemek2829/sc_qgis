import os
import sys
import re

from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QSettings as qs
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtGui import QIcon

from .sc_url_validator import SCUrlValidator as url_validator
from .sc_sparqlhighlighter import SPARQLHighlighter
from .sc_names import ScNames as scn

sys.path.append(os.path.dirname(__file__))
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_qgis_dockwidget_base.ui'), resource_suffix='')
extensions_map = {'RDF/XML': ['Resource Description Framework (*.rdf)', 'rdf'],
                  'Turtle': ['Turtle (*.ttl)', 'ttl'],
                  'N-Triples': ['N-Triples (*.nt)', 'nt']}
GEOM_ICON = QIcon(':/plugins/sc_qgis/geom_variable.png')
LON_LAT_ICON = QIcon(':/plugins/sc_qgis/lon_lat_variable.png')
GEOJSON_ICON = QIcon(':/plugins/sc_qgis/geojson.png')
GEOPACKAGE_ICON = QIcon(':/plugins/sc_qgis/geopackage.png')
MEMORY_ICON = QIcon(':/plugins/sc_qgis/memory.png')


class SemanticComponentsDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(SemanticComponentsDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.browse_button.clicked.connect(
            lambda: self.getPath(self.file_path_input, extensions_map[self.rdf_notation_combo.currentText()][0]))
        self.rdf_notation_combo.currentTextChanged.connect(self.changeFormat)
        self.base_uri_input.textEdited.connect(lambda uri: url_validator.validateUrl(uri, self.base_uri_input))
        self.query_text_edit.textChanged.connect(self.highlightSPARQL)
        self.query_text_edit.textChanged.connect(self.showLineNumber)
        self.sparqlhighlight = SPARQLHighlighter(self.query_text_edit)
        self.errorline = None
        self.setGeomVariableIcon()
        self.setFormatIcon()
        self.vertical_scroll_bar = self.query_text_edit.verticalScrollBar()
        self.vertical_scroll_bar.valueChanged.connect(self.scrollLineContainer)
        self.query_text_edit.textChanged.connect(self.scrollLineContainer)
        self.query_text_edit.cursorPositionChanged.connect(self.scrollLineContainer)

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        width = self.tabWidget.geometry().size().width()
        height = self.tabWidget.geometry().size().height()
        self.export_main_widget.resize(width - 20, height - 110)
        self.export_button.move(5, height - 70)
        self.query_widget.resize(width - 5, height - 70)

    def getPath(self, path_container, extension):
        selected_file = QFileDialog.getSaveFileName(self, "Wkaż miejsce zapisu RDF", "", extension)
        if selected_file[0] != "":
            path_container.setText(selected_file[0])

    def changeFormat(self, format_text):
        current_path = self.file_path_input.text().strip()
        if current_path != '':
            new_extension = extensions_map[format_text][1]
            new_path = re.sub('^(.*)\\.(.*)$', r'\1.%s' % new_extension, current_path)
            self.file_path_input.setText(new_path)

    def artificialResize(self):
        self.resize(self.size().width() - 1, self.size().height() - 1)
        self.resize(self.size().width() + 1, self.size().height() + 1)

    def scrollLineContainer(self, value=None):
        if value is None:
            value = self.vertical_scroll_bar.value()
        self.query_line_container.verticalScrollBar().setValue(value)

    def highlightSPARQL(self):
        query_text = self.query_text_edit.toPlainText()
        if query_text is not None and query_text != "":
            self.errorline = -1
            self.sparqlhighlight.errorhighlightline = self.errorline
            self.sparqlhighlight.currentline = 0
            self.errorline = None

    def showLineNumber(self):
        query_text = self.query_text_edit.toPlainText()
        line_text = ''
        for i, text in enumerate(query_text.split('\n'), 1):
            line_text += '%s\n' % i
        self.query_line_container.clear()
        self.query_line_container.insertPlainText(line_text)

    def setGeomVariableIcon(self):
        settings = qs()
        geom_variable = settings.value(scn.SC_GEOM.value)
        if geom_variable is not None:
            if geom_variable == scn.GEOMETRY.value:
                self.geom_variable_button.setIcon(GEOM_ICON)
            if geom_variable == scn.LON_LAT.value:
                self.geom_variable_button.setIcon(LON_LAT_ICON)

    def setFormatIcon(self):
        settings = qs()
        save_format_variable = settings.value(scn.SC_SAVE_FORMAT.value)
        if save_format_variable is not None:
            if save_format_variable == scn.GEOJSON.value:
                self.save_format_button.setIcon(GEOJSON_ICON)
            if save_format_variable == scn.GEOPACKAGE.value:
                self.save_format_button.setIcon(GEOPACKAGE_ICON)
            if save_format_variable == scn.MEMORY.value:
                self.save_format_button.setIcon(MEMORY_ICON)
