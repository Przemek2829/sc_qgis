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
    os.path.dirname(__file__), 'sc_save_format_dialog.ui'), resource_suffix='')


class SaveFormatDialog(QDialog, FORM_CLASS):
    def __init__(self, dockwidget, parent=None):
        """Constructor."""
        super(SaveFormatDialog, self).__init__(parent)
        self.setupUi(self)
        self.dockwidget = dockwidget
        self.finished.connect(self.saveChanges)
        self.geojson_button.clicked.connect(lambda checked: self.changeFormat(checked, self.geojson_button))
        self.geopackage_button.clicked.connect(lambda checked: self.changeFormat(checked, self.geopackage_button))
        self.memory_button.clicked.connect(lambda checked: self.changeFormat(checked, self.memory_button))
        self.buttons = [self.geojson_button, self.geopackage_button, self.memory_button]
        self.loadSettings()

    def loadSettings(self):
        settings = qs()
        save_format_variable = settings.value(scn.SC_SAVE_FORMAT.value)
        if save_format_variable is not None:
            if save_format_variable == scn.GEOJSON.value:
                self.geojson_button.setChecked(True)
            if save_format_variable == scn.GEOPACKAGE.value:
                self.geopackage_button.setChecked(True)
            if save_format_variable == scn.MEMORY.value:
                self.memory_button.setChecked(True)
        else:
            self.geojson_button.setChecked(True)

    def saveChanges(self):
        if self.geojson_button.isChecked():
            qs().setValue(scn.SC_SAVE_FORMAT.value, scn.GEOJSON.value)
            self.dockwidget.save_format_button.setIcon(self.geojson_button.icon())
        if self.geopackage_button.isChecked():
            qs().setValue(scn.SC_SAVE_FORMAT.value, scn.GEOPACKAGE.value)
            self.dockwidget.save_format_button.setIcon(self.geopackage_button.icon())
        if self.memory_button.isChecked():
            qs().setValue(scn.SC_SAVE_FORMAT.value, scn.MEMORY.value)
            self.dockwidget.save_format_button.setIcon(self.memory_button.icon())

    def changeFormat(self, checked, button):
        if checked:
            buttons = self.buttons.copy()
            buttons.remove(button)
            for btn in buttons:
                btn.setChecked(False)
        else:
            button.setChecked(True)
