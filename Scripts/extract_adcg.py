# This script takes a file containing an uncompressed ADCG chunk and outputs PVR textures.
# The textures have the same format and resolution. The output file names include the
# offset and the position where they would be placed when rendered in-game.
# Some values are currently unknown.

import mmap
import struct
import sys
from collections import namedtuple


def extract_adcg(adcg_file):

    textures_written = 0
    ADCGSubTexture = namedtuple("ADCGTexture","id offset x y value1")

    with open(adcg_file,"rb") as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            mm.read(4)
            adcg_size = struct.unpack("<I",mm.read(4))[0]
            value1 = mm.read(4) # 00 00 00, followed by a single byte. Possible signed 2-byte value?
            textures_num = struct.unpack("<I",mm.read(4))[0]

            texture_width = struct.unpack("<H",mm.read(2))[0]
            texture_height = struct.unpack("<H",mm.read(2))[0]
            value2 = mm.read(4) # 18 00 00 00. Offset - 8?

            pvr_format = mm.read(4)[0:2]

            total_width = struct.unpack("<H",mm.read(2))[0]
            total_height = struct.unpack("<H",mm.read(2))[0]

            textures = []

            for _ in range(textures_num):
                textures.append(ADCGSubTexture(struct.unpack("<I",mm.read(4))[0],
                                   struct.unpack("<I",mm.read(4))[0],
                                   str(struct.unpack("<H",mm.read(2))[0]),
                                   str(struct.unpack("<H",mm.read(2))[0]),
                                   mm.read(4)))

            # Create PVR textures.
            for i,data in enumerate(textures):
                mm.seek(data.offset + 32 + (16 * i))
                abs_offset = mm.tell()

                try:
                    # Texture size is calculated from offset of next texture, plus 16.
                    texture_size = textures[i+1].offset - data.offset + 16
                    texture_data = mm.read(texture_size)
                except IndexError:
                    # For last texture, read to end of file.
                    texture_data = mm.read(adcg_size - data.offset + 16)

                chunk_size = struct.pack("<I",len(texture_data) + 8)

                filename = f"_{hex(abs_offset)}_({data.x}, {data.y})"

                output = b'PVRT' + chunk_size + pvr_format + b'\x00\x00' + struct.pack("<H",texture_width) + struct.pack("<H",texture_height) + texture_data

                with open(adcg_file + filename + ".pvr","wb") as output_file:
                    output_file.write(output)
                    print(f"{output_file.name}: Wrote {len(output)} bytes. PVR format: {hex(pvr_format[0])}, {hex(pvr_format[1])}. Dimensions: {texture_width} x {texture_height}. Position: ({data.x}, {data.y}).")
                    textures_written += 1                

            print(f"Extracted {textures_written} textures.")


def main():

    if len(sys.argv) > 1:
        for i in sys.argv[1:]:
            extract_adcg(i)
    else:
        print("Specify input file(s) containing ADCG data.")

if __name__ == "__main__":
    main()
