from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from qgis.analysis import *
from PyQt5.QtCore import *
from PyQt5.QtXml import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

import shutil, os

MESSAGE_CATEGORY = 'Laag laden'

class LayerRepair(QgsTask):    
    def __init__(self, description, layer:QgsVectorLayer, schijfmap, cachemap, action):
        super().__init__(description, QgsTask.CanCancel)
        self.setDescription(description)
        self.layer = layer
        self.schijfmap = schijfmap
        self.cachemap = cachemap
        self.action = action
        self.exception = None
        self.message = None
        # self.klic_laden_projectnr(projectnr)

    def run(self):
        QgsMessageLog.logMessage(
                f"Actie {self.action} op laag {self.layer.name()}: kopiëren naar {self.cachemap if self.action == 'load' else self.schijfmap}",
                MESSAGE_CATEGORY, Qgis.Info)
        
        if self.layer.providerType().lower() in ('wfs', 'wms', 'wcs'):
            if self.action == 'load': # bij opslaan hoeft deze bron niet aangepast te worden
                self.layer.setDataSource(self.layer.source(), self.layer.name(), self.layer.providerType())
            return True
        else:
            try:
                if '|' in self.layer.source():
                    parts = self.layer.source().split('|')
                    file_path = parts[0]
                    package = '|'.join(parts[1:])
                    print(file_path, package)
                else:
                    raise Exception("'|' komt niet voor in bron van laag.")
            except Exception as e:
                print(f"Er ging iets mis bij het splitsen van het pad naar {self.layer.name()}: {e}")
                file_path = self.layer.source()
                package = None
            QgsMessageLog.logMessage(
                f"Huidige bron van {self.layer.name()}: {file_path}",
                MESSAGE_CATEGORY, Qgis.Info)
            projectfolder, filename = os.path.split(file_path)
            if self.action == 'load':
                newpath = os.path.join(self.cachemap, filename)
            elif self.action == 'save':
                newpath = os.path.join(self.schijfmap, filename)
                if newpath == file_path:
                    return True
            try:
                try:
                    newpath_ = shutil.copy(file_path, newpath)
                except:
                    newpath_ = shutil.copy(os.path.join(self.schijfmap, filename), newpath)
                self.layer.setDataSource(f"{newpath_}|{package}" if package is not None else newpath_, self.layer.name(), self.layer.providerType())
            except Exception as e:
                self.exception = f'Er ging iets mis bij het cachen van laag {self.layer.name()}: {e}'
                return False
        self.layer.setCrs(QgsCoordinateReferenceSystem('EPSG:28992'))
        # self.layer.updateExtents()
        return True            
    
    def finished(self, result):
        """This method is automatically called when self.run returns.
        result is the return value from self.run.
        This function is automatically called when the task has completed (
        successfully or otherwise). You just implement finished() to do 
        whatever
        follow up stuff should happen after the task is complete. finished is
        always called from the main thread, so it's safe to do GUI
        operations and raise Python exceptions here.
        """
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" uitgevoerd.'.format(
                    name=self.description),
                MESSAGE_CATEGORY, Qgis.Success)
                            
            if self.message != None:
                msg = QMessageBox()
                msg.setText(self.message)
                msg.setIcon(QMessageBox.Information) 
                msg.exec_()
            # Exec_klicladen.finished()
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without exception ' \
                    '(probably the task was manually canceled by the '
                    'user)'.format(
                        name=self.description),
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description, exception=self.exception),
                    MESSAGE_CATEGORY, Qgis.Critical)
                # msg = QMessageBox()
                # msg.setText(self.exception)
                # msg.setIcon(QMessageBox.Critical) 
                # msg.exec_()

    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was cancelled'.format(name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()

class Exec_repairlayer(QgsTask):
    def __init__(self, layer:QgsVectorLayer, schijfmap, cachemap, action):
        """Example of the class that needs to get tasks done. """
        """Subclassed examples. """
        self.layer = layer
        globals()[f'repairlayer_{layer.id()}'] = LayerRepair(f'Laag {layer.name()}', layer, schijfmap, cachemap, action)

    def run(self):
        """Do tasks using QgsTask subclass. """
        QgsApplication.taskManager().addTask(globals()[f'repairlayer_{self.layer.id()}']) # id gebruiken omdat naam niet uniek is