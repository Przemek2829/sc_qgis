import os.path

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QTreeWidgetItem
from qgis.core import *
from rdflib import Graph, Literal, RDF, Namespace, URIRef, XSD

from .sc_export_layers_dialog import ExportLayersDialog
from .sc_names import ScNames as scn
from .sc_logger_mode import SCLoggerMode

rdf_formats = {'RDF/XML': 'xml',
               'Turtle': 'ttl',
               'N-Triples': 'nt'}
wgs_crs = QgsCoordinateReferenceSystem('EPSG:4326')


class ExportLayersManager:
    def __init__(self, project, dockwidget, logger):
        self.project = project
        self.dockwidget = dockwidget
        self.logger = logger
        self.export_config = {}
        self.dialog = ExportLayersDialog(project, self.export_config)
        self.layer_metadata_map = {scn.OUTPUT_LAYER_NAME.value: '',
                                   scn.RDF_TYPES.value: ['http://www.opengis.net/ont/geosparql#Feature'],
                                   scn.INCLUDE_DEFAULT_TYPE.value: 'True'}

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
        if rdf_export_path == '':
            self.dockwidget.browse_button.click()
        g = Graph()
        base_namespace = Namespace(self.dockwidget.base_uri_input.text())
        opengis_namespace = Namespace('http://www.opengis.net/ont/')
        geosparql_namespace = Namespace('http://www.opengis.net/ont/geosparql#')
        for layer_id, layer_config in self.export_config.items():
            if layer_config[0] == 2:
                layer_metadata = layer_config[3]
                layer = self.project.mapLayer(layer_id)
                pk = self.getPK(layer, layer_config)
                geom_type = QgsWkbTypes.displayString(layer.wkbType())
                tr_wgs = QgsCoordinateTransform(layer.crs(), wgs_crs, self.project)
                fields_config = layer_config[1]
                geom_config = layer_config[2]['geometry']
                rdf_types = []
                for rdf_type in layer_metadata[scn.RDF_TYPES.value]:
                    rdf_types.append(URIRef(rdf_type))
                for feature in layer.getFeatures():
                    if pk is None:
                        pk_value = feature.id()
                    else:
                        pk_value = feature.attribute(pk)
                    feature_uri = base_namespace['%s' % pk_value]
                    for rdf_namespace in rdf_types:
                        g.add((feature_uri, RDF.type, rdf_namespace))
                    if layer_metadata[scn.INCLUDE_DEFAULT_TYPE.value] == 'True':
                        g.add(
                            (feature_uri, RDF.type, base_namespace['%s' % layer_metadata[scn.OUTPUT_LAYER_NAME.value]]))
                    for field, field_config in fields_config.items():
                        if field_config[0] == 2:
                            config_custom_uri = field_config[1][scn.CUSTOM_URI.value]
                            if config_custom_uri == '':
                                predicate = base_namespace[field_config[1][scn.OUTPUT_FIELD_NAME.value]]
                            else:
                                predicate = URIRef(config_custom_uri)
                            literal_type = field_config[1][scn.LITERAL_TYPE.value]
                            g.add((feature_uri, predicate, Literal(feature.attribute(field), datatype=literal_type)))
                    if geom_config[0] == 2:
                        feature_geom = feature.geometry()
                        feature_geom.transform(tr_wgs)
                        geom_uri = base_namespace['%s#geometry' % pk_value]
                        geom_predicate = geosparql_namespace['hasGeometry']
                        g.add((feature_uri, geom_predicate, geom_uri))
                        g.add((geom_uri, RDF.type, opengis_namespace['sf#%s' % geom_type]))
                        if geom_config[1][scn.GEOSPARQL_WKT.value] == 'True':
                            g.add((geom_uri, geosparql_namespace['asWKT'],
                                   Literal(feature_geom.asWkt(), datatype=geosparql_namespace['wktLiteral'])))
                        if geom_type == 'Point' and geom_config[1][scn.WGS84_BASIC_GEO.value] == 'True':
                            feature_geom_point = feature_geom.asPoint()
                            lon = feature_geom_point.x()
                            lat = feature_geom_point.y()
                            g.add((feature_uri, URIRef('http://www.w3.org/2003/01/geo/wgs84_pos#lat'),
                                   Literal(lat, datatype=XSD.double)))
                            g.add((feature_uri, URIRef('http://www.w3.org/2003/01/geo/wgs84_pos#long'),
                                   Literal(lon, datatype=XSD.double)))

        rdf_export_path = self.dockwidget.file_path_input.text().strip()
        if rdf_export_path != '':
            rdf_format = rdf_formats[self.dockwidget.rdf_notation_combo.currentText()]
            try:
                g.serialize(destination=os.path.normpath(rdf_export_path), format=rdf_format, encoding='utf-8')
                self.logger.logMessage('SC QGIS', 'RDF export succeed', Qgis.Success,
                                       SCLoggerMode.loud)
            except Exception as e:
                self.logger.logMessage('SC QGIS', 'Export error: %s' % e, Qgis.Critical,
                                       SCLoggerMode.loud)
        else:
            self.logger.logMessage('SC QGIS', 'Specify the path for saving RDF data', Qgis.Warning,
                                   SCLoggerMode.loud)

    def getPK(self, layer, layer_config):
        for field, field_configs in layer_config[1].items():
            if field_configs[1]['Uri Key'] == 'True':
                return field
        pk_indexes = layer.dataProvider().pkAttributeIndexes()
        if len(pk_indexes) > 0:
            return pk_indexes[0]
        return None
