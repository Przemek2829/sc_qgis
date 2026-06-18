import os

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import *
from qgis.core import *
import sys

from .sc_url_validator import SCUrlValidator as url_validator
from .sc_rdf_types_dialog import RdfTypesDialog
from .sc_names import ScNames as scn

sys.path.append(os.path.dirname(__file__))

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sc_export_layers_dialog.ui'), resource_suffix='')

PK_ICON = QIcon(':/plugins/sc_qgis/pk.png')
WIDGET_HEIGHT = 25
WIDGET_STYLESHEET = 'text-align: left;font-weight:bold;margin-top: 2.5;margin-bottom: 2.5;margin-right: 2.5'
GEOM_TYPES = ['Point', 'Line', 'Polygon']
XML_SCHEMA_TYPES = {'boolean': ('%sboolean' % scn.XML_SCHEMA_BASE_URI.value),
                    'integer64': ('%sinteger' % scn.XML_SCHEMA_BASE_URI.value),
                    'integer': ('%sinteger' % scn.XML_SCHEMA_BASE_URI.value),
                    'real': ('%sdecimal' % scn.XML_SCHEMA_BASE_URI.value),
                    'double': ('%sdecimal' % scn.XML_SCHEMA_BASE_URI.value),
                    'json': ('%sstring' % scn.XML_SCHEMA_BASE_URI.value),
                    'text': ('%sstring' % scn.XML_SCHEMA_BASE_URI.value),
                    'string': ('%sstring' % scn.XML_SCHEMA_BASE_URI.value),
                    'duration': ('%sduration' % scn.XML_SCHEMA_BASE_URI.value),
                    'time': ('%stime' % scn.XML_SCHEMA_BASE_URI.value),
                    'date': ('%sdate' % scn.XML_SCHEMA_BASE_URI.value),
                    'datetime': ('%sdateTime' % scn.XML_SCHEMA_BASE_URI.value),
                    'bytes': ('%sbytes' % scn.XML_SCHEMA_BASE_URI.value),
                    'binary': ('%sbytes' % scn.XML_SCHEMA_BASE_URI.value),
                    'blob': ('%sbytes' % scn.XML_SCHEMA_BASE_URI.value)
                    }


