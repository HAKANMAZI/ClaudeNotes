"""HakEngine v2 başlatıcı.

  python hakengine.py veritabanim             etkileşimli komut satırı
  python hakengine.py veritabanim dosya.sql   SQL dosyasını çalıştırır
"""
import sys
from hakengine.cli import main

if __name__ == "__main__":
    sys.exit(main())
