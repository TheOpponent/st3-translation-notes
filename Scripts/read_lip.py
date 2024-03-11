# This script reads LIP files in the 'source' subdirectory.
# It outputs CSV files in the 'translate' subdirectory using pipe characters | as delimiters.
#
# Each row contains: the voice index, dialogue offset address in hex, dialogue text converted to UTF-8,
# lip movement command sequence address in hex, and raw bytes of command sequence separated by spaces.

import os
import struct
import sys
from shutil import copyfile

from utils.utils import read_string

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path, "source")
translate_path = os.path.join(path, "translate")
backups_path = os.path.join(path, "backups")


def main():
    files_written = 0
    backup_files_written = 0

    os.makedirs(translate_path, exist_ok=True)
    os.makedirs(backups_path, exist_ok=True)

    for file in [i for i in os.listdir(source_path) if i.lower().endswith((".lip"))]:
        # If a CSV for the file already exists, do not process.
        if os.path.exists(os.path.join(translate_path, file + ".csv")):
            print(
                f"{os.path.join(translate_path, file + '.csv')} already exists; not overwriting."
            )
            continue

        # Read files in working directory. If first 4 bytes do not contain signature ALPD, skip the file.
        with open(os.path.join(source_path, file), "rb") as f:
            if f.read(4) != b"ALPD":
                return

            # Size of this file 0x08 to end of data area.
            file_size = struct.unpack("<I", f.read(4))[0]
            # Number of lines. Multiply by 12 and add 8 for first offset.
            table_length = struct.unpack("<I", f.read(4))[0]

            # Read the offset table and load the data into a list.
            # Offsets in the table are 8 bytes before actual data. The output CSV does not include this adjustment.
            table_data = []
            for i in range(table_length):
                f.seek((i + 1) * 12)
                voice_index = struct.unpack("<I", f.read(4))[0]
                text_location = struct.unpack("<I", f.read(4))[0]
                cmd_location = struct.unpack("<I", f.read(4))[0]

                text = ""
                cmd = ""

                # Read dialogue string.
                f.seek(text_location + 8)
                text = read_string(f)

                # Read command sequence.
                f.seek(cmd_location + 8)
                cmd = read_string(f, encoding=None).hex()

                table_data.append([voice_index, text_location, text, cmd_location, cmd])

            with open(
                os.path.join(translate_path, file + ".csv"), "w", encoding="utf-8"
            ) as output_file:
                for i in table_data:
                    output_file.write(
                        "|".join([str(i[0]), hex(i[1]), i[2], hex(i[3]), i[4]]) + "\n"
                    )

            files_written += 1

            # Create backup copies of the script CSV files, but do not overwrite existing copies.
            if not os.path.exists(os.path.join(backups_path, file + ".csv")):
                copyfile(
                    os.path.join(translate_path, file + ".csv"),
                    os.path.join(backups_path, file + ".csv"),
                )
                backup_files_written += 1

        print(f"{file}: Data area length: {file_size}. Entries: {table_length}.")

    if files_written > 0:
        print(f"\n{files_written} CSV file(s) written to {translate_path}.")

    else:
        print("No files written.")

    if backup_files_written > 0:
        print(f"\n{backup_files_written} CSV file(s) written to {backups_path}.")


if __name__ == "__main__":
    main()
