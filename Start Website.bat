@echo off
setlocal
cd /d "%~dp0"
title Radhaus Fuhse - lokaler Server

set PORT=8094

where php >/dev/null 2>&1
if errorlevel 1 goto ohnephp

if not exist ".env" php bin\einrichten.php --vorfuehrdaten
if errorlevel 1 goto fehler
php bin\bauen.php
start "" http://localhost:%PORT%/
echo.
echo   Radhaus Fuhse laeuft auf http://localhost:%PORT%/
echo   Verwaltung: http://localhost:%PORT%/verwaltung/
echo   Zum Beenden: Strg+C oder dieses Fenster schliessen.
echo.
php -S 127.0.0.1:%PORT% -t public bin\dev-router.php
goto ende

:ohnephp
where python >/dev/null 2>&1
if errorlevel 1 goto keinpython
start "" http://localhost:%PORT%/
echo.
echo   PHP nicht gefunden, starte die Vorfuehrfassung.
echo   Radhaus Fuhse laeuft auf http://localhost:%PORT%/
echo   Zum Beenden: Strg+C oder dieses Fenster schliessen.
echo.
python -m http.server %PORT% --bind 127.0.0.1 --directory docs
goto ende

:keinpython
echo.
echo   FEHLER: Weder php noch python gefunden.
echo   PHP 8.3 oder Python installieren und zum PATH hinzufuegen.
echo.
pause
exit /b 1

:fehler
echo.
echo   Einrichtung fehlgeschlagen. Ist die Erweiterung sodium und pdo_sqlite in php.ini aktiv?
echo.
pause
exit /b 1

:ende
echo.
echo   Server beendet. Laeuft eventuell schon einer auf Port %PORT%?
pause
