"""Offline primitives for the TDX V7.73 0x0554 tick stream.

The wire stream uses the same signed variable-length integer as the public
TDX quote protocol.  A first response contains five stream/header values and
one six-value record; every following record contains six values.  The
record-level field transforms are intentionally kept explicit because the
session/stock key is part of the stream state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Sequence


@dataclass(frozen=True)
class VarInt:
    value: int
    start: int
    end: int
    raw: bytes


def read_varint(data: bytes | bytearray | memoryview, offset: int = 0) -> VarInt:
    """Read one TDX signed varint.

    The first byte contributes six payload bits (bit 6 is the sign and bit 7
    is the continuation bit); later bytes contribute seven payload bits.  The
    wire representation is little-bit-endian, matching pytdx's K-line codec.
    """
    start = offset
    value = 0
    index = 0
    view = memoryview(data)
    while offset < len(view):
        byte = view[offset]
        offset += 1
        if index == 0:
            value |= byte & 0x3F
        else:
            value |= (byte & 0x7F) << (6 + (index - 1) * 7)
        index += 1
        if not byte & 0x80:
            break
    else:
        raise ValueError(f"truncated varint at offset {start}")
    if view[start] & 0x40:
        value = -value
    return VarInt(value, start, offset, bytes(view[start:offset]))


def iter_varints(data: bytes | bytearray | memoryview) -> Iterator[VarInt]:
    """Yield all varints in a payload and reject trailing/truncated bytes."""
    offset = 0
    while offset < len(data):
        item = read_varint(data, offset)
        yield item
        offset = item.end


def xor_unsigned(encoded: int, key: int) -> int:
    """Undo an XOR field transform from a signed wire value.

    0x0554 uses the sign bit of the varint as a stream marker.  For the
    confirmed order-number fields the decoded varint is ``-(order ^ key)``.
    ``encoded`` is therefore expected to be negative; accepting positive
    values makes this helper useful while inspecting malformed samples.
    """
    return (abs(encoded) ^ key) & 0xFFFFFFFF


def decode_order_id(encoded: int, key: int = 0x04993249) -> int:
    """Decode a bid/ask order number for the validated 000759 stream."""
    return xor_unsigned(encoded, key)


def decode_lots(encoded: int, key: int = 9) -> int:
    """Decode the lots field observed in subsequent records.

    For clean 000759 samples the wire value is ``-(lots ^ 9)``.  The odd-lot
    byte is carried by the auxiliary field and is intentionally left raw.
    """
    return xor_unsigned(encoded, key)


@dataclass(frozen=True)
class TickChunk:
    """One decoded six-value record plus its original varints."""

    values: tuple[int, ...]
    raw: tuple[bytes, ...]

    @property
    def time_raw(self) -> int:
        return self.values[0]

    @property
    def price_raw(self) -> int:
        return self.values[1]

    @property
    def lots_raw(self) -> int:
        return self.values[2]

    @property
    def aux_raw(self) -> int:
        return self.values[3]

    @property
    def bid_raw(self) -> int:
        return self.values[4]

    @property
    def ask_raw(self) -> int:
        return self.values[5]


def split_chunks(payload: bytes, *, first_header_values: int = 5) -> tuple[tuple[int, ...], TickChunk, tuple[TickChunk, ...]]:
    """Split a 0x0554 payload into header, first record and delta records.

    The first five varints are stream/header state.  The next six values form
    the first record; each remaining six values form one subsequent record.
    This works for 21/22-byte first records and variable-length later chunks,
    avoiding the earlier fixed-13-byte slicing error.
    """
    items = tuple(iter_varints(payload))
    values = tuple(item.value for item in items)
    raws = tuple(item.raw for item in items)
    if len(values) < first_header_values + 6:
        raise ValueError(f"0x0554 payload has {len(values)} values; need at least 11")
    rest = len(values) - first_header_values
    if rest % 6:
        raise ValueError(f"0x0554 value count {len(values)} does not fit 5 + 6*n")
    header = values[:first_header_values]
    first_at = first_header_values
    first = TickChunk(values[first_at:first_at + 6], raws[first_at:first_at + 6])
    later = tuple(
        TickChunk(values[i:i + 6], raws[i:i + 6])
        for i in range(first_at + 6, len(values), 6)
    )
    return header, first, later


def decode_confirmed(chunk: TickChunk, *, order_key: int = 0x04993249) -> dict[str, int | bytes]:
    """Decode fields confirmed by paired 000759 samples.

    Time and price/aux remain raw until the stream-specific initial state is
    supplied.  This is deliberate: treating them as absolute integers was the
    source of the false ``not monotonic`` conclusion in the earlier notes.
    """
    return {
        "time_encoded": chunk.time_raw,
        "price_encoded": chunk.price_raw,
        "lots": decode_lots(chunk.lots_raw),
        "aux_encoded": chunk.aux_raw,
        "bid_order_number": decode_order_id(chunk.bid_raw, order_key),
        "ask_order_number": decode_order_id(chunk.ask_raw, order_key),
        "bid_raw": chunk.raw[4],
        "ask_raw": chunk.raw[5],
    }


__all__ = [
    "VarInt", "TickChunk", "read_varint", "iter_varints", "xor_unsigned",
    "decode_order_id", "decode_lots", "split_chunks", "decode_confirmed",
]
