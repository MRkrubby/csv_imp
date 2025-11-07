import unittest
from unittest.mock import MagicMock, patch, mock_open

import subprocess, os
# subprocess.check_call(r"C:\Users\m.vandenbrink\OneDrive - Geonius\Documenten\QTG voor W\QTGvoorWerkvoorbereiding_dev\tests\importfix.bat")
# os.add_dll_directory(r"C:\Program Files\QGIS 3.34.15\apps\qgis-ltr\bin")
# os.add_dll_directory(r"C:\Program Files\QGIS 3.34.15\apps\Qt5\bin")
# os.add_dll_directory(r"C:\Program Files\QGIS 3.34.15\bin")

from ..printomgeving.printomgevingbasis import Printomgeving

class TestPrintomgeving(unittest.TestCase):
    @patch('printomgeving.QgsProject')
    @patch('printomgeving.QApplication')
    @patch('printomgeving.open', new_callable=mock_open, read_data='<qpt></qpt>')
    @patch('printomgeving.QDomDocument')
    @patch('printomgeving.QgsPrintLayout')
    @patch('printomgeving.QgsReadWriteContext')
    @patch('printomgeving.get_layout_path')
    @patch('printomgeving.type_checks')
    @patch('printomgeving.get_common_fields')
    @patch('printomgeving.get_onderdeel_info')
    def test_run_printomgeving_milieu(
        self, mock_get_onderdeel_info, mock_get_common_fields, mock_type_checks, mock_get_layout_path,
        mock_QgsReadWriteContext, mock_QgsPrintLayout, mock_QDomDocument, mock_open, mock_QApplication, mock_QgsProject
    ):
        # Arrange
        mock_dialog = MagicMock()
        mock_dialog.tabWidget.currentWidget.return_value.objectName.return_value = 'tab_milieu'
        mock_dialog.versie.text.return_value = 'A'
        mock_dialog.topografisch.isChecked.return_value = False
        mock_dialog.bijlagenr.value.return_value = 1
        mock_dialog.rapportage.isChecked.return_value = False
        mock_dialog.rapportage_3.isChecked.return_value = False

        mock_project = MagicMock()
        mock_QgsProject.instance.return_value = mock_project
        mock_project.layoutManager.return_value = MagicMock()

        mock_get_layout_path.return_value = 'layout_path'
        mock_type_checks.return_value = {'some': 'input'}
        mock_get_common_fields.return_value = {
            'projectnummer': '123',
            'projectnaam': 'TestProject',
            'projectleider': 'Alice',
            'omschrijving': 'TestOmschrijving',
            'opsteller': 'Bob'
        }
        mock_get_onderdeel_info.return_value = ('Onderdeel', 'Type')

        obj = Printomgeving('C:/plugin_dir', mock_dialog)

        # Act
        obj.run_printomgeving()

        # Assert
        mock_QApplication.processEvents.assert_called()
        mock_project.layoutManager.assert_called()
        mock_get_layout_path.assert_called()
        mock_type_checks.assert_called()
        mock_open.assert_called()  # Template file should be opened

if __name__ == '__main__':
    unittest.main()