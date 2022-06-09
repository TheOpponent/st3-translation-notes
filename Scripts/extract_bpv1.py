# This script reads a file containing BPV1 chunks and attempts to extract PVR textures. 
# The PVR header is formed manually using information from https://github.com/nickworonekin/puyotools/wiki/PVR-Texture
# Note that the output files may contain invalid PVR format information, and some fields are currently unknown.

import mmap
import struct
import sys
from collections import namedtuple


def extract_bpv1(bpv1_file):

    textures_written = 0
    BPV1Texture = namedtuple("BPV1Texture","offset, format, value1, value2, width, height, value3, value4, value5, value6, value7")

    with open(bpv1_file,"rb") as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            while True:

                # Search for BPV1 signature.
                bpv1_pos = mm.find(b'BPV1',mm.tell())

                if bpv1_pos != -1:
                    mm.seek(bpv1_pos)
                    mm.read(4)
                    bpv1_size = struct.unpack("<I",mm.read(4))[0]
                    header_length = struct.unpack("<I",mm.read(4))[0] # Appears to always be 0x8.
                    groups_num = struct.unpack("<I",mm.read(4))[0]    # Number of data groups in this chunk.

                    groups = []
                    textures = []
                    for _ in range(groups_num):
                        # Group data: offset, unknown value 1, unknown value 2
                        groups.append((struct.unpack("<I",mm.read(4))[0],
                                    struct.unpack("<I",mm.read(4))[0],
                                    struct.unpack("<I",mm.read(4))[0]))

                    for _ in range(groups_num):
                        # Read 11 4-byte values as BPV1 texture properties. The last 5 values appear to always be 0.
                        textures.append(BPV1Texture(struct.unpack("<I",mm.read(4))[0],
                                        mm.read(4)[2:],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0],
                                        struct.unpack("<I",mm.read(4))[0]))

                    # Create PVR textures.
                    for i,data in enumerate(textures):
                        mm.seek(bpv1_pos + data.offset + 8)
                        abs_offset = mm.tell()

                        try:
                            # Texture size is calculated from offset of next texture, minus current offset.
                            texture_size = textures[i+1].offset - data.offset
                            texture_data = mm.read(texture_size)
                        except IndexError:
                            # For last texture, subtract from BPV1 chunk size instead.
                            texture_data = mm.read(bpv1_size - data.offset)

                        chunk_size = struct.pack("<I",len(texture_data) + 8)

                        filename = "_" + hex(abs_offset)

                        output = b'PVRT' + chunk_size + data.format + b'\x00\x00' + struct.pack("<H",data.width) + struct.pack("<H",data.height) + texture_data

                        with open(bpv1_file + filename + ".pvr","wb") as output_file:
                            output_file.write(output)
                            print(f"{output_file.name}: Wrote {len(output)} bytes. PVR format: {hex(data.format[0])}, {hex(data.format[1])}. Dimensions: {data.width} x {data.height}.")
                            textures_written += 1

                else:
                    print(f"Extracted {textures_written} textures.")
                    break


def main():

    if len(sys.argv) > 1:
        for i in sys.argv[1:]:
            extract_bpv1(i)
    else:
        print("Specify input file(s) containing BPV1 data.")

if __name__ == "__main__":
    main()