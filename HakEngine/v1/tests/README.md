# tests — Birim testleri

Python'un kendi `unittest` modülü kullanılır. Ek paket gerekmez.

| Test | Neyi kontrol eder |
|---|---|
| `test_select_where_order` | WHERE ve ORDER BY |
| `test_aggregate` | COUNT, SUM, AVG |
| `test_primary_key` | Aynı anahtarla ikinci kayıt reddedilir |
| `test_update_delete` | UPDATE ve DELETE |
| `test_rollback` | ROLLBACK değişiklikleri geri alır |
| `test_persistence` | Veritabanı kapatılıp açılınca veri korunur |
| `test_many_rows` | Beş bin satır ve indeks araması |
| `test_crash_recovery` | Yarım kalan commit journal ile kurtarılır |

## Kullanım

`v1` klasöründen:

```bash
python -m unittest discover tests
```

Tek bir testi çalıştırmak:

```bash
python -m unittest tests.test_hakengine.HakEngineTest.test_rollback
```

Beklenen çıktı:

```
........
Ran 8 tests in 0.040s

OK
```
