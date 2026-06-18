import os
from rdflib import Graph, Literal, RDF, Namespace, URIRef, XSD

from qgis.core import *

from .sc_names import ScNames as scn
from .sc_logger_mode import SCLoggerMode
from .sc_url_validator import SCUrlValidator as url_validator

MESSAGE_CATEGORY = 'SC QGIS'
rdf_formats = {'RDF/XML': 'xml',
               'Turtle': 'ttl',
               'N-Triples': 'nt'}
wgs_crs = QgsCoordinateReferenceSystem('EPSG:4326')


class ExportTask(QgsTask):
    def __init__(self, dockwidget, iface, project, export_config, logger, description):
        super().__init__(description, QgsTask.CanCancel)

        self.dockwidget = dockwidget
        self.iface = iface
        self.project = project
        self.export_config = export_config
        self.logger = logger
        self.exception = None

    def run(self):
        self.dockwidget.export_button.setEnabled(False)
        rdf_export_path = self.dockwidget.file_path_input.text().strip()
        if rdf_export_path == '':
            self.dockwidget.browse_button.click()
        g = Graph()
        base_namespace = Namespace(self.dockwidget.base_uri_input.text())
        opengis_namespace = Namespace('http://www.opengis.net/ont/')
        geosparql_namespace = Namespace('http://www.opengis.net/ont/geosparql#')
        status_bar = self.iface.statusBarIface()
        for layer_id, layer_config in self.export_config.items():
            if self.isCanceled():
                return False
            try:
                if layer_config[0] == 2:
                    layer_metadata = layer_config[3]
                    layer = self.project.mapLayer(layer_id)
                    layer_name = layer.name()
                    status_bar.showMessage("SC QGIS Export. Processing layer: %s" % layer_name)
                    self.setDescription('Export to RDF Task - %s' % layer_name)
                    pk = self.getPK(layer, layer_config)
                    geom_type = QgsWkbTypes.displayString(layer.wkbType())
                    tr_wgs = QgsCoordinateTransform(layer.crs(), wgs_crs, self.project)
                    fields_config = layer_config[1]
                    geom_config = layer_config[2]['geometry']
                    rdf_types = []
                    for rdf_type in layer_metadata[scn.RDF_TYPES.value]:
                        rdf_types.append(URIRef(rdf_type))
                    count = layer.featureCount()
                    for i, feature in enumerate(layer.getFeatures()):
                        if self.isCanceled():
                            return False
                        if pk is None:
                            pk_value = feature.id()
                        else:
                            pk_value = feature.attribute(pk)
                        feature_uri = base_namespace['%s' % pk_value]
                        for rdf_namespace in rdf_types:
                            g.add((feature_uri, RDF.type, rdf_namespace))
                        if layer_metadata[scn.INCLUDE_DEFAULT_TYPE.value] == 'True':
                            g.add((feature_uri, RDF.type, base_namespace['%s' % layer_metadata[scn.OUTPUT_LAYER_NAME.value]]))
                        for field, field_config in fields_config.items():
                            if field_config[0] == 2:
                                config_custom_uri = field_config[1][scn.CUSTOM_URI.value]
                                if config_custom_uri == '':
                                    predicate = base_namespace[field_config[1][scn.OUTPUT_FIELD_NAME.value]]
                                else:
                                    predicate = URIRef(config_custom_uri)
                                attribute = feature.attribute(field)
                                if field_config[1][scn.AS_RELATION.value] == 'True' and url_validator.validateUrl(str(attribute)):
                                    g.add((feature_uri, predicate, URIRef(attribute)))
                                else:
                                    literal_type = field_config[1][scn.LITERAL_TYPE.value]
                                    g.add((feature_uri, predicate, Literal(attribute, datatype=literal_type)))
                        if geom_config[0] == 2:
                            feature_geom = feature.geometry()
                            feature_geom.transform(tr_wgs)
                            geom_uri = base_namespace['%s_geometry' % pk_value]
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
                        percent = i / float(count) * 100
                        self.setProgress(percent)
            except Exception as e:
                self.exception = e
                return False
        status_bar.showMessage("Saving to RDF")
        self.setDescription('Export to RDF Task - saving to RDF')
        rdf_format = rdf_formats[self.dockwidget.rdf_notation_combo.currentText()]
        rdf_export_path = self.dockwidget.file_path_input.text().strip()
        try:
            g.serialize(destination=os.path.normpath(rdf_export_path), format=rdf_format, encoding='utf-8')
            return True
        except Exception as e:
            self.exception = e
            return False

    def getPK(self, layer, layer_config):
        for field, field_configs in layer_config[1].items():
            if field_configs[1]['Uri Key'] == 'True':
                return field
        pk_indexes = layer.dataProvider().pkAttributeIndexes()
        if len(pk_indexes) > 0:
            return pk_indexes[0]
        return None

    def finished(self, result):
        self.dockwidget.export_button.setEnabled(True)
        if result:
            self.logger.logMessage('SC QGIS', 'RDF export succeed', Qgis.Success, SCLoggerMode.loud)
        else:
            if self.exception is not None:
                self.logger.logMessage('SC QGIS', 'Export error: %s' % self.exception, Qgis.Critical, SCLoggerMode.loud)
        self.iface.statusBarIface().showMessage("")

    def cancel(self):
        self.logger.logMessage('SC QGIS', 'Export task canceled', Qgis.Info, SCLoggerMode.loud)
        super().cancel()
