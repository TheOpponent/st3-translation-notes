# This script takes a file containing ADCG chunks and decompresses them.
# Pillow is required as a dependency.
#
# The decompressed ADCG chunks are output in the working directory with the extension .adcg.
# The decompressed image data is then weaved into a complete image and saved as PNG.
# In files that contain them, ADCG headers are preceded by an AGR1 or AGR2 signature,
# which is followed by 00 00 00 00.
# Some values in the ADCG header are currently unknown.

import io
import mmap
import os
import struct
import subprocess
import sys
from collections import namedtuple
from PIL import Image
from utils import prs

path = os.path.realpath(os.path.dirname(sys.argv[0]))

# Set these to the path and arguments of a utility that accepts a PVR file and output a PNG file.
# It is recommended that the arguments include a switch that suppresses console output, if available.
pvr2png_path = os.path.join(path,os.path.normpath(r".\lib\pvr2png.exe"))
pvr2png_args = [pvr2png_path,"~temp.pvr","~temp.png","-q"]

def weave_adcg(input_data):
    """Extracts the PVR subtextures from an uncompressed ADCG chunk,
    and attmpts to assemble it into a full image based on the properties
    in the ADCG header."""

    ADCGSubTexture = namedtuple("ADCGSubTexture","id offset x y value1")

    with io.BytesIO(input_data) as stream:
        signature = stream.read(4)
        adcg_size = struct.unpack("<I",stream.read(4))[0]
        value1 = stream.read(4) # 00 00 00, followed by a single byte. Possible signed 2-byte value?
        textures_num = struct.unpack("<I",stream.read(4))[0]

        texture_width = struct.unpack("<H",stream.read(2))[0]
        texture_height = struct.unpack("<H",stream.read(2))[0]
        value2 = stream.read(4) # 18 00 00 00. Offset - 8?

        pvr_format = stream.read(4)[0:2]

        total_width = struct.unpack("<H",stream.read(2))[0]
        total_height = struct.unpack("<H",stream.read(2))[0]

        # Initialize output image.
        output_image = Image.new("RGBA",(total_width,total_height))

        textures = []

        for _ in range(textures_num):
            textures.append(ADCGSubTexture(struct.unpack("<I",stream.read(4))[0],
                                struct.unpack("<I",stream.read(4))[0],
                                struct.unpack("<H",stream.read(2))[0],
                                struct.unpack("<H",stream.read(2))[0],
                                stream.read(4)))

        # Create PVR textures.
        for i,data in enumerate(textures):
            stream.seek(data.offset + 32 + (16 * i))

            try:
                # Texture size is calculated from offset of next texture, plus 16.
                texture_size = textures[i+1].offset - data.offset + 16
                texture_data = stream.read(texture_size)
            except IndexError:
                # For last texture, read to end of file.
                texture_data = stream.read(adcg_size - data.offset + 16)

            chunk_size = struct.pack("<I",len(texture_data) + 8)

            output = b'PVRT' + chunk_size + pvr_format + b'\x00\x00' + struct.pack("<H",texture_width) + struct.pack("<H",texture_height) + texture_data

            with open("~temp.pvr","wb") as output_file:
                output_file.write(output)

            # Convert PVR texture to PNG.
            pvr_convert = subprocess.run(pvr2png_args,shell=True)
            pvr_convert.check_returncode()

            # Load converted texture into an Image object.
            with Image.open("~temp.png") as png:
                output_image.paste(png,(data.x,data.y))

        return output_image


def extract_adcg(input_file,offset=0,end=-1):
    """From input_file, searches for ADCG chunks and decompresses them.
    The original uncompressed ADCG data is saved to file, as its header is
    required to reconstruct the file after editing the image.
    Each chunk is then assembled into a complete image file and saved as PNG.

    If the offset argument is set, start searching that many bytes into the file.
    If the end argument is set, stop searching after this many bytes."""

    adcg_index = 0
    files_written = 0

    with open(input_file,"rb") as f:

        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:

            if end < 0:
                end = len(mm)

            while True:
                # Decompress a single ADCG chunk.
                adcg_pos = mm.find(b'ADCG',mm.tell())

                if adcg_pos > end:
                    break

                if adcg_pos != -1:
                    mm.seek(adcg_pos)

                    # Skip offset bytes, but attempt to keep index number accurate.
                    if mm.tell() >= offset:
                        abs_offset = hex(mm.tell())
                        adcg_prs_data = bytearray()

                        while True:
                            buffer = mm.read(4)
                            adcg_prs_data += buffer
                            if buffer == b'EOFC':
                                adcg_prs_data += mm.read(4)
                                break

                        try:
                            adcg_uncompressed = bytes(prs.decompress(adcg_prs_data))
                        except:
                            print(f"Error processing ADCG chunk at {abs_offset}. Continuing with next chunk.")
                            continue

                        # Save uncompressed ADCG data and PNG to file.
                        filename = input_file + "_" + str(adcg_index).zfill(4) + "_" + abs_offset

                        with open(filename + ".adcg","wb") as raw_file:
                            raw_file.write(adcg_uncompressed)

                        output_image = weave_adcg(adcg_uncompressed)

                        with open(filename + ".png","wb") as output_file:
                            output_image.save(output_file)
                            files_written += 1
                            print(f"{output_file.name}: Dimensions: {output_image.size}.")

                    else:
                        print(f"Skipping ADCG chunk {str(adcg_index).zfill(4)} at {hex(mm.tell())}.")
                        mm.seek(4,1)

                    adcg_index += 1

            print(f"Wrote {files_written} ADCG + PNG file pairs.")

    if os.path.isfile("~temp.pvr"):
        os.remove("~temp.pvr")
    if os.path.isfile("~temp.png"):
        os.remove("~temp.png")


def main():

    if len(sys.argv) > 2:
        if len(sys.argv) >= 4:
            extract_adcg(sys.argv[1],int(sys.argv[2]),int(sys.argv[3]))
        elif len(sys.argv) == 3:
            extract_adcg(sys.argv[1],int(sys.argv[2]))
        else:
            extract_adcg(sys.argv[1])
    elif len(sys.argv) == 2:
        extract_adcg(sys.argv[1])
    else:
        print("Specify input file containing ADCG data.\nOptional arguments: number of bytes to skip; number of bytes to search.")


if __name__ == "__main__":
    main()