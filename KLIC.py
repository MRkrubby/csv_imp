import os, time

from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from qgis.analysis import *
from PyQt5.QtCore import *
from PyQt5.QtXml import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import processing
import qgis
from ..algemene_functies import filtercheck, get_projectinfo

MESSAGE_CATEGORY = 'KLIC'

class Klicladen(QgsTask):    
    def __init__(self, description, projectnr, combiprojectnr, provider):
        super().__init__(description, QgsTask.CanCancel)
        self.projectnr = projectnr
        self.combiprojectnr = combiprojectnr
        self.provider = provider
        self.exception = None
        self.message = None
        # self.klic_laden_projectnr(projectnr)

    def run(self):
        QgsMessageLog.logMessage(
            'Task "{name}" started'.format(name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)       
            
        # Remove previous KLIC
        # kliclaag = QgsProject.instance().mapLayersByName(f"KLIC_{self.projectnr}")
        # if len(kliclaag) != 0:
        #     QgsProject.instance().removeMapLayer(kliclaag[0])

        # Filter
        if len(self.projectnr) > 12:
            self.projectnr = f"{self.projectnr[:12]}"            

        if self.combiprojectnr != qgis.core.NULL:
            if len(self.combiprojectnr) > 12:
                self.combiprojectnr = f"{self.combiprojectnr[:12]}"
            str_projectnr = f"'{self.projectnr}', '{self.combiprojectnr}'"
        else:
            str_projectnr = f"'{self.projectnr}'"
        self.kliclayer, features = self.generate_klicwfs(str_projectnr)
        print(str_projectnr)
        # kliclayer = processing.run("qgis:convertgeometrytype", {'INPUT':kliclayer,'TYPE':4,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT'] 
        if features == 0:
            if self.combiprojectnr == qgis.core.NULL:
                self.exception = f"Er zijn geen KLIC objecten gevonden met projectnummer {self.projectnr}"
            else:
                self.exception = f"Er zijn geen KLIC objecten gevonden met projectnummers {self.projectnr} of {self.combiprojectnr}"
            # QgsProject.instance().removeMapLayer(kliclayer)
            return False
            # else:
            #     self.message = f"Er zijn geen KLIC objecten gevonden met projectnummer {self.projectnr} maar wel met projectnummer {str_projectnr}. Deze is ingeladen."
        
        path = os.path.dirname(os.path.abspath(__file__))
        qml_path = os.path.join(path, '..', 'styles')
        qml_file = os.path.join(qml_path, 'KLIC.qml')
        self.kliclayer.loadNamedStyle(qml_file)
        self.kliclayer.setSubsetString(f'"projectnummer" IN ({str_projectnr})')
        
        self.meldnummers = []
        for f in self.kliclayer.getFeatures():
            meldnummer = f['meldnummer']
            if meldnummer not in self.meldnummers:
                self.meldnummers.append(meldnummer)
            if self.isCanceled():
                return False
        QgsMessageLog.logMessage(
            'Gevonden meldnummers: {name}'.format(name=self.meldnummers),
            MESSAGE_CATEGORY, Qgis.Info)
        
        # WMS laag
        if self.provider == 'wms':
            uri = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&contextualWMSLegend=0&crs=EPSG:28992&dpiMode=7&featureCount=10&format=image/png&layers=Geometrie&password=PbJ8HR%25gd8cYwPhtS$7h9F$&styles&tilePixelRatio=0&url=https://geoserver.geonius.nl/geoserver/klic/wms?CQL_FILTER%3Dprojectnummer%3D'{pn}'&username=QTG_Klic".format(pn=self.projectnr)
            self.wms_kliclayer = QgsRasterLayer(uri, f"KLIC_{self.projectnr}", "wms") 
        return True

    def generate_klicwfs(self, str_projectnr):
        # Load KLIC-layer from Geoserver
        uri = QgsDataSourceUri()

        QgsMessageLog.logMessage(
            f'filter: "projectnummer" IN ({str_projectnr})',
            MESSAGE_CATEGORY, Qgis.Info)

        uri.setSql(f"SELECT * FROM Geometrie WHERE geometryType(Geometrie.centrelineGeometry) = 'Polygon' AND Geometrie.projectnummer IN ({str_projectnr})")
        uri.setParam('url', 'https://geoserver.geonius.nl/geoserver/klic/wfs')
        uri.setParam('typename', 'klic:Geometrie')
        uri.setParam('srsName', 'EPSG:28992')
        uri.setParam('service', 'wfs')
        uri.setParam('version', 'auto')
        uri.setParam('request', 'GetFeature')
        uri.setParam('RestrictToRequestBBOX', '1')
        
        uri.setUsername('QTG_Klic')
        uri.setPassword('PbJ8HR%gd8cYwPhtS$7h9F$')
        # uri.setWkbType(QgsWkbTypes.Polygon)

        QgsMessageLog.logMessage(
            'Kliclaag {name} wordt toegevoegd aan geheugen'.format(name=self.projectnr),
            MESSAGE_CATEGORY, Qgis.Info)

        kliclayer = QgsVectorLayer(uri.uri(), f"KLIC_{self.projectnr}", "wfs")
        return kliclayer, kliclayer.featureCount()
    
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
                'Task "{name}" uitgevoerd, lagen worden nu toegevoegd aan project.'.format(
                    name=self.description),
                MESSAGE_CATEGORY, Qgis.Success)
            # KLIC group
            root = QgsProject.instance().layerTreeRoot()
            group_klic = root.findGroup("KLIC")
            if group_klic == None:
                group = root.addGroup("KLIC")
                group_klic = root.findGroup("KLIC")
            
            if self.provider == 'wfs':                  
                dialog = PopupTableDialog(self.meldnummers, ['Meldnummers'], 'Overzicht meldnummers', self.provider, self.kliclayer)
                dialog.exec_()

            elif self.provider == 'wms':                    
                dialog = PopupTableDialog(self.meldnummers, ['Meldnummers'], 'Overzicht meldnummers', self.provider)
                dialog.exec_()
                
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
                msg = QMessageBox()
                msg.setText(self.exception)
                msg.setIcon(QMessageBox.Critical) 
                msg.exec_()

    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was cancelled'.format(name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()    

