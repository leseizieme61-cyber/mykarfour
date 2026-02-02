@echo off
REM Script de configuration pour les rappels automatiques MyKarfour sur Windows
REM Ce script configure le Planificateur de tâches Windows pour l'envoi automatique des rappels

echo 🔧 Configuration des rappels automatiques MyKarfour (Windows)...

REM Vérifier si nous sommes dans le bon répertoire
if not exist "manage.py" (
    echo ❌ Erreur: Ce script doit être exécuté depuis le répertoire racine de Django (où se trouve manage.py)
    pause
    exit /b 1
)

REM Obtenir le chemin complet du projet
set PROJECT_PATH=%CD%
set PYTHON_CMD=python

REM Demander le chemin de Python si nécessaire
echo 🐍 Vérification de Python...
%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python non trouvé dans le PATH.
    set /p PYTHON_CMD="Entrez le chemin complet de python.exe (ex: C:\Python39\python.exe): "
)

REM Créer le fichier batch pour les rappels
set RAPPELS_BATCH=%PROJECT_PATH%\scripts\envoyer_rappels.bat
echo @echo off > "%RAPPELS_BATCH%"
echo echo Envoi des rappels automatiques MyKarfour... >> "%RAPPELS_BATCH%"
echo cd /d "%PROJECT_PATH%" >> "%RAPPELS_BATCH%"
echo "%PYTHON_CMD%" manage.py envoyer_rappels >> "%PROJECT_PATH%\logs\rappels.log" 2>&1 >> "%RAPPELS_BATCH%"
echo if errorlevel 1 ( >> "%RAPPELS_BATCH%"
echo     echo Erreur lors de l'envoi des rappels >> "%PROJECT_PATH%\logs\rappels.log" >> "%RAPPELS_BATCH%"
echo ) >> "%RAPPELS_BATCH%"

REM Créer le fichier batch pour la programmation des sessions
set SESSIONS_BATCH=%PROJECT_PATH%\scripts\programmer_sessions.bat
echo @echo off > "%SESSIONS_BATCH%"
echo echo Programmation des sessions MyKarfour... >> "%SESSIONS_BATCH%"
echo cd /d "%PROJECT_PATH%" >> "%SESSIONS_BATCH%"
echo "%PYTHON_CMD%" manage.py programmer_sessions >> "%PROJECT_PATH%\logs\sessions.log" 2>&1 >> "%SESSIONS_BATCH%"
echo if errorlevel 1 ( >> "%SESSIONS_BATCH%"
echo     echo Erreur lors de la programmation des sessions >> "%PROJECT_PATH%\logs\sessions.log" >> "%SESSIONS_BATCH%"
echo ) >> "%SESSIONS_BATCH%"

REM Créer le répertoire des logs
if not exist "%PROJECT_PATH%\logs" mkdir "%PROJECT_PATH%\logs"

echo ✅ Fichiers batch créés:
echo    - %RAPPELS_BATCH%
echo    - %SESSIONS_BATCH%

REM Créer les tâches planifiées
echo.
echo 📅 Création des tâches planifiées...

REM Tâche pour les rappels quotidiens (8h00)
schtasks /create /tn "MyKarfour Rappels Quotidiens" /tr "%RAPPELS_BATCH%" /sc daily /st 08:00 /f
if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche "MyKarfour Rappels Quotidiens"
) else (
    echo ✅ Tâche "MyKarfour Rappels Quotidiens" créée (8h00 tous les jours)
)

REM Tâche pour la programmation des sessions (dimanche 20h00)
schtasks /create /tn "MyKarfour Programmation Sessions" /tr "%SESSIONS_BATCH%" /sc weekly /d SUN /st 20:00 /f
if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche "MyKarfour Programmation Sessions"
) else (
    echo ✅ Tâche "MyKarfour Programmation Sessions" créée (dimanche 20h00)
)

REM Tâche de nettoyage (lundi 2h00)
set NETTOYAGE_BATCH=%PROJECT_PATH%\scripts\nettoyer_rappels.bat
echo @echo off > "%NETTOYAGE_BATCH%"
echo echo Nettoyage des anciens rappels MyKarfour... >> "%NETTOYAGE_BATCH%"
echo cd /d "%PROJECT_PATH%" >> "%NETTOYAGE_BATCH%"
echo "%PYTHON_CMD%" manage.py shell -c "from repetiteur_ia.models import RappelRevision; from django.utils import timezone; from datetime import timedelta; seuil = timezone.now() - timedelta(days=30); anciens = RappelRevision.objects.filter(date_creation__lt=seuil); count = anciens.count(); anciens.delete(); print(f'Nettoyé {count} anciens rappels')" >> "%PROJECT_PATH%\logs\nettoyage.log" 2>&1 >> "%NETTOYAGE_BATCH%"

schtasks /create /tn "MyKarfour Nettoyage Rappels" /tr "%NETTOYAGE_BATCH%" /sc weekly /d MON /st 02:00 /f
if errorlevel 1 (
    echo ❌ Erreur lors de la création de la tâche "MyKarfour Nettoyage Rappels"
) else (
    echo ✅ Tâche "MyKarfour Nettoyage Rappels" créée (lundi 2h00)
)

echo.
echo 📋 Tâches planifiées créées:
schtasks /query /fo LIST | findstr "MyKarfour"

echo.
echo 📝 Les logs seront écrits dans:
echo    - %PROJECT_PATH%\logs\rappels.log
echo    - %PROJECT_PATH%\logs\sessions.log
echo    - %PROJECT_PATH%\logs\nettoyage.log

echo.
echo 🧪 Pour tester manuellement:
echo    %PYTHON_CMD% manage.py envoyer_rappels
echo    %PYTHON_CMD% manage.py programmer_sessions

echo.
echo 🔧 Pour modifier les tâches:
echo    - Panneau de configuration ^> Outils d'administration ^> Planificateur de tâches
echo    - Ou: schtasks /change /tn "NomTâche" /st HH:MM

echo.
echo 🗑️  Pour supprimer les tâches:
echo    schtasks /delete /tn "MyKarfour Rappels Quotidiens" /f
echo    schtasks /delete /tn "MyKarfour Programmation Sessions" /f
echo    schtasks /delete /tn "MyKarfour Nettoyage Rappels" /f

echo.
echo 🎉 Configuration terminée!
pause
