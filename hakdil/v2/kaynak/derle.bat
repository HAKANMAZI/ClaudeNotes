@echo off
REM HakDil derleyicisini Windows uzerinde derler (MinGW-w64 / w64devkit gerekir)
cd /d "%~dp0"
gcc -O2 -o hakc.exe hakc.c
gcc -O2 -c hakrt.c -o hakrt.o
echo Hazir: hakc program.hak
