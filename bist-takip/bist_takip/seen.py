"""Daha önce görülen KAP bildirimlerini yerel bir dosyada tutar.

Böylece uygulama her açıldığında son ziyaretten beri gelen yeni bildirimleri işaretleyebilir.
"""

import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "seen_disclosures.json"


def load_seen(path: Path = DEFAULT_PATH) -> set[str]:
    try:
        return set(json.loads(path.read_text(encoding="utf-8")))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def save_seen(links: set[str], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(links), ensure_ascii=False, indent=0), encoding="utf-8")
