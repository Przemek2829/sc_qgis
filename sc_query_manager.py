import os
import re
import operator
import json
from osgeo import ogr
import platform
import subprocess

from qgis.PyQt.QtCore import Qt, QSize, QSettings as qs
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox
from qgis.core import *
from SPARQLWrapper import JSON

from .sc_logger_mode import SCLoggerMode
from .sc_layers_manager import LayersManager
from .sc_geom_variable_dialog import GeomVariableDialog
from .sc_save_format_dialog import SaveFormatDialog
from .sc_queries_dialog import QueriesDialog
from .sc_messenger import Messenger as msg
from .sc_names import ScNames as scn

GEOSPARQL_URI = 'http://www.opengis.net/ont/geosparql#'
CRS_URI = '<http://www.opengis.net/def/crs/EPSG/0/'
WGS_EPSG = 'EPSG:4326'
QUERY_DIR = os.path.join(os.path.dirname(__file__), 'queries')
QUERIES_DIR = os.path.join(os.path.dirname(__file__), 'query_results')


class QueryManager:
    def __init__(self, project, dockwidget, connections_manager, logger):
        if not os.path.exists(QUERY_DIR):
            os.mkdir(QUERY_DIR)
        self.project = project
        self.dockwidget = dockwidget
        self.logger = logger
        self.connections_manager = connections_manager
        self.setDefaultSettings()
        self.layers_manager = LayersManager(project, logger)
        self.queries_file = os.path.join(QUERY_DIR, 'queries.json')

    def setDefaultSettings(self):
        settings = qs()
        if settings.value(scn.SC_SAVE_FORMAT.value) is None:
            settings.setValue(scn.SC_SAVE_FORMAT.value, scn.GEOJSON.value)
        if settings.value(scn.SC_GEOM.value) is None:
            settings.setValue(scn.SC_GEOM.value, scn.GEOMETRY.value)
            settings.setValue(scn.GEOMETRY_VARIABLE.value, scn.GEOMETRY.value)

    def openQueriesDir(self):
        if platform.system() == "Windows":
            os.startfile(QUERIES_DIR)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", QUERIES_DIR])
        else:
            subprocess.Popen(["xdg-open", QUERIES_DIR])

    def runQuery(self):
        connection_name = self.dockwidget.active_connection_combo.currentText()
        if connection_name != '':
            connection_data = self.connections_manager.connections.get(connection_name)
            connection_type = connection_data.get('type')
            prefixes = ''
            for prefix, uri in connection_data.get('prefixes').items():
                prefixes += 'PREFIX %s: <%s>\n' % (prefix, uri)
            query = self.dockwidget.query_text_edit.toPlainText().strip()
            if query != '':
                query = prefixes + query
                self.connections_manager.connect(connection_name)
                try:
                    if connection_type == 'endpoint':
                        self.connections_manager.connector.setQuery(query)
                        self.connections_manager.connector.setReturnFormat(JSON)
                        query_output = self.connections_manager.connector.query().convert()['results']['bindings']
                    else:
                        qresult = self.connections_manager.connector.query(query)
                        query_output = qresult.bindings
                    features, layer_crs = self.getRDFFeatures(query_output, connection_type)
                    layer_name = self.dockwidget.layer_name_input.text().strip()
                    layer_name = connection_name if layer_name == '' else layer_name
                    for geom_type, features_data in features.items():
                        self.layers_manager.generateRDFLayer(layer_name, features_data, geom_type, layer_crs)
                except Exception as e:
                    self.logger.logMessage('SC QGIS', 'Query error: %s' % e, Qgis.Critical, SCLoggerMode.loud)
            else:
                self.logger.logMessage('SC QGIS', 'SPARQL query is empty', Qgis.Info, SCLoggerMode.loud)
        else:
            self.logger.logMessage('SC QGIS', 'No connection selected', Qgis.Info, SCLoggerMode.loud)

    def getRDFFeatures(self, query_output, connection_type):
        settings = qs()
        sc_geom = settings.value(scn.SC_GEOM.value)
        features = {}
        layer_crss = {}
        for bindings in query_output:
            feature = {}
            geometry_types = set()
            geometry_type = None
            found_geometries_counter = 1
            if sc_geom == scn.LON_LAT.value:
                lon_lat_variable = settings.value(scn.GEOMETRY_VARIABLE.value)
                lon_data = bindings.get(lon_lat_variable[0])
                lat_data = bindings.get(lon_lat_variable[1])
                if lon_data is not None and lat_data is not None:
                    try:
                        if connection_type == 'endpoint':
                            lon = float(lon_data.get('value'))
                            lat = float(lat_data.get('value'))
                        elif connection_type == 'file':
                            lon = float(str(lon_data))
                            lat = float(str(lat_data))
                        geometry = ogr.Geometry(ogr.wkbPoint)
                        geometry.AddPoint(lon, lat)
                        geometry.FlattenTo2D()
                        feature[scn.GEOMETRY.value] = [WGS_EPSG, geometry.ExportToWkt()]
                        crs_count = layer_crss.get(WGS_EPSG, 0)
                        layer_crss[WGS_EPSG] = crs_count + 1
                        geometry_type = geometry.GetGeometryName()
                    except:
                        if connection_type == 'endpoint':
                            feature[lon_lat_variable[0]] = [lon_data.get('datatype', 'String'), lon_data.get('value')]
                            feature[lon_lat_variable[1]] = [lat_data.get('datatype', 'String'), lat_data.get('value')]
                        elif connection_type == 'file':
                            try:
                                lon_data_type = lon_data.datatype
                            except:
                                lon_data_type = 'String'
                            try:
                                lat_data_type = lat_data.datatype
                            except:
                                lat_data_type = 'String'
                            feature[lon_lat_variable[0]] = [lon_data_type, str(lon_data)]
                            feature[lon_lat_variable[1]] = [lat_data_type, str(lat_data)]
                else:
                    if lon_data is not None:
                        if connection_type == 'endpoint':
                            feature[lon_lat_variable[0]] = [lon_data.get('datatype', 'String'), lon_data.get('value')]
                        elif connection_type == 'file':
                            try:
                                lon_data_type = lon_data.datatype
                            except:
                                lon_data_type = 'String'
                            feature[lon_lat_variable[0]] = [lon_data_type, str(lon_data)]
                    if lat_data is not None:
                        if connection_type == 'endpoint':
                            feature[lon_lat_variable[1]] = [lat_data.get('datatype', 'String'), lat_data.get('value')]
                        elif connection_type == 'file':
                            try:
                                lat_data_type = lat_data.datatype
                            except:
                                lat_data_type = 'String'
                            feature[lon_lat_variable[1]] = [lat_data_type, str(lat_data)]
            if sc_geom == scn.GEOMETRY.value:
                geom_variable = settings.value(scn.GEOMETRY_VARIABLE.value)
                geom_data = bindings.get(geom_variable)
                if geom_data is not None:
                    if connection_type == 'endpoint':
                        geom_data_type = geom_data.get('datatype', 'String')
                        geom_data_value = geom_data.get('value')
                    elif connection_type == 'file':
                        geom_data_value = str(geom_data)
                        try:
                            geom_data_type = str(geom_data.datatype)
                        except:
                            geom_data_type = 'String'
                    if GEOSPARQL_URI in geom_data_type:
                        geometry_representation = geom_data_type.replace(GEOSPARQL_URI, '')
                        geometry_value = re.sub('(%s\\d+>)?(.*)' % CRS_URI, r'\2', geom_data_value).strip()
                        geometry_crs = 'EPSG:%s' % re.sub('(%s)?(\\d+)?(>)?(.*)' % CRS_URI, r'\2',
                                                          geom_data_value).strip()
                        geometry_crs = WGS_EPSG if geometry_crs == '' else geometry_crs
                        crs_count = layer_crss.get(geometry_crs, 0)
                        layer_crss[geometry_crs] = crs_count + 1
                        if geometry_representation == 'gmlLiteral':
                            geometry = ogr.CreateGeometryFromGml(geometry_value)
                        elif geometry_representation == 'wkbLiteral':
                            geometry = ogr.CreateGeometryFromWkb(geometry_value)
                        elif geometry_representation == 'wktLiteral':
                            geometry = ogr.CreateGeometryFromWkt(geometry_value)
                        elif geometry_representation == 'geojsonLiteral':
                            geometry = ogr.CreateGeometryFromJson(geometry_value)
                        else:
                            geometry = None
                        if geometry is not None:
                            geometry_type = geometry.GetGeometryName()
                            feature['geometry'] = [geometry_crs, geometry.ExportToWkt()]
                        else:
                            feature['geometry'] = [None, None]
            if connection_type == 'endpoint':
                for binding, data in bindings.items():
                    data_type = data.get('datatype', 'String')
                    data_value = data.get('value')
                    if binding != settings.value(scn.GEOMETRY_VARIABLE.value):
                        feature[binding] = [data_type, data_value]
            elif connection_type == 'file':
                for binding in bindings:
                    data_value = str(bindings.get(binding))
                    try:
                        data_type = str(data_value.datatype)
                    except:
                        data_type = 'String'
                    binding_str = str(binding)
                    if binding_str != settings.value(scn.GEOMETRY_VARIABLE.value):
                        feature[binding_str] = [data_type, data_value]
            features_by_geom = features.get(geometry_type, [])
            features_by_geom.append(feature)
            features[geometry_type] = features_by_geom
        layer_crs = max(layer_crss.items(), key=operator.itemgetter(1))[0] if len(layer_crss) > 0 else None
        return features, layer_crs

    def openGeomVariableDialog(self):
        dialog = GeomVariableDialog(self.dockwidget)
        dialog.setModal(True)
        dialog.show()

    def startSaveQuery(self):
        query_text = self.dockwidget.query_text_edit.toPlainText().strip()
        if query_text != '':
            dialog = QInputDialog()
            dialog.setModal(True)
            dialog.setWindowTitle('Set Query Name')
            dialog.setLabelText('Enter query name')
            dialog.finished.connect(lambda accepted: self.saveQuery(accepted, dialog))
            dialog.show()
        else:
            self.logger.logMessage('SC QGIS', 'Query is empty', Qgis.Info, SCLoggerMode.loud)

    def saveQuery(self, accepted, dialog):
        if accepted:
            query_name = dialog.textValue().strip()
            if query_name != '':
                try:
                    with open(self.queries_file) as file:
                        queries = json.load(file)
                except:
                    queries = {}
                save_query = False
                query_text = self.dockwidget.query_text_edit.toPlainText()
                query = {'connection': self.dockwidget.active_connection_combo.currentText(),
                         'query_text': query_text}
                if queries.get(query_name) is not None:
                    return_value = msg.createMessage("Query exists", QMessageBox.Question,
                                                     "Query with name <b>\"%s\"</b> already exists. Do you want to continue?" % query_name)
                    if return_value == QMessageBox.Ok:
                        queries[query_name] = query
                        save_query = True
                else:
                    queries[query_name] = query
                    save_query = True
                if save_query:
                    with open(self.queries_file, 'w') as file:
                        json.dump(queries, file, ensure_ascii=False)
                    self.logger.logMessage('SC QGIS', 'Query saved', Qgis.Success, SCLoggerMode.loud)
            else:
                dialog.show()

    def openSaveFormatDialog(self):
        dialog = SaveFormatDialog(self.dockwidget)
        dialog.setModal(True)
        dialog.show()

    def openSavedQueriesDialog(self):
        dialog = QueriesDialog(self, self.logger)
        dialog.setModal(True)
        dialog.show()
