@echo off
echo INICIANDO POLLING DO ERP...
cd erp_polling
start cmd /k npm start
cd ..
echo.
echo APOS GERAR produtos.json, RODE:
cd bagy_integration
python sync_gestaoclick_to_bagy.py
pause
