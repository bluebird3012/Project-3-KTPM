"""Generate valid PNG files with exact byte sizes for a finite configured M.

The caller must set the matching limit on the local Moodle test environment.
A legal ancillary PNG chunk pads the small image; no external downloads needed.
"""
from pathlib import Path
import argparse
import struct
import zlib

ROOT = Path(__file__).resolve().parent / 'images'


def padded_png(source: bytes, size: int) -> bytes:
    if not source.startswith(b'\x89PNG\r\n\x1a\n') or source[-8:-4] != b'IEND':
        raise ValueError('Expected a PNG ending with IEND')
    pad = size - len(source) - 12
    if pad < 0 or size > 64 * 1024 * 1024:
        raise ValueError('Size must fit valid PNG padding and be <= 64 MiB; supply larger files manually.')
    payload = b'\0' * pad
    chunk_type = b'paDd'  # ancillary, private, reserved uppercase, safe to copy
    chunk = struct.pack('>I', pad) + chunk_type + payload + struct.pack('>I', zlib.crc32(chunk_type + payload) & 0xffffffff)
    return source[:-12] + chunk + source[-12:]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('max_bytes', type=int)
    m = parser.parse_args().max_bytes
    source = (ROOT / 'f1_avatar.png').read_bytes()
    for name, delta in [('boundary_minus1.png', -1), ('boundary_max.png', 0), ('boundary_plus1.png', 1)]:
        path = ROOT / name
        path.write_bytes(padded_png(source, m + delta))
        print(f'{path.name}: {path.stat().st_size} bytes')

if __name__ == '__main__':
    main()
