# coding=utf-8
"""DockWidget test.

.. note:: This program is free software; you can redistribute it and/or modify
     it under the terms of the GNU General Public License as published by
     the Free Software Foundation; either version 2 of the License, or
     (at your option) any later version.

"""

__author__ = 'wizipisi@wizipisi.pl'
__date__ = '2023-02-05'
__copyright__ = 'Copyright 2023, WIZIPISI'

import unittest

from qgis.PyQt.QtGui import QDockWidget

from sc_qgis_dockwidget import SemanticComponentsDockWidget

from utilities import get_qgis_app

QGIS_APP = get_qgis_app()


class SemanticComponentsDockWidgetTest(unittest.TestCase):
    """Test dockwidget works."""

    def setUp(self):
        """Runs before each test."""
        self.dockwidget = SemanticComponentsDockWidget(None)

    def tearDown(self):
        """Runs after each test."""
        self.dockwidget = None

    def test_dockwidget_ok(self):
        """Test we can click OK."""
        pass

if __name__ == "__main__":
    suite = unittest.makeSuite(SemanticComponentsDialogTest)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)

