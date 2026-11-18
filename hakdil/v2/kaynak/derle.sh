#!/bin/sh
# HakDil derleyicisini Linux/macOS üzerinde derler
set -e
cd "$(dirname "$0")"
gcc -O2 -o hakc hakc.c
gcc -O2 -c hakrt.c -o hakrt.o
echo "Hazır: ./hakc program.hak"
