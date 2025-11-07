@echo off
SET OSGEO4W_ROOT=C:\Program Files\QGIS 3.34.15

REM Zet QGIS LTR omgevingsvariabelen
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
set PATH=%OSGEO4W_ROOT%\apps\qgis-ltr\bin;%OSGEO4W_ROOT%\apps\Qt5\bin;%OSGEO4W_ROOT%\bin;%PATH%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis-ltr\python
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr
set PYTHONHOME=%OSGEO4W_ROOT%\apps\Python312
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qgis-ltr\qtplugins;%OSGEO4W_ROOT%\apps\Qt5\plugins

cmd.exe