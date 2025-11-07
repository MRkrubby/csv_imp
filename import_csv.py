import os, csv, time

import qgis
from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from qgis.analysis import *
from PyQt5.QtCore import *
from PyQt5.QtXml import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from datetime import date
import pandas as pd
import gc
from ..algemene_functies import filtercheck, get_projectinfo, opsteller_mail
from ..dialogs.combiproject_dialog import combiproject_dialog

MESSAGE_CATEGORY = 'Importeren Coordinaten'

class Importcsv(QgsTask):
    def __init__(self, description, filename, divisie, ahncheck, naamgepland, dialog = None):
        self.exception = None
        self.filename = filename
        self.divisie = divisie
        self.ahncheck = ahncheck
        self.naamgepland = naamgepland
        self.dialog = dialog
        self.description = description
        super().__init__(description, QgsTask.CanCancel)
        # self.klic_laden_projectnr(projectnr)

    def run(self):
        """
        Functie die wordt aangeroepen vanuit QGIS. 

        Zorgt ervoor dat ingemeten punten correct worden ingeladen in de juiste lagen.

        De functie maakt eerst onderscheid tussen de twee verschillende mogelijke formaten waarin de punten zijn opgeslagen in Excel.
        Nieuwe punten worden toegevoegd aan de juiste laag. Bestaande punten worden overgeschreven. De origineel ingetekende punten
        worden opgeslagen in een laag 'archief'.
        Aan het einde van dit proces krijgt de gebruiker een pop-up te zien. Hierin wordt, afhankelijk van uitkomsten, weergegeven of 
        de punten correct zijn ingeladen, welke punten eventueel niet zijn ingeladen en welke punten een grote afwijking hadden.

        Parameters
        ----------
        self : 
            om objecten makkelijk door te geven aan opvolgende functies.

        Returns
        -------
        None

        """
        QgsMessageLog.logMessage(
                'Task "{name}" started'.format(
                    name=self.description),
                MESSAGE_CATEGORY, Qgis.Info)
        self.start_time_tot = time.time()
        try:   
            res = get_projectinfo(attributen=['DivisieNaam'])         
            self.projectdivisie = res[0]
            l_boringen_M = []
            l_boringen_G = []
            l_sonderingen = []
            l_overig = []
            l_vast = []
            self.l_hdop = []
            hdop = 0
            self.l_ongeladen_punten = []
            self.onbekende_punten = []
            if self.ahncheck:
                self.afwijkingenZ = pd.DataFrame(columns=['Naam', 'Ingemeten Z', 'Z (AHN)', 'Verschil'])
            self.rijnummer = 0
            self.teller = 0

            # Progress bar
            # dialog, self.bar = self.progdialog(0, 'Inladen GPS-coördinaten')
            
            # self.bar.setValue(0)
            # self.bar.setMaximum(100)
            
            l_type_b = ["B","DB","MB","PB","BP","DBP"]
            l_type_s = ["S","HS","LS","ZS","SW","SWW","SWM","SG","SSW"]
            l_type_o = ["PDP", "HMB","SM","TM","WSM","DRI"]
            l_type_v = ["PG","D","DORPEL","KW","MP","PUT","VL","VLOER","WP","Overig"]
            
            # Lagen en geselecteerde features inladen
            root = QgsProject.instance().layerTreeRoot()
            group = root.findGroup('Milieu')
            if group is not None:
                for child in group.children():
                    if child.name() == "Boringen":
                        boringen_milieu = child.layer()
                        filtercheck(boringen_milieu)
                        for f in boringen_milieu.getFeatures():
                            naam = str(f['nummer'])
                            l_boringen_M.append(naam)

            group = root.findGroup('Geotechniek')
            if group is not None:
                for child in group.children():
                    if child.name() == "Boringen":
                        boringen_geotechniek = child.layer()
                        filtercheck(boringen_geotechniek)
                        for f in boringen_geotechniek.getFeatures():
                            naam = str(f['type']) + str(f['nummer'])
                            l_boringen_G.append(naam)
                    elif child.name() == 'Sonderingen':
                        sonderingen = child.layer()
                        filtercheck(sonderingen) # Voor bewerken, anders wordt filter niet aangepast
                        for f in sonderingen.getFeatures():
                            naam = str(f['type']) + str(f['nummer'])
                            l_sonderingen.append(naam)
                    elif child.name() == 'Overig':
                        overig = child.layer()
                        filtercheck(overig)
                        for f in overig.getFeatures():
                            naam = str(f['type']) + str(f['nummer'])
                            l_overig.append(naam)
                    elif child.name() == 'Vast punt':
                        vast_punt = child.layer()
                        filtercheck(vast_punt)
                        for f in vast_punt.getFeatures():
                            naam = str(f['type']) + str(f['nummer'])
                            l_vast.append(naam)
            self.nieuwformat = False

            self.meldinglist = []
            max_id = 1

            with open(self.filename, newline='', encoding='utf-8-sig') as csvfile:
                csv_reader = csv.reader(csvfile, delimiter=',')

                self.total_rows = sum(1 for row in csvfile)
                csvfile.seek(0)

                if 'coordinates' in next(csv_reader)[0]:
                    nieuwformat = True
                    csvfile.seek(0)
                    [next(csvfile) for _ in range(3)]
                    self.total_rows = self.total_rows - 3
                else:
                    nieuwformat = False
                    csvfile.seek(0)

                for row in csv_reader:
                    # Manier van inlezen aanpassen naargelang systeeminstellingen
                    if len(row) == 1:
                        string = row[0]
                        list = string.split(',')
                    else:
                        list = row

                    self.naam_gepland = list[0]
                    self.x_veld = list[1]
                    self.y_veld = list[2]
                    try:
                        self.z_veld = list[3]
                    except:
                        print(f'Z-waarde niet gevonden bij {self.naam_gepland}, deze wordt ingesteld op NULL')
                        self.z_veld = NULL
                    if nieuwformat == True:
                        if list[5] != '?':
                            hdop = float(list[5])

                    # TODO: test out of range als er geen eff nummer is ingegeven
                    try:
                        self.naam_eff = list[4]
                    except:
                        # Als het effectieve nummer leeg is, moet het ingeplande nummer aangehouden worden
                        self.naam_eff = ''
                        list.append('') 

                    type_afk, nummer = self.naam_gepland.rstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-* ').rstrip(' 0123456789'), self.naam_gepland.lstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-* ')
                    type_afk_eff, nummer_eff = self.naam_eff.rstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-* ').rstrip(' 0123456789'), self.naam_eff.lstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-* ')
                    if type_afk == '' and nummer == '':
                        x = self.naam_gepland.split(' ')
                        type_afk, nummer = x[0].upper(), x[1].upper()
                        y = self.naam_eff.split(' ')
                        type_afk_eff, nummer_eff = x[0].upper(), x[1].upper()
                    
                    type_afk = type_afk.upper()
                    try:
                        nummer = nummer.upper()
                    except:
                        pass
                    if self.divisie == 'Milieu':
                        if len(nummer) == 1:
                            nummer = '00' + nummer
                        elif len(nummer) == 2:
                            nummer = '0' + nummer

                        nummer_eff_clean = nummer_eff.rstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-* ')
                        if len(nummer_eff_clean) == 1:
                            nummer_eff = '00' + nummer_eff
                        elif len(nummer_eff_clean) == 2:
                            nummer_eff = '0' + nummer_eff
                    print(type_afk, nummer, type_afk_eff, nummer_eff, self.x_veld, self.y_veld, self.z_veld)

                    if self.divisie == 'Milieu':
                        print('Milieu')
                        if type_afk == '':
                            self.process_imp_features(l_boringen_M, boringen_milieu, nummer, type_afk, max_id, type_afk_eff, nummer_eff)
                        else:
                            self.process_imp_features([], None, nummer, type_afk, max_id, type_afk_eff, nummer_eff)
                            self.onbekende_punten.append(self.naam_eff)
                    elif self.divisie == 'Geotechniek':
                        print('Ander')
                        if type_afk in l_type_b:
                            # print('Boring')
                            self.process_imp_features(l_boringen_G, boringen_geotechniek, nummer, type_afk, max_id, type_afk_eff, nummer_eff)
                        elif type_afk in l_type_s:
                            # print('Sondering')
                            self.process_imp_features(l_sonderingen, sonderingen, nummer, type_afk, max_id, type_afk_eff, nummer_eff)
                        elif type_afk in l_type_o:
                            # print('Overig')   
                            self.process_imp_features(l_overig, overig, nummer, type_afk, max_id, type_afk_eff, nummer_eff) 
                        elif type_afk in l_type_v:
                            # print('Vast punt')  
                            self.process_imp_features(l_vast, vast_punt, nummer, type_afk, max_id, type_afk_eff, nummer_eff)  
                        else:
                            self.process_imp_features([], None, nummer, type_afk, max_id, type_afk_eff, nummer_eff)
                            self.onbekende_punten.append(self.naam_eff)
                    else:
                        self.l_ongeladen_punten.append(self.naam_eff)                

                    # HDOP
                    if hdop > 0.1:
                        self.l_hdop.append(self.naam_eff)
                    max_id += 1
            return True
        except Exception as e:
            self.exception = str(e)
            return False

    def process_imp_features(self, list, layer, nummer, type_afk, max_id, type_afk_eff, nummer_eff):
        """
        Functie die wordt aangeroepen vanuit run_laag_imp_csv. Wordt aangeroepen met de juiste attributen om punten 
        toe te voegen aan juiste laag, of aan archief.

        Deze functie checkt eerst of het in te laden punt bestaat in de laag. Wanneer dit punt bestaat, wordt het 
        verplaatst Zo niet, wordt het punt alleen toegevoegd aan de juiste laag. Onbekende punten worden toegevoegd 
        aan de laag boringen van de juiste divisie.      

        Parameters
        ----------
        self : 
            om objecten makkelijk door te geven aan opvolgende functies.
        list :
            lijst met alle namen van punten in elke relevante laag, dus:
            boringen milieu: alleen nummers
            lagen geotechniek: type + nummer
        layer :
            de relevante laag
        nummer :
            het nummer van het in te laden punt
        type_afk :
            het afgekorte type van het in te laden punt

        Returns
        -------
        None

        """
        ## Types
        l_type_b = ["B","DB","MB","PB","BP","DBP"]
        l_type_s = ["S","HS","LS","ZS","SW","SWW","SWM", "SSW", "SG"]
        l_type_o = ["PDP", "HMB","SM","TM","WSM","DRI"]
        l_type_v = ["PG","D", "DORPEL","KW","MP","PUT","VL", "VLOER","WP", "Overig"]
        
        if layer == None:
            if self.divisie == 'Milieu':
                layer = QgsProject.instance().mapLayersByName('Boringen')[0]
            if self.divisie == 'Geotechniek':
                layer = QgsProject.instance().mapLayersByName('Boringen')[1]
        layer.startEditing()

        project = QgsProject.instance()
        projectid = QgsExpressionContextUtils.projectScope(project).variable('QTGFASEID')
        lookup = QgsProject.instance().mapLayersByName("Projectfasen")[0]
        expr = QgsExpression('"ID"=\'%s\'' % projectid)
        request = QgsFeatureRequest(expr)
        for featurePnr in lookup.getFeatures(request):
            projectnr = featurePnr['Projectnr']
            fase = featurePnr['ID']

        today = date.today()
        today = today.strftime("%Y-%m-%dT%H:%M:%S")

        opsteller = opsteller_mail()

        # list.remove(self.naam_clean)
        # if list != []:
        if self.naamgepland:
            expr = f"\"nummer\" = '{self.naam_gepland}'"
        else:
            if self.divisie == 'Milieu':
                expr = f"\"nummer\" = '{nummer}'"
            else: # alle andere punten
                if type_afk != '' and type_afk not in l_type_b and type_afk not in l_type_s and type_afk not in l_type_o and type_afk not in l_type_v: # externe punten
                    expr = f"\"nummer\" = '{nummer}'"
                else:
                    if type_afk == 'VLOER':
                        type_afk = 'VL'
                    elif type_afk == 'DORPEL':
                        type_afk = 'D'
                    expr = f"\"nummer\" = '{nummer}' AND \"type\" = '{type_afk}'"
        print(expr)
        layer.selectByExpression(expr)
        
        if len(layer.selectedFeatures()) == 0 or (len(layer.selectedFeatures()) != 0 and ('projectfase_ID' not in layer.subsetString() and 'projectnr' not in layer.subsetString())): 
            # Punt staat niet in tabel, dus nieuw punt maken
            print('Nieuw punt')
            f = QgsFeature(layer.fields())
            f['ogr_fid'] = max_id
            f['projectfase_ID'] = fase
            f['divisie'] = self.divisie
            f['tekenaar'] = opsteller
            f['datum'] = today
            f['status'] = 'Gepland'
            f['verharding'] = 'Onbekend'
            f['nummer'] = nummer
            if self.naamgepland:
                f['nummer'] = self.naam_gepland
            f['projectnr'] = projectnr
            f['x_coordinaat'] = self.x_veld
            f['y_coordinaat'] = self.y_veld
            f['z_hoogte'] = self.z_veld
            f['klic_nabij'] = 'false'
            f['monstername'] = 'false'
            f['potten'] = 'false'
            f['PIDMeting'] = 'false'
            f['olie_water'] = 'false'
            f['fundatie_bemonsteren'] = 'false'
            f['dissipatie'] = 'false'
            f['verankering_minirups'] = 'false'
            f['afdichten'] = 'false'
            f['gecontroleerd_PL'] = 'false'
            f['foto_maken'] = 'false'
            f['asfalt_bemonsteren'] = 'false'
            f['beton_bemonsteren'] = 'false'

            f['proefgat'] = 'false'
            f['proefsleuf'] = 'false'
            f['waterbodem'] = 'false'
            f['machinaal'] = 'false'
            f['doorlatendheidsmeting'] = 'false'
            f['peilbuis'] = 'false'

            if type_afk != '':      
                # if nummer_eff != nummer:  
                    # if type_afk_eff == '' and self.naam_eff != '':
                if self.naam_eff != '':
                    f['externe_naam'] = self.naam_eff
                    # else:
                    #     f['externe_naam'] = type_afk_eff + nummer_eff
                f['naam'] = self.naam_gepland  
                if self.divisie == 'Geotechniek':
                    if type_afk in l_type_b:
                        if 'B' in type_afk and type_afk != 'PB':
                            f['type'] = 'B'
                        else:
                            f['type'] = 'NULL'
                        if 'D' in type_afk:
                            f['doorlatendheidsmeting'] = 'true'
                        if 'M' in type_afk:
                            f['machinaal'] = 'true'
                        if 'P' in type_afk:
                            f['peilbuis'] = 'true'
                    elif type_afk in l_type_s or type_afk in l_type_o or type_afk in l_type_v:
                        f['type'] = type_afk
                    else:
                        f['type'] = 'B'
                        f['diepte'] = 3.2
                if self.divisie == 'Milieu':
                    f['diepte'] = 0.5
                    f['type'] = 'B'                
            else:
                if self.divisie == 'Milieu':
                    f['diepte'] = 0.5
                else:
                    f['diepte'] = 3.2
                f['type'] = 'B'
            if layer.name() == 'Boringen':
                self.meldinglist.append(self.naam_eff)
            self.teller += 1

            pnt = QgsGeometry.fromPointXY(QgsPointXY(float(self.x_veld), float(self.y_veld)))
            f.setGeometry(pnt)
            layer.addFeature(f)
            # iface.mapCanvas().refresh()

        elif len(layer.selectedFeatures()) != 0 and ('projectfase_ID' in layer.subsetString() or 'projectnr' in layer.subsetString()):
            # Pas coordinaten aan in oorspronkelijke laag
            features_nieuw = layer.selectedFeatures()
            # Verplaats boring naar effectieve locatie
            for feature_nieuw in features_nieuw:
                # Update x en y voor laag boringen
                if self.naam_eff not in list:
                    feature_nieuw['naam'] = self.naam_gepland
                    # if type_afk_eff == '' and self.naam_eff != '':                    
                    if self.naam_eff != '':
                        feature_nieuw['externe_naam'] = self.naam_eff
                    # else:
                    #     feature_nieuw['externe_naam'] = type_afk_eff + nummer_eff
                feature_nieuw['nummer'] = nummer
                if self.naamgepland:
                    feature_nieuw['nummer'] = self.naam_gepland
                feature_nieuw['x_coordinaat'] = self.x_veld
                feature_nieuw['y_coordinaat'] = self.y_veld
                feature_nieuw['z_hoogte'] = self.z_veld
                pnt = QgsGeometry.fromPointXY(QgsPointXY(float(self.x_veld), float(self.y_veld)))
                feature_nieuw.setGeometry(pnt)

                # Updaten van laag
                layer.updateFeature(feature_nieuw)
                layer.changeGeometry(feature_nieuw.id(), pnt)
        
        else:
            self.l_ongeladen_punten.append(type_afk, nummer)

        if self.ahncheck:
            point = QgsPointXY(float(self.x_veld), float(self.y_veld))
            ahnval = self.ahn_check(point)
            if ahnval == -9999:
                ahn_res = 'n.v.t.'
                diff_res = 'n.v.t.'
                try:
                    self.afwijkingenZ.loc[self.rijnummer] = [self.naam_gepland, float(self.z_veld), ahn_res, diff_res]
                except:
                    self.afwijkingenZ.loc[self.rijnummer] = [self.naam_gepland, 0, ahn_res, diff_res]

            else:
                ahn_res = round(ahnval,3)
                diff_res = round(float(self.z_veld) - round(ahnval,3), 3)
                try:
                    self.afwijkingenZ.loc[self.rijnummer] = [self.naam_gepland, float(self.z_veld), ahn_res, diff_res]
                except:
                    self.afwijkingenZ.loc[self.rijnummer] = [self.naam_gepland, 0, ahn_res, diff_res]
            
            # Update the dockwidget only periodically to reduce UI overhead
            try:
                if (self.rijnummer % 20) == 0 or (self.rijnummer + 1) == self.total_rows:
                    try:
                        self.dialog.populate(self.afwijkingenZ)
                    except Exception:
                        pass
            except Exception:
                pass
            self.rijnummer = self.rijnummer + 1
        progress = (float(self.rijnummer) / float(self.total_rows)) * 100
        self.setProgress(progress)
        layer.removeSelection()
        layer.commitChanges()
        # self.bar.setValue(progress)

    def ahn_check(self, point: QgsPointXY) -> float:
        """
        Haal AHN-waarde op via WCS/REST afhankelijk van CRS.
        Gebruik rasterio.MemoryFile om geen tijdelijke bestanden te schrijven.
        Retourneert float of n.v.t. bij fouten of bij nodata/sentinel values.
        """
        try:
            from rasterio.io import MemoryFile
            import requests
            from owslib.wcs import WebCoverageService
            from qgis.core import QgsMessageLog, Qgis
            import math
        except Exception:
            return -9999

        projectcrs = QgsExpressionContextUtils.projectScope(QgsProject.instance()).variable('project_crs')

        # threshold om onrealistisch hoge sentinel-waarden te detecteren (Float32 max ~3.4e38)
        SENTINEL_THRESHOLD = 1e30

        try:
            if projectcrs == 'EPSG:28992':
                wcs_url = 'https://service.pdok.nl/rws/ahn/wcs/v1_0'
                wcs = WebCoverageService(wcs_url, version='2.0.1')

                output = wcs.getCoverage(
                    identifier=['dtm_05m'],
                    format='image/tiff',
                    crs='EPSG:28992',
                    subsets=[
                        ('X', point.x() - 0.5, point.x() + 0.5),
                        ('Y', point.y() - 0.5, point.y() + 0.5),
                    ]
                )

                data = output.read()  # bytes
                if not data:
                    return -9999

                try:
                    with MemoryFile(data) as memfile:
                        with memfile.open() as src:
                            for val_arr in src.sample([(point.x(), point.y())]):
                                raw = val_arr[0]
                                try:
                                    val = float(raw)
                                except Exception:
                                    QgsMessageLog.logMessage(f"AHN: sample niet-numeriek ({raw}) op {point.x()},{point.y()}", 'QTG ImportCSV', Qgis.Debug)
                                    return -9999
                                # detecteer nodata / sentinel / inf
                                if (not math.isfinite(val)) or abs(val) > SENTINEL_THRESHOLD:
                                    QgsMessageLog.logMessage(f"AHN: gedetecteerde sentinel/nodata waarde {val} → vervangen door n.v.t.", 'QTG ImportCSV', Qgis.Debug)
                                    return -9999
                                return val
                except Exception:
                    return -9999

            elif projectcrs == 'EPSG:31370':
                url = f"https://www.dov.vlaanderen.be/zoeken-ocdov/proxy-dhm/api/elevation/v1/DHMV2?Locations={point.x()},{point.y()}"
                try:
                    res = requests.get(url, timeout=8)
                    if res.status_code != 200 or not res.content:
                        return -9999
                    text = res.content.decode("utf-8")
                    vals = text.split(',')
                    raw = vals[-1].strip("]'")
                    try:
                        val = float(raw)
                    except Exception:
                        QgsMessageLog.logMessage(f"AHN(DOV): niet-numerieke respons '{raw}'", 'QTG ImportCSV', Qgis.Debug)
                        return -9999
                    if (not math.isfinite(val)) or abs(val) > SENTINEL_THRESHOLD:
                        QgsMessageLog.logMessage(f"AHN(DOV): sentinel/nodata waarde {val} → n.v.t.", 'QTG ImportCSV', Qgis.Debug)
                        return -9999
                    return val
                except Exception:
                    return -9999
            else:
                return -9999
        except Exception:
            return -9999
    
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
                    name=self.description),
                MESSAGE_CATEGORY, Qgis.Success)
            if result == True:
                self.msgbox()
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
    
    def msgbox(self):
        endtime = time.time()
        tottime = endtime - self.start_time_tot
        text = f"\n\n De onderzoekspunten zijn ingeladen."

        if self.projectdivisie == 'Milieu':
            diepte = '0,5'
        else:
            diepte = '3,2'

        if len(self.meldinglist) != 0:
            text = text + f"\n\nLet op, de onderstaande punten zijn ingeladen met onbekende diepte. Deze is ingesteld op {diepte} meter. \n" + ', '.join(self.meldinglist)        
        if len(self.onbekende_punten) != 0:
            text = text + f"\n\nLet op, de onderstaande punten bevatten een niet herkend type en zijn ingeladen in de laag boringen ({self.divisie}). \n" + ', '.join(self.onbekende_punten)
        if len(self.l_ongeladen_punten) != 0:
            text = text + "\n\nLet op, onderstaande punten zijn niet ingeladen: \n" + ', '.join(self.l_ongeladen_punten) + '\n Maak hiervan een melding bij het GIS-team.' 
        if len(self.l_hdop) != 0:
            text = text + '\n\nLet op, deze boringen hebben een horizontale afwijking groter dan 10cm:\n' + ', '.join(
            self.l_hdop)

        msg = QMessageBox()
        msg.setText(text)
        msg.setIcon(QMessageBox.Information)  
        msg.exec_()            

