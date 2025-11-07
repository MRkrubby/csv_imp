from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from qgis.core import *
from qgis.gui import *
from qgis.utils import *

class LoadingDock(QDockWidget):
    def __init__(self, aantaltaken:int=0, takenlijst:list=None, parent=None):
        super().__init__("Loading Progress", parent)
        self.setMaximumHeight(100)
        
        self.aantaltaken = aantaltaken
        self.takenlijst = takenlijst if takenlijst else []
        self.n = 100  # Total instance
        
        self.initUI()

    def initUI(self):
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        self.setWidget(widget)

        self.labelDescription = QLabel("Waiting for tasks...")
        self.labelDescription.setAlignment(Qt.AlignCenter)
        self.labelDescription.setWordWrap(True)
        layout.addWidget(self.labelDescription)

        self.progressBar = QProgressBar()
        self.progressBar.setAlignment(Qt.AlignCenter)
        self.progressBar.setFormat('%p%')
        self.progressBar.setTextVisible(True)
        self.progressBar.setRange(0, self.n)
        layout.addWidget(self.progressBar)
    
    def loading(self, value):
        prog = self.aantaltaken - value
        perc = (prog / self.aantaltaken) * 100 if self.aantaltaken > 0 else 0
        self.progressBar.setValue(int(perc))
        
        tasks = QgsApplication.taskManager().activeTasks()
        description = [task.description() for task in tasks]

        for d in self.takenlijst[:]:  # Copy list to avoid modification issues
            if d not in description:
                self.takenlijst.remove(d)
                self.labelDescription.setText(f'<strong>Geladen: {d}</strong>')
                break
        