class Kliccontrole(QgsTask):
    def __init__(self, description):
        self.exception = None
        super().__init__(description, QgsTask.CanCancel)

    def run(self):
        project = QgsProject.instance()
        crs_project = project.crs()
        map_project = QgsExpressionContextUtils.projectScope(project).variable('project_folder')

        res = get_projectinfo(['Projectnr', 'CombiProjectnr', 'DivisieNaam'])
        projectnr = res[0]        
        # projectnr = 'MA230003.021' # TEST
        combiprojectnr = res[1]
        divisie = res[2]

        self.boringen_m            = QgsProject.instance().mapLayersByName("Boringen")[0]
        self.boringen_g            = QgsProject.instance().mapLayersByName("Boringen")[1]
        self.sonderingen           = QgsProject.instance().mapLayersByName("Sonderingen")[0]
        self.vast_punt             = QgsProject.instance().mapLayersByName("Vast punt")[0]
        self.overig                = QgsProject.instance().mapLayersByName("Overig")[0]

        flag_bg = None
        flag_s = None
        flag_o = None
        flag_b = None

        lijst_lagen_M = []
        lijst_lagen_G = []

        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup('Geotechniek')
        if group is not None:
            for child in group.children():
                if child.name() == "Boringen":
                    boringen: QgsVectorLayer = child.layer()
                    result = filtercheck(boringen)
                    if result == True:
                        boringen.selectAll()
                        boringen_features = boringen.selectedFeatures()
                        if boringen.selectedFeatureCount() != 0:                            
                            lijst_lagen_G.append(boringen)
                            boringen.startEditing()
                            flag_bg = True
                        boringen.removeSelection()
                    else:
                        boringen_features = []
                if child.name() == "Sonderingen":
                    sonderingen: QgsVectorLayer = child.layer()
                    result = filtercheck(sonderingen)
                    if result == True:
                        sonderingen.selectAll()
                        sonderingen_features = sonderingen.selectedFeatures()
                        if sonderingen.selectedFeatureCount() != 0:
                            lijst_lagen_G.append(sonderingen)
                            sonderingen.startEditing()
                            flag_s = True
                        sonderingen.removeSelection()
                    else:
                        sonderingen_features = []
                if child.name() == "Overig":
                    overig: QgsVectorLayer = child.layer()
                    result = filtercheck(overig)
                    if result == True:
                        overig.selectAll()
                        overig_features = overig.selectedFeatures()
                        if overig.selectedFeatureCount() != 0:
                            lijst_lagen_G.append(overig)
                            overig.startEditing()
                            flag_o = True
                        overig.removeSelection()
                    else:
                        overig_features = []
        
        group = root.findGroup('Milieu')
        if group is not None:
            for child in group.children():
                if child.name() == 'Boringen':
                    boringen_m: QgsVectorLayer = child.layer()
                    result = filtercheck(boringen)
                    if result == True:
                        boringen_m.selectAll()
                        boringen_m_features = boringen_m.selectedFeatures()
                        if boringen_m.selectedFeatureCount() != 0:
                            lijst_lagen_M.append(boringen_m)
                            boringen_m.startEditing()
                            flag_b = True
                        boringen_m.removeSelection()
                    else:
                        boringen_m_features = []
        
        # Controleer of onderzoekspunten geselecteerd zijn
        selected_features = boringen_features + sonderingen_features + overig_features + boringen_m_features
        aantal_features = len(selected_features)
        QgsMessageLog.logMessage(
                'Gevonden aantal onderzoekspunten binnen project: {aantal}'.format(
                    aantal=aantal_features),
                MESSAGE_CATEGORY, Qgis.Info)

        lijst_intersect_eis = []
        lijst_intersect = []
        lijst_lagen = lijst_lagen_M if divisie == 'Milieu' else lijst_lagen_G
        if combiprojectnr != qgis.core.NULL:
            lijst_lagen = lijst_lagen + lijst_lagen_M if divisie != 'Milieu' else lijst_lagen + lijst_lagen_G
        if projectnr != qgis.core.NULL: 
            kliclayer = self.get_kliclayer(projectnr, combiprojectnr)
            if not isinstance(kliclayer, QgsVectorLayer):
                self.exception = Exception('KLIC-laag kon niet worden gefilterd op projectnummer.')
                return False
            # Controle
            li = self.process_layer(lijst_lagen, kliclayer, False)
            lijst_intersect.extend(li)
            lie = self.process_layer(lijst_lagen, kliclayer, True)
            lijst_intersect_eis.extend(lie)

        if flag_bg == True:
            boringen.commitChanges()
            iface.vectorLayerTools().stopEditing(boringen)  
        if flag_s == True:
            sonderingen.commitChanges()
            iface.vectorLayerTools().stopEditing(sonderingen)
        if flag_o == True:
            overig.commitChanges()
            iface.vectorLayerTools().stopEditing(overig)
        if flag_b == True:
            boringen_m.commitChanges()
            iface.vectorLayerTools().stopEditing(boringen_m)      

        # Maak passende boodschap
        string = ''
        if len(lijst_intersect) == 0 and len(lijst_intersect_eis) == 0:
            string = "Er liggen geen onderzoekspunten nabij de ingeladen KLIC-melding."
        elif len(lijst_intersect) == 1:
            string = "Het volgende onderzoekspunt ligt nabij de ingeladen KLIC-melding: \n" + ', '.join(lijst_intersect)
        elif len(lijst_intersect) > 1:
            string = "De volgende onderzoekspunten liggen nabij de ingeladen KLIC-melding: \n" + ', '.join(
                lijst_intersect)
        if len(lijst_intersect_eis) == 1:
            if len(lijst_intersect) == 0:
                string = string + "Het volgende onderzoekspunt ligt nabij de ingeladen Eis Voorzorgsmaatregel: \n" + ', '.join(
                    lijst_intersect_eis)
            else:
                string = string + "\n\nHet volgende onderzoekspunt ligt nabij de ingeladen Eis Voorzorgsmaatregel: \n" + ', '.join(
                    lijst_intersect_eis)
        elif len(lijst_intersect_eis) > 1:
            if len(lijst_intersect) == 0:
                string = string + "De volgende onderzoekspunten liggen nabij de ingeladen Eis Voorzorgsmaatregel: \n" + ', '.join(
                    lijst_intersect_eis)
            else:
                string = string + "\n\nDe volgende onderzoekspunten liggen nabij de ingeladen Eis Voorzorgsmaatregel: \n" + ', '.join(
                    lijst_intersect_eis)

        self.outputmessage = string
        return True

    def process_layer(self, lijst_lagen:list[QgsVectorLayer], kliclayer:QgsVectorLayer, ev:bool):
        lijst_intersect = []
        eisvoorzorgsmaatregel = "'AanduidingEisVoorzorgsmaatregel'"
        if ev:
            expr = QgsExpression(f'"featuretype" = {eisvoorzorgsmaatregel}')
        else:
            expr = QgsExpression(f'"featuretype" != {eisvoorzorgsmaatregel}')
        request = QgsFeatureRequest(expr)
        for laag in lijst_lagen:
            for feature in laag.getFeatures():
                feature:QgsFeature
                bbox = feature.geometry().boundingBox().buffered(3)
                request.setFilterRect(bbox)
                for klicfeature in kliclayer.getFeatures(request):
                    geometry_klic = klicfeature.geometry()
                    geom = feature.geometry()
                    if not ev:
                        geom = geom.buffer(1.5, 10)
                    naam = str(feature['type']) + str(feature['nummer'])
                    QgsMessageLog.logMessage(
                'Naam {naam} verwerkt, geometrie: {geom}.'.format(
                        naam=naam, geom=geom),
                    MESSAGE_CATEGORY, Qgis.Info)
                    
                    if geom.intersects(geometry_klic):
                        if naam not in lijst_intersect:
                            lijst_intersect.append(naam)
                            feature['klic_nabij'] = 'true'
                    else:
                        feature['klic_nabij'] = 'false'
                    laag.updateFeature(feature)
            QgsMessageLog.logMessage(
        'Laag {laag} verwerkt, EV: {ev}.'.format(
            laag=laag.name(), ev=ev),
        MESSAGE_CATEGORY, Qgis.Info)
        return lijst_intersect
    
    def get_kliclayer(self, projectnr, combiprojectnr):
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup('KLIC')
        if group is not None:
            for child in group.children():
                meldnrlayer: QgsVectorLayer = child.layer()
                kliclayer = meldnrlayer.clone()
                kliclayer.setSubsetString(f"\"projectnummer\" = '{projectnr}'")
                if combiprojectnr != None:
                    kliclayer.setSubsetString(f"\"projectnummer\" IN ('{projectnr}', '{combiprojectnr}')")
                if kliclayer.featureCount() == 0:
                    raise Exception(f'Geen KLIC-objecten gevonden op projectnummers {projectnr, combiprojectnr}.')
                return kliclayer
    
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
                'Task "{name}" completed'.format(
                    name=self.description()),
                MESSAGE_CATEGORY, Qgis.Success)
            msg = QMessageBox()
            msg.setText(self.outputmessage)
            msg.setIcon(QMessageBox.Information) 
            msg.exec_()
        else:
            if self.exception is None:
                QgsMessageLog.logMessage(
                    'Task "{name}" not successful but without exception ' \
                    '(probably the task was manually canceled by the '
                    'user)'.format(
                        name=self.description()),
                    MESSAGE_CATEGORY, Qgis.Warning)
            else:
                QgsMessageLog.logMessage(
                    'Task "{name}" Exception: {exception}'.format(
                        name=self.description(), exception=self.exception),
                    MESSAGE_CATEGORY, Qgis.Critical)
                raise self.exception

    def cancel(self):
        QgsMessageLog.logMessage(
            'Task "{name}" was cancelled'.format(name=self.description()),
            MESSAGE_CATEGORY, Qgis.Info)
        super().cancel()

