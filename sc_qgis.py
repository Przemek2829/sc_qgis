from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import *
from .resources import *
import platform

from .sc_qgis_dockwidget import SemanticComponentsDockWidget
from .sc_export_layers_manager import ExportLayersManager
from .sc_connections_manager import ConnectionsManager
from .sc_query_manager import QueryManager
from .sc_logger import SCLogger
from .sc_logger_mode import SCLoggerMode
import os


class SemanticComponents:

    def __init__(self, iface):
        self.iface = iface
        self.project = QgsProject.instance()
        self.export_layers_dialog = None
        self.export_layers_manager = None
        self.connections_manager = None
        self.query_manager = None
        self.logger = None
        self.plugin_dir = os.path.dirname(__file__)
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SemanticComponents_{}.qm'.format(locale))
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        self.actions = []
        self.menu = self.tr(u'&SC QGIS Plugin')
        self.pluginIsActive = False
        self.dockwidget = None

    def tr(self, message):
        return QCoreApplication.translate('SemanticComponents', message)

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        self.actions.append(action)
        return action

    def initGui(self):
        icon_path = ':/plugins/sc_qgis/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Manage spatial and graph data'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def onClosePlugin(self):
        self.dockwidget.closingPlugin.disconnect(self.onClosePlugin)
        self.pluginIsActive = False

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&SC QGIS Plugin'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.pluginIsActive:
            self.pluginIsActive = True
            if self.dockwidget is None:
                self.dockwidget = SemanticComponentsDockWidget()
                self.logger = SCLogger(self.iface)
                self.export_layers_manager = ExportLayersManager(self.project, self.dockwidget, self.logger)
                self.connections_manager = ConnectionsManager(self.dockwidget, self.logger)
                self.query_manager = QueryManager(self.project, self.dockwidget, self.connections_manager, self.logger)
                self.dockwidget.manual_button.clicked.connect(self.openManual)
                self.dockwidget.run_query_button.clicked.connect(self.query_manager.runQuery)
                self.dockwidget.add_connection_button.clicked.connect(lambda: self.connections_manager.openConnectionDialog(None))
                self.dockwidget.show_connections_button.clicked.connect(self.connections_manager.showConnections)
                self.dockwidget.prefix_button.clicked.connect(self.connections_manager.showPrefixes)
                self.dockwidget.geom_variable_button.clicked.connect(self.query_manager.openGeomVariableDialog)
                self.dockwidget.save_query_button.clicked.connect(self.query_manager.startSaveQuery)
                self.dockwidget.save_format_button.clicked.connect(self.query_manager.openSaveFormatDialog)
                self.dockwidget.queries_dir_button.clicked.connect(self.query_manager.openQueriesDir)
                self.dockwidget.show_queries_button.clicked.connect(self.query_manager.openSavedQueriesDialog)
                self.dockwidget.load_export_layers_button.clicked.connect(self.export_layers_manager.loadExportLayers)
                self.dockwidget.export_button.clicked.connect(self.export_layers_manager.exportLayersToRDF)

            self.dockwidget.closingPlugin.connect(self.onClosePlugin)

            self.iface.addTabifiedDockWidget(Qt.BottomDockWidgetArea, self.dockwidget, [], True)
            self.dockwidget.show()
            self.dockwidget.artificialResize()

    def openManual(self):
        manual_path = os.path.join(self.plugin_dir, 'manual.pdf')
        if platform.system() == "Windows":
            os.startfile(manual_path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", manual_path])
        else:
            subprocess.Popen(["xdg-open", manual_path])