class ExportLayersDialog(QDialog, FORM_CLASS):
    def __init__(self, project, export_config, parent=None):
        """Constructor."""
        super(ExportLayersDialog, self).__init__(parent)
        self.project = project
        self.export_config = export_config
        self.setupUi(self)
        screen = QApplication.primaryScreen()
        container_layout = self.container_widget.layout()

        layers_tree = container_layout.takeAt(0)
        attributes_tree = container_layout.takeAt(0)
        metadata_widget = container_layout.takeAt(0)
        splitter = QSplitter()
        splitter.addWidget(layers_tree.widget())
        splitter.addWidget(attributes_tree.widget())
        splitter.addWidget(metadata_widget.widget())
        container_layout.addWidget(splitter)

        self.resize(screen.size().width() - 100, self.size().height())
        self.resizeEvent = self.adjustSize
        self.layers_tree.itemClicked.connect(self.manageCheckState)
        self.layers_tree.itemClicked.connect(self.showLayerFields)
        self.layers_tree.itemClicked.connect(self.showLayerMetadata)
        self.attributes_tree.itemClicked.connect(self.showAttributeMetadata)
        self.attributes_tree.itemClicked.connect(self.changeAttributesCheckState)
        self.field_metadata_map = {scn.OUTPUT_FIELD_NAME.value: '',
                                   scn.LITERAL_TYPE.value: '',
                                   scn.INCLUDE_DEFAULT_RDF_TYPE.value: 'True',
                                   scn.CUSTOM_URI.value: '',
                                   scn.AS_RELATION.value: 'False',
                                   scn.URI_KEY.value: 'False'}
        self.geometry_metadata_map = {scn.WGS84_BASIC_GEO.value: 'False',
                                      scn.GEOSPARQL_WKT.value: 'True'}
        self.rdf_types_dialog = RdfTypesDialog()
        self.rdf_types_dialog.finished.connect(self.getRdfTypes)
        self.select_all_attributes.stateChanged.connect(self.toggleAttributesState)

    def adjustSize(self, event):
        width = event.size().width()
        height = event.size().height()
        self.container_widget.resize(width - 20, height - 20)
        tree_width = self.attributes_tree.size().width()
        self.attributes_tree.header().setMinimumSectionSize(int(tree_width / 2) - 5)
        self.attributes_tree.header().setMaximumSectionSize(int(tree_width / 2) - 5)
        self.attributes_tree.header().setDefaultSectionSize(int(tree_width / 2) - 5)
        self.metadata_tree.header().setMinimumSectionSize(int(tree_width / 2) - 5)
        self.metadata_tree.header().setMaximumSectionSize(int(tree_width / 2) - 5)
        self.metadata_tree.header().setDefaultSectionSize(int(tree_width / 2) - 5)

    def artificialResize(self):
        self.resize(self.size().width() - 1, self.size().height() - 1)
        self.resize(self.size().width() + 1, self.size().height() + 1)

    def toggleAttributesState(self, state):
        attributes_root = self.attributes_tree.invisibleRootItem()
        for i in range(0, attributes_root.childCount()):
            attribute_item = attributes_root.child(i)
            attribute_item.setCheckState(0, state)
            self.changeAttributesCheckState(attribute_item, 0)

    def manageCheckState(self, item, column):
        if item.parent() is None:
            item_state = item.checkState(0)
            if item_state != Qt.PartiallyChecked:
                for i in range(0, item.childCount()):
                    child = item.child(i)
                    child.setCheckState(0, item_state)
                    layer_id = child.data(0, 100)
                    self.export_config[layer_id][0] = item_state
                    self.showLayerFields(child, 0)
        else:
            parent_item = item.parent()
            all_checked = True
            all_unchecked = True
            for i in range(0, parent_item.childCount()):
                child = parent_item.child(i)
                layer_id = child.data(0, 100)
                check_state = child.checkState(0)
                self.export_config[layer_id][0] = check_state
                if all_checked and check_state == Qt.Unchecked:
                    all_checked = False
                if all_unchecked and check_state == Qt.Checked:
                    all_unchecked = False
            if all_checked:
                parent_item.setCheckState(0, Qt.Checked)
            elif all_unchecked:
                parent_item.setCheckState(0, Qt.Unchecked)
            else:
                parent_item.setCheckState(0, Qt.PartiallyChecked)

    def showLayerFields(self, item, column):
        layer = self.project.mapLayer(item.data(0, 100))
        self.attributes_tree.clear()
        if layer is not None:
            layer_id = layer.id()
            geom_config = self.export_config[layer_id][2]
            geom_type = QgsWkbTypes.geometryDisplayString(layer.geometryType())
            geom_item = self.createFieldTreeItem(scn.GEOM_FIELD.value, geom_type, layer_id)
            if geom_config.get(scn.GEOM_FIELD.value) is None:
                geom_item.setCheckState(0, Qt.Unchecked)
                geom_config[scn.GEOM_FIELD.value] = [Qt.Unchecked, self.geometry_metadata_map]
            else:
                geom_item.setCheckState(0, geom_config[scn.GEOM_FIELD.value][0])
            pk_indexes = layer.dataProvider().pkAttributeIndexes()
            pk_index = None if len(pk_indexes) == 0 else pk_indexes[0]
            fields_config = self.export_config[layer_id][1]
            checked_items = 0
            for c, field in enumerate(layer.fields()):
                field_name = field.displayName()
                field_item = self.createFieldTreeItem(field_name, field.typeName(), layer_id)
                is_pk = c == pk_index
                if fields_config.get(field_name) is None:
                    field_item.setCheckState(0, Qt.Unchecked)
                    self.createFieldConfigMetadata(fields_config, field_name, is_pk)
                    if is_pk:
                        field_item.setIcon(0, PK_ICON)
                else:
                    check_state = fields_config[field_name][0]
                    field_item.setCheckState(0, check_state)
                    if check_state == 2:
                        checked_items = checked_items + 1
                    if fields_config.get(field_name)[1][scn.URI_KEY.value] == 'True':
                        field_item.setIcon(0, PK_ICON)
            c += 1
            if checked_items == c:
                self.select_all_attributes.setCheckState(2)
            else:
                self.select_all_attributes.setCheckState(0)

    def createFieldTreeItem(self, field_name, field_type, layer_id):
        field_item = QTreeWidgetItem(self.attributes_tree)
        field_item.setText(0, field_name)
        field_item.setText(1, field_type)
        field_item.setData(0, 100, layer_id)
        field_item.setSizeHint(0, QSize(1, 20))
        field_item.setSizeHint(1, QSize(1, 20))
        return field_item

    def createFieldConfigMetadata(self, config_fields, field_name, is_pk):
        field_metadata_map = self.field_metadata_map.copy()
        field_metadata_map[scn.OUTPUT_FIELD_NAME.value] = field_name
        field_metadata_map[scn.URI_KEY.value] = str(is_pk)
        field_config = [Qt.Unchecked, field_metadata_map]
        config_fields[field_name] = field_config

    def showLayerMetadata(self, item, column):
        layer = self.project.mapLayer(item.data(0, 100))
        self.metadata_tree.clear()
        self.metadata_title_label.setText('')
        if layer is not None:
            layer_name = layer.name()
            layer_id = layer.id()
            layer_config_metadata = self.export_config[layer_id][3]
            geom_type = QgsWkbTypes.geometryDisplayString(layer.geometryType())

            self.metadata_title_label.setText('Layer: %s' % layer_name)

            # Create metadata tree widgets
            group_item = QTreeWidgetItem(self.metadata_tree)
            group_item.setText(0, 'Layer')
            self.createMetadataTreeItem(group_item, 'Source layer', layer_name)
            self.createMetadataTreeItem(group_item, 'Available features', str(layer.featureCount()))
            output_layer_name_item = QTreeWidgetItem(group_item)
            output_layer_name_item.setText(0, scn.OUTPUT_LAYER_NAME.value)
            layer_line_edit = self.createMetadataWidget(QLineEdit(layer_config_metadata[scn.OUTPUT_LAYER_NAME.value]),
                                                        layer_id, layer_config_metadata, scn.OUTPUT_LAYER_NAME.value)
            self.metadata_tree.setItemWidget(output_layer_name_item, 1, layer_line_edit)
            self.createMetadataTreeItem(group_item, 'Geometry type', geom_type)
            uri_key_item = QTreeWidgetItem(group_item)
            uri_key_item.setText(0, scn.URI_KEY.value)
            uri_key = ''
            attributes_root_item = self.attributes_tree.invisibleRootItem()
            for i in range(0, attributes_root_item.childCount()):
                child = attributes_root_item.child(i)
                if not child.icon(0).isNull():
                    uri_key = '%s (%s)' % (child.text(0), child.text(1))
            uri_key_item.setText(1, uri_key)
            rdf_types_button = self.createMetadataWidget(QPushButton(' Click to add...'), layer_id,
                                                         layer_config_metadata, scn.RDF_TYPES.value)
            self.createMetadataTreeItem(group_item, 'RDF types', None, rdf_types_button)
            include_default_type_combo = self.createMetadataWidget(QComboBox(), layer_id, layer_config_metadata,
                                                                   scn.INCLUDE_DEFAULT_TYPE.value)
            self.createMetadataTreeItem(group_item, scn.INCLUDE_DEFAULT_TYPE.value, None, include_default_type_combo)

            self.metadata_tree.expandItem(group_item)
            self.changeItemsSizeHint(group_item)

    def showAttributeMetadata(self, item, column):
        field_name = item.text(0)
        field_type = item.text(1)
        layer_id = item.data(0, 100)
        self.metadata_tree.clear()

        if field_type in GEOM_TYPES:
            geom_config_metadata = self.export_config[layer_id][2][scn.GEOM_FIELD.value][1]
            self.metadata_title_label.setText('Geometry: %s' % field_name)

            # Create metadata tree widgets
            geometry_group_item = QTreeWidgetItem(self.metadata_tree)
            geometry_group_item.setText(0, 'Geometry')
            self.createMetadataTreeItem(geometry_group_item, 'Geometry name', field_name)
            self.createMetadataTreeItem(geometry_group_item, 'Geometry type', field_type)
            output_geometry_group_item = QTreeWidgetItem(self.metadata_tree)
            output_geometry_group_item.setText(0, 'Output geometry')
            wgs84_basic_geo_combo = self.createMetadataWidget(QComboBox(), layer_id, geom_config_metadata,
                                                              scn.WGS84_BASIC_GEO.value,
                                                              field_name, 2)
            self.createMetadataTreeItem(output_geometry_group_item, scn.WGS84_BASIC_GEO.value, None,
                                        wgs84_basic_geo_combo)
            geosparql_combo = self.createMetadataWidget(QComboBox(), layer_id, geom_config_metadata,
                                                        scn.GEOSPARQL_WKT.value,
                                                        field_name, 2)
            self.createMetadataTreeItem(output_geometry_group_item, scn.GEOSPARQL_WKT.value, None, geosparql_combo)

            self.metadata_tree.expandItem(geometry_group_item)
            self.changeItemsSizeHint(geometry_group_item)
            self.metadata_tree.expandItem(output_geometry_group_item)
            self.changeItemsSizeHint(output_geometry_group_item)
        else:
            field_config = self.export_config[layer_id][1].get(field_name, None)
            self.metadata_title_label.setText('Field: %s' % field_name)

            # Create metadata tree widgets
            if field_config:
                field_config_metadata = field_config[1]
                group_item = QTreeWidgetItem(self.metadata_tree)
                group_item.setText(0, 'Field')
                self.createMetadataTreeItem(group_item, 'Field name', field_name)
                output_field_line_edit = self.createMetadataWidget(
                    QLineEdit(field_config_metadata[scn.OUTPUT_FIELD_NAME.value]),
                    layer_id, field_config_metadata, scn.OUTPUT_FIELD_NAME.value,
                    field_name, 1)
                self.createMetadataTreeItem(group_item, scn.OUTPUT_FIELD_NAME.value, None, output_field_line_edit)
                self.createMetadataTreeItem(group_item, 'Type', field_type)
                literal_type_combo = self.createMetadataWidget(QLineEdit(), layer_id, field_config_metadata,
                                                               scn.LITERAL_TYPE.value,
                                                               field_name, 1, set(XML_SCHEMA_TYPES.values()),
                                                               field_type.lower())
                self.createMetadataTreeItem(group_item, scn.LITERAL_TYPE.value, None, literal_type_combo)
                include_default_rdf_type_combo = self.createMetadataWidget(QComboBox(), layer_id, field_config_metadata,
                                                                           scn.INCLUDE_DEFAULT_RDF_TYPE.value, field_name,
                                                                           1)
                self.createMetadataTreeItem(group_item, scn.INCLUDE_DEFAULT_RDF_TYPE.value, None,
                                            include_default_rdf_type_combo)
                custom_uri_line_edit = self.createMetadataWidget(QLineEdit(field_config_metadata[scn.CUSTOM_URI.value]),
                                                                 layer_id,
                                                                 field_config_metadata, scn.CUSTOM_URI.value, field_name, 1)
                custom_uri_line_edit.textEdited.connect(lambda uri: url_validator.validateUrl(uri, custom_uri_line_edit))
                self.createMetadataTreeItem(group_item, scn.CUSTOM_URI.value, None, custom_uri_line_edit)
                as_relation_combo = self.createMetadataWidget(QComboBox(), layer_id, field_config_metadata,
                                                              scn.AS_RELATION.value,
                                                              field_name, 1)
                self.createMetadataTreeItem(group_item, scn.AS_RELATION.value, None, as_relation_combo)
                uri_key_combo = self.createMetadataWidget(QComboBox(), layer_id, field_config_metadata, scn.URI_KEY.value,
                                                          field_name, 1)
                self.createMetadataTreeItem(group_item, scn.URI_KEY.value, None, uri_key_combo)

                self.metadata_tree.expandItem(group_item)
                self.changeItemsSizeHint(group_item)

    def createMetadataTreeItem(self, parent_item, label, value, widget=None):
        metadata_item = QTreeWidgetItem(parent_item)
        metadata_item.setText(0, label)
        if widget is None:
            metadata_item.setText(1, value)
        else:
            self.metadata_tree.setItemWidget(metadata_item, 1, widget)

    def createMetadataWidget(self, widget, layer_id, config_metadata, key, field_name=None, idx=None, items=None,
                             field_type=None):
        widget.setMaximumHeight(WIDGET_HEIGHT)
        widget.setStyleSheet(WIDGET_STYLESHEET)
        widget_class = widget.metaObject().className()
        if widget_class == 'QComboBox':
            if items is None:
                widget.addItems(['True', 'False'])
                widget.setCurrentText(config_metadata[key])
            if field_name is None:
                widget.currentTextChanged.connect(
                    lambda: self.layerMeatadataChanged(layer_id, key, widget.currentText()))
            else:
                widget.currentTextChanged.connect(
                    lambda: self.attributeMetadataChanged(layer_id, field_name, key,
                                                          widget.currentText(), idx))
        elif widget_class == 'QLineEdit':
            widget.setClearButtonEnabled(True)
            if items is not None:
                completer = QCompleter(items)
                completer.setFilterMode(Qt.MatchContains)
                completer.setCaseSensitivity(Qt.CaseInsensitive)
                widget.setCompleter(completer)
                if config_metadata[key] == '':
                    widget.setText(XML_SCHEMA_TYPES.get(field_type, ''))
                    config_metadata[key] = XML_SCHEMA_TYPES.get(field_type, '')
                else:
                    widget.setText(config_metadata[key])
            if field_name is None:
                widget.editingFinished.connect(
                    lambda: self.layerMeatadataChanged(layer_id, key, widget.text()))
            else:
                widget.editingFinished.connect(
                    lambda: self.attributeMetadataChanged(layer_id, field_name, key, widget.text(), idx, widget))
        elif widget_class == 'QPushButton':
            widget.clicked.connect(lambda: self.openRdfTypesDialog(layer_id, config_metadata, key))
        return widget

    def openRdfTypesDialog(self, layer_id, config_metadata, key):
        if layer_id is not None:
            self.rdf_types_dialog.layer_id = layer_id
            self.rdf_types_dialog.config_metadata = config_metadata
            self.rdf_types_dialog.config_metadata_key = key
            self.rdf_types_dialog.uri_tree.clear()
            for rdf_type in config_metadata[scn.RDF_TYPES.value][1:]:
                self.rdf_types_dialog.addUri(rdf_type)
        self.rdf_types_dialog.setModal(True)
        self.rdf_types_dialog.show()

    def getRdfTypes(self):
        uri_tree = self.rdf_types_dialog.uri_tree
        uri_root_item = uri_tree.invisibleRootItem()
        layer_config_metadata = self.export_config[self.rdf_types_dialog.layer_id][3]
        rdf_types = layer_config_metadata[scn.RDF_TYPES.value][0:1]
        uris_valid = True
        for i in range(uri_root_item.childCount()):
            uri_item = uri_root_item.child(i)
            uri_widget = uri_tree.itemWidget(uri_item, 0)
            uri_line_edit = uri_widget.findChild(QLineEdit, 'uri_edit', Qt.FindChildrenRecursively)
            uri = uri_line_edit.text()
            if not url_validator.validateUrl(uri, uri_line_edit):
                uris_valid = False
                break
            if uri not in rdf_types:
                rdf_types.append(uri)
        if uris_valid:
            layer_config_metadata[scn.RDF_TYPES.value] = rdf_types
        else:
            self.openRdfTypesDialog(None, None, None)

    def layerMeatadataChanged(self, layer_id, key, value):
        self.export_config[layer_id][3][key] = value

    def attributeMetadataChanged(self, layer_id, field_name, key, value, idx, widget=None):
        if key == scn.CUSTOM_URI.value:
            if url_validator.validateUrl(value, widget) or value.strip() == '':
                self.export_config[layer_id][idx][field_name][1][key] = value
        else:
            self.export_config[layer_id][idx][field_name][1][key] = value
        if key == scn.URI_KEY.value and value == 'True':
            for field_config_name in self.export_config[layer_id][1]:
                if field_config_name != field_name:
                    self.export_config[layer_id][1][field_config_name][idx][key] = 'False'
            attributes_root_item = self.attributes_tree.invisibleRootItem()
            for i in range(attributes_root_item.childCount()):
                attribute_item = attributes_root_item.child(i)
                if attribute_item.text(0) == field_name:
                    attribute_item.setIcon(0, PK_ICON)
                else:
                    attribute_item.setIcon(0, QIcon())

    def changeItemsSizeHint(self, group_item):
        group_item.setSizeHint(0, QSize(1, WIDGET_HEIGHT))
        for i in range(0, group_item.childCount()):
            child = group_item.child(i)
            child.setSizeHint(0, QSize(1, WIDGET_HEIGHT))
            child.setSizeHint(1, QSize(1, WIDGET_HEIGHT))

    def changeAttributesCheckState(self, item, column):
        if item.text(1) not in GEOM_TYPES:
            idx = 1
        else:
            idx = 2
        field_config = self.export_config[item.data(0, 100)][idx].get(item.text(0))
        if field_config:
            field_config[0] = item.checkState(0)
