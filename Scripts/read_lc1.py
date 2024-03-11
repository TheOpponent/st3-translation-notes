# This script reads LC1 files in the 'source' subdirectory and outputs PNG files with the
# decompressed frames in a horizontal row in the 'translate' subdirectory.
# Pillow is required as a dependency.
#
# The colors of the output files are:
# 000000 707070 808080 F0F0F0

import os
import struct
import sys
from shutil import copyfile

from PIL import Image, ImageDraw

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path, "source")
translate_path = os.path.join(path, "translate")
backups_path = os.path.join(path, "backups")


def main():
    files_written = 0
    backup_files_written = 0

    os.makedirs(translate_path, exist_ok=True)
    os.makedirs(backups_path, exist_ok=True)

    for filename in [
        i for i in os.listdir(source_path) if i.lower().endswith((".lc1"))
    ]:
        try:
            with open(os.path.join(source_path, filename), "rb") as input_data:
                input_data.seek(12)

                image_num = struct.unpack("<I", input_data.read(4))[0]
                images = []
                for i in range(0, image_num):
                    input_data.seek(24 + (i * 20))
                    image_location = struct.unpack("<I", input_data.read(4))[0] + 8
                    image_height = struct.unpack("<H", input_data.read(2))[0]
                    image_width = struct.unpack("<H", input_data.read(2))[0]
                    _value1 = struct.unpack("<I", input_data.read(4))[0]
                    image_size = struct.unpack("<I", input_data.read(4))[0]

                    input_data.seek(image_location)
                    image_data = input_data.read(image_size)

                    # Draw image.
                    image = Image.new(mode="RGB", size=(image_width, image_height))
                    d = ImageDraw.Draw(image)
                    run_length = 0
                    color = 0
                    x = 0
                    y = 0

                    for byte in image_data:
                        if byte == 0:
                            continue

                        run_length = byte >> 4  # Get left nybble of current byte.
                        color = (
                            byte & 15
                        ) << 4  # Get right nybble of current byte and shift left.

                        while run_length > 0:
                            d.point([x, y], (color, color, color))
                            run_length -= 1
                            if x < image.width - 1:
                                x += 1
                            else:
                                y += 1
                                x = 0

                    images.append(image)

                for i in enumerate(images):
                    output_filename = os.path.join(
                        translate_path, filename + f"_{i[0]}" ".png"
                    )
                    if os.path.exists(output_filename):
                        print(f"{output_filename} already exists; not overwriting.")
                        continue

                    with open(output_filename, "wb") as image_output:
                        i[1].save(image_output, "png")
                        files_written += 1
                        print(f"{image_output.name}: Dimensions: {i[1].size}.")

                    # Create backup copies of the PNG files, but do not overwrite existing copies.
                    if not os.path.exists(
                        os.path.join(backups_path, filename + f"_{i[0]}" ".png")
                    ):
                        copyfile(
                            output_filename,
                            os.path.join(backups_path, filename + f"_{i[0]}" ".png"),
                        )
                        backup_files_written += 1

        except FileNotFoundError:
            print(f"{filename} not found in {source_path}.")

    if files_written > 0:
        print(f"\n{str(files_written)} file(s) written to {translate_path}.")
    else:
        print("\nNo files written.")
        return

    if backup_files_written > 0:
        print(f"{backup_files_written} file(s) written to {backups_path}.")


if __name__ == "__main__":
    main()
