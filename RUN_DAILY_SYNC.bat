@echo off
cd /d "F:\khotiyan book"
echo ========================================================
echo Raipur Land Cadastre - Daily Auto Sync Engine
echo ========================================================
python daily_d1_auto_sync.py >> daily_sync.log 2>&1
echo Done.

