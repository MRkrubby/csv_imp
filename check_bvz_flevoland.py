from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from qgis.analysis import *
from PyQt5.QtCore import *
from PyQt5.QtXml import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from ..algemene_functies import filtercheck

MESSAGE_CATEGORY = 'Check boringsvrije zone Flevoland'

class CheckBVZ(QgsTask):
    def __init__(self, description, lagen, flags):
        self.exception = None
        self.boringen_m            = lagen[0]
        self.boringen_g            = lagen[1]
        self.sonderingen           = lagen[2]
        self.vast_punt             = lagen[3]
        self.overig                = lagen[4]
        self.flag_bm               = flags[0]
        self.flag_b                = flags[1]
        self.flag_s                = flags[2]
        self.flag_o                = flags[3]
        self.flag_vp               = flags[4]
        self.description = description
        super().__init__(description, QgsTask.CanCancel)

    def run(self):
        # try:
            # Geen onderscheid meer, checks worden nu bij elk project op elke laag uitgevoerd, maar lagen worden niet meegenomen als er geen punten in projectfase of combi worden gevonden
            # Controle op boringsvrije zone
            self.boringen_m.selectAll()
            self.boringen_g.selectAll()
            self.sonderingen.selectAll()
            self.vast_punt.selectAll()
            self.overig.selectAll()

            uri = QgsDataSourceUri()
            uri.setParam('url', 'https://geo2.flevoland.nl/geoserver/Extern/wfs')
            uri.setParam('typename', 'Extern:MI_BEHEER_BORINGSVRIJEZONEGRNS')
            uri.setParam('srsName', 'EPSG:28992')
            uri.setParam('service', 'wfs')
            uri.setParam('version', '1.1.0')
            bv_flevoland = QgsVectorLayer(uri.uri(), 'Boringsvrijezone Flevoland', "WFS")
            if not bv_flevoland.isValid():
                self.exception = 'Er ging iets mis bij het aanmaken van de laag boringsvrije zone Flevoland'
                return False
            onderzoekspunten = []
            if self.flag_bm == True:
                print('Boringen milieu wordt meegenomen in check Flevoland')
                onderzoekspunten = onderzoekspunten + self.boringen_m.selectedFeatures()
            if self.flag_b == True:
                print('Boringen geotechniek wordt meegenomen in check Flevoland')
                onderzoekspunten = onderzoekspunten + self.boringen_g.selectedFeatures()
            if self.flag_s == True:
                print('Sonderingen wordt meegenomen in check Flevoland')
                onderzoekspunten = onderzoekspunten + self.sonderingen.selectedFeatures()
            if self.flag_o == True:
                print('Overig wordt meegenomen in check Flevoland')
                onderzoekspunten = onderzoekspunten + self.overig.selectedFeatures()
            if self.flag_vp == True:
                print('Vast punt wordt meegenomen in check Flevoland')
                onderzoekspunten = onderzoekspunten + self.vast_punt.selectedFeatures()

            for f in bv_flevoland.getFeatures():
                for punt in onderzoekspunten:
                    geom = punt.geometry()
                    if geom.intersects(f.geometry()):
                        self.flag_punten = True
                        return True
            
            self.flag_punten = False
            return True
        # except Exception as e:
        #     self.exception = e
        #     return False

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
        self.deselectall()
        if result:
            QgsMessageLog.logMessage(
                'Task "{name}" completed'.format(
                    name=self.description),
                MESSAGE_CATEGORY, Qgis.Success)
            if self.flag_punten == True:
                self.msgbox()
            else:
               QgsMessageLog.logMessage(
                'Geen punten gevonden binnen boringsvrije zone Flevoland.',
                MESSAGE_CATEGORY, Qgis.Success) 
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
                msg = QMessageBox()
                msg.setText(str(self.exception))
                msg.setIcon(QMessageBox.Critical) 
                msg.exec_()
    
    def deselectall(self):
        self.boringen_m.removeSelection()
        self.boringen_g.removeSelection()
        self.sonderingen.removeSelection()
        self.vast_punt.removeSelection()
        self.overig.removeSelection()
    
    def msgbox(self):
        msg = QMessageBox()
        msg.setText(
            "Let op!\n\nEr zijn binnen dit project onderzoekspunten ingetekend in de boringsvrije zone Flevoland.\n\nEen melding bij de omgevingsdienst is verplicht. Ga naar:\n\nhttps://www.ofgv.nl/thema/bodem/boringsvrije-zone/meldingsformulier/")
        msg.setIcon(QMessageBox.Critical)
        msg.exec_()
    
    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was cancelled'.format(name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()  

class Exec_CheckBVZ:
    def __init__(self, lagen, flags):
        globals()['Flevoland'] = CheckBVZ('Check boringsvrije zone Flevoland', lagen, flags)

    def run(self):
        """Do tasks using QgsTask subclass. """
        QgsApplication.taskManager().addTask(globals()['Flevoland'])