import os
import re

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtCore import QSettings as qs
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt import uic
import sys

from .sc_names import ScNames as scn

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_geom_variable_dialog.ui'), resource_suffix='')
VALID_COLOR = 'color: rgb(0, 0, 0);'
EMPTY_COLOR = 'color: rgb(125, 125, 125);'
INVALID_COLOR = 'color: rgb(255, 0, 0);'


class GeomVariableDialog(QDialog, FORM_CLASS):
    def __init__(self, dockwidget, parent=None):
        """Constructor."""
        super(GeomVariableDialog, self).__init__(parent)
        self.setupUi(self)
        self.resizeEvent = self.adjustSize
        self.dockwidget = dockwidget
        self.finished.connect(self.saveChanges)
        self.geom_button.clicked.connect(
            lambda checked: self.changeVariableType(checked, self.geom_button, scn.GEOMETRY.value))
        self.lon_lat_button.clicked.connect(
            lambda checked: self.changeVariableType(checked, self.lon_lat_button, scn.LON_LAT.value))
        self.geom_input.textChanged.connect(self.validateForm)
        self.lon_input.textChanged.connect(self.validateForm)
        self.lat_input.textChanged.connect(self.validateForm)
        self.form_is_valid = False
        self.loadSettings()

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.main_widget.resize(width - 10, height - 10)

    def loadSettings(self):
        settings = qs()
        geom_variable = settings.value(scn.SC_GEOM.value)
        if geom_variable is not None:
            if geom_variable == scn.GEOMETRY.value:
                self.geom_button.setChecked(True)
                self.geom_input.setEnabled(True)
                self.geom_input.setText(settings.value(scn.GEOMETRY_VARIABLE.value))
                self.lon_lat_button.setChecked(False)
                self.lon_input.setEnabled(False)
                self.lat_input.setEnabled(False)
            if geom_variable == scn.LON_LAT.value:
                self.lon_lat_button.setChecked(True)
                self.lon_input.setEnabled(True)
                self.lat_input.setEnabled(True)
                self.lon_input.setText(settings.value(scn.GEOMETRY_VARIABLE.value)[0])
                self.lat_input.setText(settings.value(scn.GEOMETRY_VARIABLE.value)[1])
                self.geom_button.setChecked(False)
                self.geom_input.setEnabled(False)
        self.validateForm()

    def saveChanges(self):
        if self.form_is_valid:
            if self.geom_button.isChecked():
                qs().setValue(scn.SC_GEOM.value, scn.GEOMETRY.value)
                qs().setValue(scn.GEOMETRY_VARIABLE.value, self.geom_input.text())
                self.dockwidget.geom_variable_button.setIcon(self.geom_button.icon())
            if self.lon_lat_button.isChecked():
                qs().setValue(scn.SC_GEOM.value, scn.LON_LAT.value)
                qs().setValue(scn.GEOMETRY_VARIABLE.value, [self.lon_input.text(), self.lat_input.text()])
                self.dockwidget.geom_variable_button.setIcon(self.lon_lat_button.icon())
        else:
            self.show()

    def changeVariableType(self, checked, button, variable_type):
        if checked:
            if variable_type == scn.GEOMETRY.value:
                self.geom_input.setEnabled(checked)
                self.lon_lat_button.setChecked(not checked)
                self.lon_input.setEnabled(not checked)
                self.lat_input.setEnabled(not checked)
            elif variable_type == scn.LON_LAT.value:
                self.lon_input.setEnabled(checked)
                self.lat_input.setEnabled(checked)
                self.geom_button.setChecked(not checked)
                self.geom_input.setEnabled(not checked)
            self.validateForm()
        else:
            button.setChecked(True)

    def validateForm(self):
        valid_pattern = '^[a-zA-Z0-9_]+$'
        if self.geom_button.isChecked():
            geom = self.geom_input.text().strip()
            geom_valid = re.match(valid_pattern, geom)
            self.setInputStylesheet(self.geom_input, geom, geom_valid)
            self.form_is_valid = geom_valid
        elif self.lon_lat_button.isChecked():
            lon = self.lon_input.text().strip()
            lat = self.lat_input.text().strip()
            lon_valid = re.match(valid_pattern, lon)
            lat_valid = re.match(valid_pattern, lat)
            self.setInputStylesheet(self.lon_input, lon, lon_valid)
            self.setInputStylesheet(self.lat_input, lat, lat_valid)
            self.form_is_valid = lon_valid and lat_valid

    def setInputStylesheet(self, widget, value, valid):
        if valid:
            widget.setStyleSheet(VALID_COLOR)
        elif value == '':
            widget.setStyleSheet(EMPTY_COLOR)
        else:
            widget.setStyleSheet(INVALID_COLOR)
