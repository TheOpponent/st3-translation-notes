# This script reads a file containing BPV1 chunks and attempts to extract PVR textures.
# The PVR header is formed manually using information from https://github.com/nickworonekin/puyotools/wiki/PVR-Texture
# Note that the output files may contain invalid PVR format information, and some fields are currently unknown.

import io
import mmap
import os
import struct
import subprocess
import sys
from collections import namedtuple
from utils import prs

path = os.path.realpath(os.path.dirname(sys.argv[0]))

BPV1Texture = namedtuple(
    "BPV1Texture",
    "offset, format, value1, value2, width, height, value3, value4, value5, value6, value7",
)

# Set these to the path and arguments of a utility that accepts a PVR file and outputs a PNG file.
# It is recommended that the arguments include a switch that suppresses console output, if available.
pvr2png_path = os.path.join(path, os.path.normpath(r".\lib\pvr2png.exe"))
pvr2png_args = ["-q"]
quiet = False


def decompress_bpv1(bpv1_file):
    """Open a file containing PRS-compressed BPV1 chunks. Each chunk is loaded
    into a buffer and decompressed in place, then passed to extract_bpv1 with the
    relative location added to the filename."""

    files_written = 0
    with open(bpv1_file, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            while True:
                # Search for BPV1 signature.
                bpv1_pos = mm.find(b"BPV1", mm.tell())

                if bpv1_pos != -1:
                    mm.seek(bpv1_pos)
                    buffer = b""
                    cprs_data = bytearray()
                    while buffer != b"CPRS":
                        buffer = mm.read(4)
                        cprs_data += buffer
                    cprs_data += mm.read(4)

                    bpv1_decompressed = prs.decompress(cprs_data)
                    # Skip invalid data.
                    if bpv1_decompressed is None:
                        continue

                    with io.BytesIO(bpv1_decompressed) as bpv1_stream:
                        files_written += extract_bpv1(
                            bpv1_file, bpv1_stream, filename_offset=bpv1_pos
                        )

                else:
                    print(f"Extracted {files_written} textures.")
                    break


def search_bpv1(bpv1_file):
    """Open a file containing uncompressed BPV1 chunks."""

    files_written = 0
    with open(bpv1_file, "rb") as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            while True:
                # Search for BPV1 signature.
                bpv1_pos = mm.find(b"BPV1", mm.tell())

                if bpv1_pos != -1:
                    files_written += extract_bpv1(bpv1_file, mm, bpv1_pos)

                else:
                    print(f"Extracted {files_written} textures.")
                    break


def extract_bpv1(bpv1_file, mm, bpv1_pos=0, filename_offset=0):
    """Extract BPV1 subtextures from bpv1_file opened at memory map mm, at bpv1_pos.
    filename_offset is added to the address in the filename and is specified by
    decompress_bpv1.

    Returns the number of subtextures written."""

    global quiet

    mm.seek(bpv1_pos)
    mm.read(4)
    bpv1_size = struct.unpack("<I", mm.read(4))[0]
    _header_length = struct.unpack("<I", mm.read(4))[0]  # Appears to always be 0x8.
    groups_num = struct.unpack("<I", mm.read(4))[
        0
    ]  # Number of data groups in this chunk.

    groups = []
    textures = []
    for _ in range(groups_num):
        # Group data: offset, unknown value 1, unknown value 2
        groups.append(
            (
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
            )
        )

    for _ in range(groups_num):
        # Read 11 4-byte values as BPV1 texture properties. The last 5 values appear to always be 0.
        textures.append(
            BPV1Texture(
                struct.unpack("<I", mm.read(4))[0],
                mm.read(4)[2:],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
                struct.unpack("<I", mm.read(4))[0],
            )
        )

    # Create PVR textures.
    subtextures_written = 0
    for i, data in enumerate(textures):
        mm.seek(bpv1_pos + data.offset + 8)

        try:
            # Texture size is calculated from offset of next texture, minus current offset.
            texture_size = textures[i + 1].offset - data.offset
            texture_data = mm.read(texture_size)
        except IndexError:
            # For last texture, subtract from BPV1 chunk size instead.
            texture_data = mm.read(bpv1_size - data.offset)

        chunk_size = struct.pack("<I", len(texture_data) + 8)

        filename = f"_{hex(bpv1_pos + filename_offset)}_{subtextures_written}"

        output = (
            b"PVRT"
            + chunk_size
            + data.format
            + b"\x00\x00"
            + struct.pack("<H", data.width)
            + struct.pack("<H", data.height)
            + texture_data
        )

        with open(bpv1_file + filename + ".pvr", "wb") as output_file:
            output_file.write(output)
            if not quiet:
                print(
                    f"{output_file.name}: Wrote {len(output)} bytes. PVR format: {hex(data.format[0])}, {hex(data.format[1])}. Dimensions: {data.width} x {data.height}."
                )
            subtextures_written += 1

        # Convert PVR texture to PNG.
        pvr_convert = subprocess.run(
            [pvr2png_path, bpv1_file + filename + ".pvr", bpv1_file + filename + ".png"]
            + pvr2png_args,
            shell=True,
        )
        pvr_convert.check_returncode()

    return subtextures_written


def main():
    global quiet

    if len(sys.argv) > 1:
        if "-q" in sys.argv:
            quiet = True

        if "-c" in sys.argv:
            for i in sys.argv[1:]:
                if os.path.isfile(i):
                    decompress_bpv1(i)
        else:
            for i in sys.argv[1:]:
                if os.path.isfile(i):
                    search_bpv1(i)

    else:
        print(
            "Specify input file(s) containing BPV1 data.\n",
            "Arguments:",
            "-c: Input is PRS-compressed BPV1 data.",
            "-q: Quiet mode -- do not print information on written files."
        )


if __name__ == "__main__":
    main()
