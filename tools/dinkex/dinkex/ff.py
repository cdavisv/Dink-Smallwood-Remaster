"""Reader for Dink ``dir.ff`` archives.

Layout (FFReader.h:15, FFReader.cpp:144-157; bible 04 section 1)::

    int32 count
    count x { int32 offset; char name[13]; }     # packed, 17 bytes each
    ... raw file data ...

The last record is a sentinel with an empty name whose offset is the file
size.  A file's length is the next record's offset minus its own; if the next
offset is 0 the reader skips one record (FFReader.cpp:157).  Names are
upper-case 8.3 and are lower-cased on load.

Trap found while verifying against the shipped data: three archives also
contain an entry named ``dir.ff`` (a copy of the archive header itself, not a
BMP).  Callers that want frames must filter by extension.
"""

import struct
from dataclasses import dataclass

RECORD = struct.Struct("<i13s")  # 17 bytes, no padding with "<"


@dataclass(frozen=True)
class FFEntry:
    index: int          # record number in the archive (0-based)
    name: str           # lower-cased
    offset: int
    size: int


class FFError(Exception):
    pass


def parse_ff(data):
    """Parse the bytes of a .ff archive into a list of FFEntry.

    The sentinel is not returned.  Tolerates the zero-offset skip rule and
    clamps ranges to the file size rather than raising on odd archives.
    """
    if len(data) < 4:
        raise FFError("archive shorter than its header")
    (count,) = struct.unpack_from("<i", data, 0)
    if count < 0 or 4 + count * RECORD.size > len(data):
        raise FFError("bad record count %d" % count)
    recs = [RECORD.unpack_from(data, 4 + i * RECORD.size) for i in range(count)]
    entries = []
    for i, (off, raw) in enumerate(recs):
        name = raw.split(b"\0")[0].decode("latin1").lower()
        if not name:
            continue  # sentinel (or blank record)
        j = i + 1
        end = recs[j][0] if j < count else len(data)
        if end == 0 and j + 1 < count:      # FFReader.cpp:157 skip rule
            end = recs[j + 1][0]
        if end == 0 or end > len(data):
            end = len(data)
        size = max(0, end - off)
        entries.append(FFEntry(i, name, off, size))
    return entries


def read_ff(path):
    with open(path, "rb") as f:
        data = f.read()
    return data, parse_ff(data)
