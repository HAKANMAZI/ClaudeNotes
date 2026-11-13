import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hesaptablom.formula import Engine, FErr, display, map_formula, parse_ref, shift_formula, structural_map


def val(cells, ref, extra=None):
    book = {"sheets": [{"id": "a", "name": "Sayfa1", "cells": {k: {"v": v} for k, v in cells.items()}, "colW": {}}],
            "active": 0}
    if extra:
        book["sheets"].append({"id": "b", "name": "Sayfa2", "cells": {k: {"v": v} for k, v in extra.items()},
                               "colW": {}})
    eng = Engine(lambda: book)
    r, c = parse_ref(ref)
    return eng.value(book["sheets"][0], r, c)


def test_aritmetik():
    assert val({"A1": "10", "A2": "3,5", "B1": "=A1+A2*2"}, "B1") == 17
    assert val({"A1": "=2^3*10%"}, "A1") == 0.8


def test_fonksiyonlar():
    c = {"A1": "10", "A2": "20", "A3": "30", "B1": "Elma", "B2": "Armut", "B3": "elma"}
    c.update({"C1": "=TOPLA(A1:A3)", "C2": "=ortalama(A1:A3)", "C3": '=EĞER(A1>5;"büyük";"küçük")',
              "C4": '=ETOPLA(A1:A3;">15")', "C5": '=EĞERSAY(B1:B3;"elma")',
              "C6": '=DÜŞEYARA("Armut";B1:C3;2;YANLIŞ)', "C7": "=YUVARLA(2,345;2)",
              "C8": '=BİRLEŞTİR(B1;" ";A1)', "C9": "=SUM(1,2)"})
    assert val(c, "C1") == 60
    assert val(c, "C2") == 20
    assert val(c, "C3") == "büyük"
    assert val(c, "C4") == 50
    assert val(c, "C5") == 2
    assert val(c, "C6") == 20
    assert val(c, "C7") == 2.35
    assert val(c, "C8") == "Elma 10"
    assert val(c, "C9") == 3


def test_hatalar():
    assert val({"A1": "=1/0"}, "A1") == FErr("#SAYI/0!")
    assert val({"A1": "=B1", "B1": "=A1"}, "A1") == FErr("#DÖNGÜ!")
    assert val({"A1": "=YOKBOYLE(1)"}, "A1") == FErr("#AD?")
    assert val({"A1": "=EĞERHATA(1/0;0)"}, "A1") == 0


def test_sayfalar_arasi():
    assert val({"A1": "=Sayfa2!B2*2"}, "A1", {"B2": "21"}) == 42


def test_gosterim():
    assert display(1234.5, {"fmt": "num"}) == "1.234,50"
    assert display(1234.5, {"fmt": "cur"}) == "1.234,50 ₺"
    assert display(0.25, {"fmt": "pct"}) == "%25"
    assert display(2.5) == "2,5"


def test_kaydirma():
    assert shift_formula('=A1+$B$2+Sayfa2!A1+TOPLA(A1:B3)&"A1"', 2, 1) == '=B3+$B$2+Sayfa2!A1+TOPLA(B3:C5)&"A1"'
    assert map_formula("=TOPLA(A1:A10)", structural_map(True, True, 4, 1)) == "=TOPLA(A1:A11)"
    assert map_formula("=TOPLA(A1:A10)", structural_map(True, False, 4, 2)) == "=TOPLA(A1:A8)"
    assert map_formula("=A5", structural_map(True, False, 4, 1)) == "=#BAŞV!"
