"""
Pure-Python Mapbox Vector Tile (MVT) decoder — zero native dependencies.

Only extracts feature properties (no geometry reconstruction), which is all
the field-catalog loader needs.  Drop-in for mapbox_vector_tile.decode().
"""
from __future__ import annotations

import struct
from typing import Any


# ── Low-level protobuf primitives ────────────────────────────────────────────

def _varint(buf: bytes, pos: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        b = buf[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _read_field(buf: bytes, pos: int) -> tuple[int, int, Any, int]:
    tag, pos = _varint(buf, pos)
    fn, wt = tag >> 3, tag & 7
    if wt == 0:    # VARINT
        v, pos = _varint(buf, pos)
    elif wt == 1:  # 64-bit (double)
        v = struct.unpack_from("<d", buf, pos)[0]; pos += 8
    elif wt == 2:  # LEN-delimited (bytes / sub-message / packed)
        n, pos = _varint(buf, pos)
        v = buf[pos:pos + n]; pos += n
    elif wt == 5:  # 32-bit (float)
        v = struct.unpack_from("<f", buf, pos)[0]; pos += 4
    else:
        raise ValueError(f"Unsupported protobuf wire type {wt}")
    return fn, wt, v, pos


# ── MVT message decoders ─────────────────────────────────────────────────────

def _decode_value(buf: bytes) -> Any:
    """Decode an MVT Value message to a Python scalar."""
    pos = 0
    while pos < len(buf):
        fn, wt, v, pos = _read_field(buf, pos)
        if fn == 1 and wt == 2: return v.decode("utf-8", errors="replace")  # string
        if fn == 2 and wt == 5: return v        # float32
        if fn == 3 and wt == 1: return v        # float64
        if fn == 4 and wt == 0: return v        # int64
        if fn == 5 and wt == 0: return v        # uint64
        if fn == 6 and wt == 0: return (v >> 1) ^ -(v & 1)  # sint64 zigzag
        if fn == 7 and wt == 0: return bool(v)  # bool
    return None


def _decode_feature(buf: bytes, keys: list[str], values: list[Any]) -> dict[str, Any]:
    """Decode an MVT Feature, returning its {key: value} properties."""
    props: dict[str, Any] = {}
    pos = 0
    while pos < len(buf):
        fn, wt, v, pos = _read_field(buf, pos)
        if fn == 2 and wt == 2:           # packed uint32 tags
            ti = 0
            while ti < len(v):
                ki, ti = _varint(v, ti)
                vi, ti = _varint(v, ti)
                if ki < len(keys) and vi < len(values):
                    props[keys[ki]] = values[vi]
    return props


def _decode_layer(buf: bytes) -> tuple[str, list[dict]]:
    """Decode an MVT Layer, returning (name, [{properties: {...}}])."""
    name = ""
    keys: list[str] = []
    values: list[Any] = []
    feature_bufs: list[bytes] = []
    pos = 0
    while pos < len(buf):
        fn, wt, v, pos = _read_field(buf, pos)
        if   fn == 1 and wt == 2: name = v.decode("utf-8", errors="replace")
        elif fn == 2 and wt == 2: feature_bufs.append(v)
        elif fn == 3 and wt == 2: keys.append(v.decode("utf-8", errors="replace"))
        elif fn == 4 and wt == 2: values.append(_decode_value(v))
    features = [{"properties": _decode_feature(fb, keys, values)} for fb in feature_bufs]
    return name, features


# ── Public API ───────────────────────────────────────────────────────────────

def decode(tile_bytes: bytes) -> dict[str, dict]:
    """
    Decode a raw MVT tile.

    Returns: {layer_name: {"features": [{"properties": {...}}]}}

    Drop-in replacement for mapbox_vector_tile.decode() for property-only
    access (geometry coordinates are not reconstructed).
    """
    result: dict[str, dict] = {}
    pos = 0
    while pos < len(tile_bytes):
        fn, wt, v, pos = _read_field(tile_bytes, pos)
        if fn == 3 and wt == 2:
            layer_name, features = _decode_layer(v)
            if layer_name:
                result[layer_name] = {"features": features}
    return result