class Exec_klicladen(QgsTask):
    def __init__(self, projectnr, combiprojectnr, provider):
        """Example of the class that needs to get tasks done. """
        """Subclassed examples. """
        globals()['klicladen'] = Klicladen('KLIC laden', projectnr, combiprojectnr, provider)

    def run(self):
        """Do tasks using QgsTask subclass. """
        QgsApplication.taskManager().addTask(globals()['klicladen'])        

class Exec_kliccontrole:
    def __init__(self):
        """Example of the class that needs to get tasks done. """
        """Subclassed examples. """
        globals()['kliccontroleren'] = Kliccontrole('KLIC controleren')

    def run(self):
        """Do tasks using QgsTask subclass. """
        QgsApplication.taskManager().addTask(globals()['kliccontroleren'])

class PopupTableDialog(QDialog):
    def __init__(self, data: list, headers: list, title: str, provider: str, mainlayer: QgsVectorLayer = None, parent = None):
        super(PopupTableDialog, self).__init__(parent)
        if mainlayer != None:
            self.mainlayer = mainlayer
        self.provider = provider
        
        self.setWindowTitle(title)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(200, 200)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)

        # Create a QVBoxLayout
        layout = QVBoxLayout(self)
        sublayout = QGridLayout()
        layout.addLayout(sublayout)

        # Create a QTableWidget
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setRowCount(len(data))
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)

        # Populate the table with data
        for i in range(len(data)):
            self.tableWidget.setItem(i, 0, QTableWidgetItem(str(data[i])))
        
        # Add the QTableWidget to the layout
        layout.addWidget(self.tableWidget)
        # self.tableWidget.setWidgetResizable(True)
        # compute the correct minimum width
        height = (layout.sizeHint().height() + 
            self.tableWidget.verticalScrollBar().sizeHint().height() + 
            self.tableWidget.height() * 2)
        self.tableWidget.setMinimumHeight(height)

        # Create a close button
        closeButton = QPushButton("Overzicht sluiten", self)
        closeButton.clicked.connect(self.overzicht_ev)
        closeButton.clicked.connect(self.close)
        layout.addWidget(closeButton)

        addlyrButton = QPushButton("Geselecteerde lagen toevoegen", self)
        addlyrButton.clicked.connect(self.addlayer)
        layout.addWidget(addlyrButton)

        addalllyrButton = QPushButton("Alle lagen toevoegen", self)
        addalllyrButton.clicked.connect(self.addalllayers)
        layout.addWidget(addalllyrButton)

        self.setLayout(layout)
    
    def addlayer(self):
        root = QgsProject.instance().layerTreeRoot()
        group_klic = root.findGroup("KLIC")
        
        items = self.tableWidget.selectedItems()
        names = [item.text() for item in items]
        print(names)
        for n in names:
            if self.provider == 'wms':
                uri = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&contextualWMSLegend=0&crs=EPSG:28992&dpiMode=7&featureCount=10&format=image/png&layers=Geometrie&password=PbJ8HR%25gd8cYwPhtS$7h9F$&styles&tilePixelRatio=0&url=https://geoserver.geonius.nl/geoserver/klic/wms?CQL_FILTER%3Dmeldnummer%3D'{meldnummer}'&username=QTG_Klic".format(meldnummer=n)
                layer = QgsRasterLayer(uri, f"KLIC_{n}", "wms") 
            elif self.provider == 'wfs':
                layer = self.mainlayer.clone()                           
                layer.setSubsetString(f''' "meldnummer" = '{n}' ''') 
                layer.setName(f'KLIC_{n}')
            QgsProject.instance().addMapLayer(layer, False)
            group_klic.insertChildNode(-1, QgsLayerTreeLayer(layer))
            layer_node = root.findLayer(layer.id())
            layer_node.setExpanded(False)
        QApplication.processEvents() 

    def addalllayers(self):
        root = QgsProject.instance().layerTreeRoot()
        group_klic = root.findGroup("KLIC")
        
        names = []
        for row in range(self.tableWidget.rowCount()):
            i = self.tableWidget.item(row,0)
            names.append(i.text())
        print(names)
        for n in names:
            if self.provider == 'wms':
                uri = "IgnoreGetFeatureInfoUrl=1&IgnoreGetMapUrl=1&contextualWMSLegend=0&crs=EPSG:28992&dpiMode=7&featureCount=10&format=image/png&layers=Geometrie&password=PbJ8HR%25gd8cYwPhtS$7h9F$&styles&tilePixelRatio=0&url=https://geoserver.geonius.nl/geoserver/klic/wms?CQL_FILTER%3Dmeldnummer%3D'{meldnummer}'&username=QTG_Klic".format(meldnummer=n)
                layer = QgsRasterLayer(uri, f"KLIC_{n}", "wms") 
            elif self.provider == 'wfs':
                layer = self.mainlayer.clone()                           
                layer.setSubsetString(f''' "meldnummer" = '{n}' ''') 
                layer.setName(f'KLIC_{n}')
            QgsProject.instance().addMapLayer(layer, False)
            group_klic.insertChildNode(-1, QgsLayerTreeLayer(layer))
            layer_node = root.findLayer(layer.id())
            layer_node.setExpanded(False)
        QApplication.processEvents() 

    def overzicht_ev(self):
        root = QgsProject.instance().layerTreeRoot()
        group_klic = root.findGroup("KLIC")
        meldnummers_ev = []
        meldnummers_multi_ev = []
        for lyr in group_klic.children():
            evs = []
            if lyr.nodeType() == 1:
                for f in lyr.layer().getFeatures():
                    if f['featuretype'] == 'AanduidingEisVoorzorgsmaatregel':
                        evs.append('Y')
                if len(evs) == 1:
                    meldnummers_ev.append(lyr.name().lstrip('KLIC_'))
                elif len(evs) > 1:
                    meldnummers_multi_ev.append(lyr.name().lstrip('KLIC_'))

        meldnummers_ev_totaal = meldnummers_ev + meldnummers_multi_ev
        l_msg = ""
        if len(meldnummers_ev_totaal) != 0:
            l_titleMsg = "Dit bericht bevat "
            if len(meldnummers_ev_totaal) > 1:
                l_titleMsg += "meerdere Eis Voorzorgsmaatregelen!"
            else:
                l_titleMsg += "een Eis Voorzorgsmaatregel!"
            
            if len(meldnummers_ev) == 1:
                l_msg = f"Het volgende meldnummer bevat een Eis Voorzorgsmaatregel: {meldnummers_ev[0]}\n\n"
            elif len(meldnummers_ev) > 1:
                l_msg = f"De volgende meldnummers bevatten een Eis Voorzorgsmaatregel: {', '.join(meldnummers_ev)}\n\n"

            if len(meldnummers_multi_ev) == 1:
                l_msg = l_msg + f"Het volgende meldnummer bevat meerdere Eis Voorzorgsmaatregel: {meldnummers_multi_ev[0]}"
            elif len(meldnummers_multi_ev) > 1:
                l_msg = l_msg + f"De volgende meldnummers bevatten meerdere Eis Voorzorgsmaatregelen: {', '.join(meldnummers_multi_ev)}"

            info_msg = "Lees de Eis Voorzorgsmaatregel(en)!\n\nHierin staat dat u verplicht bent contact op te nemen met de netbeheerder, voor aanvang van graafwerkzaamheden."
            
            msg = QMessageBox()
            msg.setWindowTitle(l_titleMsg)
            msg.setText(l_msg)
            msg.setInformativeText(info_msg)
            msg.setIcon(QMessageBox.Information) 
            msg.exec_()