class Exec_importcsv:
    def __init__(self, filename, divisie, ahncheck, naamgepland, dialog = None):
        globals()['importcsv'] = Importcsv('Importeren coördinaten', filename, divisie, ahncheck, naamgepland, dialog)

    def run(self):
        """Do tasks using QgsTask subclass. """
        QgsApplication.taskManager().addTask(globals()['importcsv'])

class PopupTableDialog(QDockWidget):
    closingPlugin = pyqtSignal()
    def __init__(self, headers, title, parent=None):
        super(PopupTableDialog, self).__init__(title)
        self.headers = headers   
        # Create a QVBoxLayout
        layout = QGridLayout(self)     
        self.tableWidget = QTableWidget(self)
        self.tableWidget.resize(500, 500)
        self.tableWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setHorizontalHeaderLabels(headers)
        # Add the QTableWidget to the layout
        layout.addWidget(self.tableWidget, 0, 0)
        self.setLayout(layout)

        self.setWindowTitle(title)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(500, 500)

    def populate(self, data:pd.DataFrame):
        print(data)
        # Create a QTableWidget
        self.tableWidget.setRowCount(len(data))

        for row in range(len(data)):
            for col in range(len(data.columns)):
                value = str(data.iloc[row, col])  # Convert cell value to string
                self.tableWidget.setItem(row, col, QTableWidgetItem(value))

    def closeEvent(self, event:QEvent):
        self.closingPlugin.emit()