from qgis.core import *
from PyQt5.QtCore import *
from qgis.PyQt.QtCore import QSettings as qs
import os
import re
from collections import OrderedDict

from .sc_logger_mode import SCLoggerMode
from .sc_names import ScNames as scn

TYPES_MAP = {'String': QVariant.String}
SAVE_DIR = os.path.join(os.path.dirname(__file__), 'query_results')


class LayersManager:

    def __init__(self, project, logger):
        if not os.path.exists(SAVE_DIR):
            os.mkdir(SAVE_DIR)
        self.project = project
        self.logger = logger

    def generateRDFLayer(self, layer_name, features_data, geom_type, layer_crs):
        structure = self.getLayerStructure(geom_type, features_data)
        layer = self.createLayer(layer_name, geom_type, layer_crs)
        self.addLayerFields(layer, structure)
        self.addLayerFeatures(layer, layer_crs, features_data, structure, geom_type)
        saved_layer = self.saveLayer(layer, geom_type)
        self.project.addMapLayer(saved_layer)

    def getLayerStructure(self, geom_type, features):
        structure = OrderedDict()
        for feature in features:
            data_complete = True
            for field_name, field_metadata in feature.items():
                if field_metadata is None or str(field_metadata).strip() == '':
                    data_complete = False
                if field_name != 'geometry' or (field_name == 'geometry' and geom_type is None):
                    structure[field_name] = TYPES_MAP.get(field_metadata[0], QVariant.String)
            if data_complete:
                break
        return structure

    def createLayer(self, layer_name, geom_type, layer_crs):
        if geom_type is None:
            layer = QgsVectorLayer('None', layer_name, 'memory')
        else:
            layer = QgsVectorLayer('%s?crs=%s' % (geom_type, layer_crs), layer_name, 'memory')
        return layer

    def addLayerFields(self, layer, structure):
        layer.startEditing()
        layer_provider = layer.dataProvider()
        fields = []
        for field_name, field_type in structure.items():
            field = QgsField(field_name, field_type, '', 0, 0, '')
            fields.append(field)
        layer_provider.addAttributes(fields)
        layer.commitChanges()

    def addLayerFeatures(self, layer, layer_crs, features_data, structure, geom_type):
        layer.startEditing()
        for feature_data in features_data:
            feature_attributes = []
            for attribute in structure.keys():
                feature_attributes.append(feature_data.get(attribute, [None, None])[1])
            feature = QgsFeature()
            feature.setAttributes(feature_attributes)
            if geom_type is not None:
                feature_geometry_data = feature_data.get('geometry')
                geometry_crs = feature_geometry_data[0]
                geometry_wkt = feature_geometry_data[1]
                feature_geometry = QgsGeometry.fromWkt(geometry_wkt)
                if geometry_crs != layer_crs:
                    feature_geometry_crs = QgsCoordinateReferenceSystem(geometry_crs)
                    tr = QgsCoordinateTransform(feature_geometry_crs, layer.sourceCrs(), self.project)
                    feature_geometry.transform(tr)
                feature.setGeometry(feature_geometry)
            layer.addFeature(feature)
        layer.commitChanges()

    def saveLayer(self, layer, geom_type):
        settings = qs()
        save_format = settings.value(scn.SC_SAVE_FORMAT.value)
        if save_format != scn.MEMORY.value:
            layer_name = layer.name()
            if geom_type is not None:
                save_file = os.path.join(SAVE_DIR, '%s_%s.%s' % (layer_name, geom_type.lower(), save_format.lower()))
            else:
                save_file = os.path.join(SAVE_DIR, '%s.%s' % (layer_name, save_format.lower()))
            save_options = QgsVectorFileWriter.SaveVectorOptions()
            save_options.driverName = save_format
            QgsVectorFileWriter.writeAsVectorFormat(layer, save_file, save_options)
            return QgsVectorLayer(save_file, layer_name, "ogr")
        return layer
