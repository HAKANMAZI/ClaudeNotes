@echo off
rem Hesap Tablom'u tek bir HesapTablom.exe dosyasina derler.
python -m pip install -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name HesapTablom --icon assets\icon.ico --add-data "assets;assets" app.py
echo.
echo Bitti: dist\HesapTablom.exe
pause
