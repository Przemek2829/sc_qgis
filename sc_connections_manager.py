import os.path
import json

from qgis.PyQt.QtCore import Qt, QSize
from qgis.PyQt.QtGui import QIcon
from qgis.core import *
from SPARQLWrapper import SPARQLWrapper, JSON
import rdflib

from .sc_logger_mode import SCLoggerMode
from .sc_add_connection_dialog import AddConnectionDialog
from .sc_connections_dialog import ConnectionsDialog
CONNECTIONS_DIR = os.path.join(os.path.dirname(__file__), 'connections')


class ConnectionsManager:
    def __init__(self, dockwidget, logger):
        if not os.path.exists(CONNECTIONS_DIR):
            os.mkdir(CONNECTIONS_DIR)
        self.dockwidget = dockwidget
        self.logger = logger
        self.connections_file = os.path.join(CONNECTIONS_DIR, 'connections.json')
        self.connections = {}
        self.loadConnections()
        self.connection_types_map = {'SPARQL Endpoint': 'endpoint',
                                     'endpoint': 'SPARQL Endpoint',
                                     'Local File': 'file',
                                     'file': 'Local File'}
        self.connector = None

    def loadConnections(self):
        self.dockwidget.active_connection_combo.clear()
        self.dockwidget.active_connection_combo.addItem('')
        try:
            with open(self.connections_file) as connections_file:
                self.connections = json.load(connections_file)
                for key, value in self.connections.items():
                    self.dockwidget.active_connection_combo.addItem(key)
        except:
            pass

    def connect(self, connection_name):
        connection_data = self.connections.get(connection_name)
        if connection_data.get('type') == 'endpoint':
            self.connector = SPARQLWrapper(connection_data['url'])
            credentials = connection_data.get('credentials', [])
            if len(credentials) == 2:
                self.connector.setCredentials(credentials[0], credentials[1])
        elif connection_data.get('type') == 'file':
            self.connector = rdflib.Graph()
            self.connector.parse(connection_data['url'])

    def testConnection(self, add_connection_dialog, show_log=True):
        connected = False
        query = 'SELECT * WHERE{?s ?p ?o} LIMIT 0'
        connection_type = self.connection_types_map.get(add_connection_dialog.type_combo.currentText())
        url = add_connection_dialog.url_input.text()
        if connection_type == 'endpoint':
            connector = SPARQLWrapper(url)
            try:
                connector.setQuery(query)
                connector.setReturnFormat(JSON)
                query_output = connector.query().convert()
                query_output['results']['bindings']
                connected = True
            except:
                connected = False
        if connection_type == 'file':
            connector = rdflib.Graph()
            try:
                connector.parse(url)
                qresult = connector.query(query)
                query_output = qresult.bindings
                connected = True
            except:
                connected = False
        if connected:
            if show_log:
                self.logger.logMessage('SC QGIS', 'Connected',
                                       Qgis.Success, SCLoggerMode.loud)
        else:
            self.logger.logMessage('SC QGIS', 'Connection failed',
                                   Qgis.Critical, SCLoggerMode.loud)
        return connected

    def openConnectionDialog(self, add_connection_dialog):
        if add_connection_dialog is None:
            add_connection_dialog = AddConnectionDialog(self)
        add_connection_dialog.setModal(True)
        add_connection_dialog.finished.connect(lambda accepted: self.addConnection(accepted, add_connection_dialog))
        add_connection_dialog.show()

    def addConnection(self, accepted, add_connection_dialog):
        if accepted:
            if add_connection_dialog.form_is_valid and self.testConnection(add_connection_dialog, False):
                connection_name = add_connection_dialog.name_input.text()
                connection_type = self.connection_types_map[add_connection_dialog.type_combo.currentText()]
                connection_url = add_connection_dialog.url_input.text()
                credentials = []
                if add_connection_dialog.use_authentication_check.checkState() == 2:
                    connection_user = add_connection_dialog.user_input.text()
                    connection_password = add_connection_dialog.password_input.text()
                    credentials = [connection_user, connection_password]
                self.connections[connection_name] = {"type": connection_type,
                                                     "url": connection_url,
                                                     "credentials": credentials,
                                                     "prefixes": add_connection_dialog.prefixes}
                with open(self.connections_file, 'w') as connections_file:
                    json.dump(self.connections, connections_file, ensure_ascii=False)
                self.loadConnections()
            else:
                add_connection_dialog.show()

    def showConnections(self):
        connections_dialog = ConnectionsDialog(self)
        connections_dialog.setModal(True)
        connections_dialog.show()

    def showPrefixes(self):
        connection_name = self.dockwidget.active_connection_combo.currentText()
        if connection_name != '':
            connections_dialog = AddConnectionDialog(self)
            connections_info = self.connections.get(connection_name)
            for prefix, uri in connections_info.get('prefixes').items():
                connections_dialog.prefixes[prefix] = uri
            connections_dialog.openPrefixesDialog(connection_name)
