"""HakEngine v1 - eğitim amaçlı ilişkisel veritabanı motoru."""
__version__ = "1.0.0"
from .errors import DBError
from .engine import Database
from .cli import print_result
