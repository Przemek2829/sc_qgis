import os.path

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QTreeWidgetItem
from qgis.core import *
from rdflib import Graph, Literal, RDF, Namespace, URIRef, XSD

from .sc_export_layers_dialog import ExportLayersDialog
from .sc_names import ScNames as scn
from .sc_logger_mode import SCLoggerMode
from .sc_export_task import ExportTask

rdf_formats = {'RDF/XML': 'xml',
               'Turtle': 'ttl',
               'N-Triples': 'nt'}
wgs_crs = QgsCoordinateReferenceSystem('EPSG:4326')


class ExportLayersManager:
    def __init__(self, iface, project, dockwidget, logger):
        self.iface = iface
        self.project = project
        self.dockwidget = dockwidget
        self.logger = logger
        self.export_config = {}
        self.dialog = ExportLayersDialog(project, self.export_config)
        self.task_manager = QgsApplication.taskManager()
        self.layer_metadata_map = {scn.OUTPUT_LAYER_NAME.value: '',
                                   scn.RDF_TYPES.value: ['http://www.opengis.net/ont/geosparql#Feature'],
                                   scn.INCLUDE_DEFAULT_TYPE.value: 'True'}
        self.project.layerRemoved.connect(self.removeExportLayer)

    def removeExportLayer(self, layerid):
        try:
            del self.export_config[layerid]
        except:
            pass

    def loadExportLayers(self):
        self.dialog.layers_tree.clear()
        self.dialog.attributes_tree.clear()
        self.dialog.metadata_tree.clear()
        self.dialog.metadata_title_label.setText('')
        group_item = QTreeWidgetItem(self.dialog.layers_tree)
        group_item.setText(0, 'Layers')
        group_item.setCheckState(0, Qt.Unchecked)
        group_item.setSizeHint(0, QSize(1, 20))
        all_checked = True
        all_unchecked = True
        for layer in self.project.mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                layer_item = QTreeWidgetItem(group_item)
                layer_name = layer.name()
                layer_id = layer.id()
                layer_item.setText(0, layer_name)
                layer_item.setData(0, 100, layer_id)
                config_layer = self.export_config.get(layer_id)
                state = Qt.Unchecked if config_layer is None else config_layer[0]
                if config_layer is None:
                    layer_metadata_map = self.layer_metadata_map.copy()
                    layer_metadata_map[scn.OUTPUT_LAYER_NAME.value] = layer_name
                    self.export_config[layer_id] = [state, {}, {}, layer_metadata_map]
                layer_item.setCheckState(0, state)
                layer_item.setSizeHint(0, QSize(1, 20))
                if all_checked and state == Qt.Unchecked:
                    all_checked = False
                if all_unchecked and state == Qt.Checked:
                    all_unchecked = False
        if all_checked:
            group_item.setCheckState(0, Qt.Checked)
        elif all_unchecked:
            group_item.setCheckState(0, Qt.Unchecked)
        else:
            group_item.setCheckState(0, Qt.PartiallyChecked)
        self.dialog.layers_tree.expandItem(group_item)
        self.dialog.setModal(True)
        self.dialog.show()
        self.dialog.artificialResize()

    def exportLayersToRDF(self):
        rdf_export_path = self.dockwidget.file_path_input.text().strip()
        if rdf_export_path != '':
            export_task = ExportTask(self.dockwidget, self.iface, self.project, self.export_config, self.logger, 'Export to RDF Task')
            self.task_manager.addTask(export_task)
        else:
            self.logger.logMessage('SC QGIS', 'Specify the path for saving RDF data', Qgis.Warning,
                                   SCLoggerMode.loud)

