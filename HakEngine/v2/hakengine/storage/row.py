"""Satır kodlama: Python değerleri <-> bayt dizisi."""
import struct

def encode_row(values):
    out = bytearray()
    for v in values:
        if v is None:
            out += b"\x00"
        elif isinstance(v, bool) or isinstance(v, int):
            out += b"\x01" + struct.pack("<q", int(v))
        elif isinstance(v, float):
            out += b"\x02" + struct.pack("<d", v)
        else:
            b = str(v).encode("utf-8")
            out += b"\x03" + struct.pack("<H", len(b)) + b
    return bytes(out)


def decode_row(data):
    vals, i = [], 0
    while i < len(data):
        t = data[i]; i += 1
        if t == 0:
            vals.append(None)
        elif t == 1:
            vals.append(struct.unpack_from("<q", data, i)[0]); i += 8
        elif t == 2:
            vals.append(struct.unpack_from("<d", data, i)[0]); i += 8
        else:
            n = struct.unpack_from("<H", data, i)[0]; i += 2
            vals.append(data[i:i + n].decode("utf-8")); i += n
    return vals


