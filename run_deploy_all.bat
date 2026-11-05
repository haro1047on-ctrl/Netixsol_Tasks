@echo off
TITLE Netixsol Deployment Manager - Weeks 7, 8, 9, 10
echo ==============================================================================
echo       NETIXSOL MASTER DEPLOYMENT LAUNCHER (WEEKS 7, 8, 9, 10)
echo ==============================================================================
echo.
echo Launching all 4 project servers and tunnel orchestrator...
python deploy_live.py %*
pause

