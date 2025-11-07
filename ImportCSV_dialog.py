import os
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from PyQt5 import uic

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ImportCSV_dialog.ui'))

class ImportCSVdialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(ImportCSVdialog, self).__init__(parent)        
        self.setupUi(self)