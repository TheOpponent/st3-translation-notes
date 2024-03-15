# This script reads a file containing BPV1 chunks and repacks the PVR textures as extracted by extract_bpv1.py.
# The PNG files accompanying each PVR texture are converted to the PVR texture, overwriting the PVR file.
# DOSPVR, the default utility for generating PVR textures, writes backups of PVR files before overwriting.
# PVR format information is based on https://github.com/nickworonekin/puyotools/wiki/PVR-Texture

# TODO: Add PRS support.

import mmap
import os
import struct
import subprocess
import sys
from typing import NamedTuple

path = os.path.realpath(os.path.dirname(sys.argv[0]))

# Set these to the path and arguments of a utility that accepts a PNG file and outputs a PVR file.
# It is recommended that the arguments include a switch that suppresses console output, if available.
png2pvr_path = os.path.join(path, os.path.normpath(r".\lib\dospvr.exe"))

# fmt: off
PVR_PIXEL_FORMATS = {0: ("-cf", "1555",), 1: ("-cf", "565",), 2: ("-cf", "4444",)}

PVR_DATA_FORMATS = {
    0x1: ("-tw",),          # Square, twiddled
    0x2: ("-tw", "-mm",),   # Square, twiddled, mipmaps
    0x3: ("-vq",),          # VQ
    0x4: ("-vq", "-mm",),   # VQ, mipmaps
    0x5: ("-pd 4",),        # 4bpp indexed
    0x7: ("-pd 8",),        # 8bpp indexed
    0x9: (),                # Rectangle
    0xD: ("-tw",),          # Rectangle, twiddled
    0x10: ("-vq",),         # Small VQ
    0x11: ("-vq", "-tw",),  # Small VQ, twiddled
    0x12: ("-tw", "-mm",),  # Square, twiddled, mipmaps (alternate)
}
# fmt: on


class PVRInfo(NamedTuple):
    offset: int
    pixel_format: int
    data_format: int
    width: int
    height: int


class PVRError(Exception):
    pass


def repack_bpv1(
    bpv1_tables: bytes,
    texture_count: int,
    pvr_files: list,
    png_files: list,
    pvr_output_path: str,
) -> tuple[bytes, int]:
    """Recreate a BPV1 chunk, using the original BPV1 offset tables and
    new PVR textures.

    The lists of pvr_files and png_files must be sorted before passing in.

    Returns a tuple containing the new chunk and the number of textures
    that were successfully repacked."""

    if len(pvr_files) != texture_count:
        raise PVRError("Amount of PVR files does not match texture_count")

    if len(png_files) != texture_count:
        raise PVRError("Amount of PNG files does not match texture_count")

    pvr_table_offsets = []
    for i in range(0, texture_count * 12, 12):
        pvr_table_offsets.append(struct.unpack("<I", bpv1_tables[i : i + 4])[0])

    bpv1_info_table: list[PVRInfo] = []
    for i in pvr_table_offsets:
        i -= 8
        offset = struct.unpack("<I", bpv1_tables[i : i + 4])[0]
        pixel_format = int(bpv1_tables[i + 6])
        data_format = int(bpv1_tables[i + 7])
        width = struct.unpack("<I", bpv1_tables[i + 16 : i + 20])[0]
        height = struct.unpack("<I", bpv1_tables[i + 20 : i + 24])[0]

        bpv1_info_table.append(
            PVRInfo(offset, pixel_format, data_format, width, height)
        )

    pvr_pixels_data = bytearray()
    textures_repacked = 0
    for bpv1_info, pvr_file, png_file in zip(bpv1_info_table, pvr_files, png_files):
        with open(pvr_file, "rb") as pvr:
            if header := pvr.read(4) != b"PVRT":
                raise ValueError(f"{pvr_file}: Header not recognized: {header}")

            pvr.seek(8)
            pvr_pixel_format = int.from_bytes(pvr.read(1))
            pvr_data_format = int.from_bytes(pvr.read(1))
            pvr.read(2)
            pvr_width = struct.unpack("<H", pvr.read(2))[0]
            pvr_height = struct.unpack("<H", pvr.read(2))[0]
            pvr_data = pvr.read()

            # Verify input PVR data.
            if pvr_pixel_format != bpv1_info.pixel_format:
                raise PVRError(
                    f"Pixel format of input PVR file {os.path.basename(pvr_file)} ({hex(pvr_pixel_format)}) does not match BPV1 pixel format at offset {hex(bpv1_info.offset)} ({hex(bpv1_info.pixel_format)})"
                )

            if pvr_data_format != bpv1_info.data_format:
                raise PVRError(
                    f"Data format of input PVR file {os.path.basename(pvr_file)} ({hex(pvr_data_format)}) does not match BPV1 data format at offset {hex(bpv1_info.offset)} ({hex(bpv1_info.data_format)})"
                )

            if pvr_width != bpv1_info.width or pvr_height != bpv1_info.height:
                raise PVRError(
                    f"Dimensions of input PVR file {os.path.basename(pvr_file)} ({pvr_width}x{pvr_height}) do not match BPV1 dimensions at offset {hex(bpv1_info.offset)} ({bpv1_info.width}x{bpv1_info.height})"
                )

            # Verify dimensions of PNG file.
            with open(png_file, "rb") as png:
                if png.read(8) != b"\x89PNG\r\n\x1a\n":
                    raise ValueError(f"{png_file} is not a valid PNG file")

                png.read(8)
                ihdr = png.read(13)
                width, height = struct.unpack(">II", ihdr[0:8])

                if width != pvr_width or height != pvr_height:
                    raise ValueError(
                        f"Dimensions of PNG file {os.path.basename(png_file)} ({width}x{height}) do not match PVR file ({pvr_width}x{pvr_height})"
                    )

            # Do PNG to PVR conversion.
            png2pvr_args = [
                png2pvr_path,
                "-q",
                png_file,
                *PVR_DATA_FORMATS[pvr_data_format],
                *PVR_PIXEL_FORMATS[pvr_pixel_format],
                "-op",
                pvr_output_path,
            ]
            subprocess.run(png2pvr_args, shell=True)

            # Verify output.
            with open(
                os.path.join(pvr_output_path, os.path.basename(pvr_file)), "rb"
            ) as new_pvr:
                new_pvr.seek(8)
                new_pvr_pixel_format = int.from_bytes(new_pvr.read(1))
                new_pvr_data_format = int.from_bytes(new_pvr.read(1))
                new_pvr.read(2)
                new_pvr_width = struct.unpack("<H", new_pvr.read(2))[0]
                new_pvr_height = struct.unpack("<H", new_pvr.read(2))[0]

                try:
                    if new_pvr_pixel_format != bpv1_info.pixel_format:
                        raise PVRError(
                            f"Pixel format of generated PVR file for {os.path.basename(png_file)} ({hex(new_pvr_pixel_format)}) does not match BPV1 pixel format at offset {hex(bpv1_info.offset)} ({hex(bpv1_info.pixel_format)})"
                        )

                    if new_pvr_data_format != bpv1_info.data_format:
                        raise PVRError(
                            f"Data format of generated PVR file for {os.path.basename(png_file)} ({hex(new_pvr_data_format)}) does not match BPV1 data format at offset {hex(bpv1_info.offset)} ({hex(bpv1_info.data_format)})"
                        )

                    if (
                        new_pvr_width != bpv1_info.width
                        or new_pvr_height != bpv1_info.height
                    ):
                        raise PVRError(
                            f"Dimensions of generated PVR file for {os.path.basename(png_file)} ({new_pvr_width}x{new_pvr_height}) do not match BPV1 dimensions at offset {hex(bpv1_info.offset)} ({bpv1_info.width}x{bpv1_info.height})"
                        )

                    new_pvr_pixels = new_pvr.read()
                    textures_repacked += 1

                except PVRError as e:
                    print(f"Error: {e}. Skipping this PVR file.")
                    new_pvr_pixels = pvr_data

            pvr_pixels_data.extend(new_pvr_pixels)

    return (bpv1_tables + pvr_pixels_data, textures_repacked)


def search_bpv1(bpv1_file: str):
    """Open a file containing uncompressed BPV1 chunks and retrieve their locations."""

    total_bpv1_texture_count = 0
    total_textures_repacked = 0

    with open(bpv1_file, "rb") as f:
        pvr_output_path = os.path.join(os.path.dirname(bpv1_file), "pvr_output")
        os.makedirs(pvr_output_path, exist_ok=True)

        # Find all BPV1 header locations.
        with mmap.mmap(
            f.fileno(), 0, access=mmap.ACCESS_READ | mmap.ACCESS_WRITE
        ) as mm:
            bpv1_locations = [
                i for i in range(0, len(mm), 4) if mm[i : i + 4] == b"BPV1"
            ]

            for i in bpv1_locations:
                # Get header for BPV1 chunk.
                # bpv1_chunk_size includes 8 bytes of subheader length and texture count.
                bpv1_chunk_size = struct.unpack("<I", mm[i + 4 : i + 8])[0]
                bpv1_texture_count = struct.unpack("<I", mm[i + 12 : i + 16])[0]
                total_bpv1_texture_count += bpv1_texture_count
                bpv1_tables = mm[i + 16 : i + 16 + bpv1_texture_count * 56]

                pvr_files = []
                png_files = []
                for j in range(bpv1_texture_count):
                    # Get PVR texture files.
                    # PVR and PNG files are named for the input file, followed by offset and a 3-digit number.
                    bpv1_subtexture_basename = f"{bpv1_file}_{hex(i)}_{str(j).zfill(3)}"

                    pvr_filename = bpv1_subtexture_basename + ".pvr"
                    if os.path.exists(pvr_filename):
                        pvr_files.append(pvr_filename)
                    else:
                        print(
                            f"Error: PVR texture file #{str(j).zfill(3)} not found for {bpv1_file}"
                        )
                        continue

                    # Search for matching PNG files.
                    png_filename = bpv1_subtexture_basename + ".png"
                    if os.path.exists(png_filename):
                        png_files.append(png_filename)
                    else:
                        print(f"Error: PNG file {png_filename} not found for {bpv1_file}")
                        continue

                repacked_bpv1, textures_repacked = repack_bpv1(
                    bpv1_tables,
                    bpv1_texture_count,
                    pvr_files,
                    png_files,
                    pvr_output_path,
                )

                repacked_bpv1_size = len(repacked_bpv1)
                if repacked_bpv1_size != bpv1_chunk_size - 8:
                    raise ValueError(
                        f"Size of repacked BPV1 chunk for {bpv1_file} at {hex(i)} ({repacked_bpv1_size + 8}) does not match original chunk ({bpv1_chunk_size + 8})"
                    )

                mm[i + 16 : i + 16 + repacked_bpv1_size] = repacked_bpv1
                if textures_repacked:
                    print(
                        f"{bpv1_file}: Repacked {bpv1_texture_count} textures at {hex(i)}."
                    )
                    total_textures_repacked += textures_repacked

            output = bytes(mm)

    with open(bpv1_file, "wb") as file:
        file.write(output)
        print(
            f"Repacked {total_textures_repacked} out of {total_bpv1_texture_count} textures into {bpv1_file}."
        )


def main():
    if len(sys.argv) > 1:
        for i in sys.argv[1:]:
            search_bpv1(i)
    else:
        print("Specify input BPV1 file(s).")


if __name__ == "__main__":
    main()
