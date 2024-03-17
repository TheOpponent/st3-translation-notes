# This script reads files in the 'source/ctpa' subdirectory containing one CTPA chunk.
# Text data is processed into strings. The text format is similar to ASCR.

import os
import struct
import sys
from shutil import copyfile

from utils.ascr import read_string


def main():    

    path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
    ctpa_path = os.path.join(path, "source", "ctpa")
    translate_path = os.path.join(path, "translate", "ctpa")
    backups_path = os.path.join(path, "backups", "ctpa")

    translate_csv_files_written = 0
    backup_files_written = 0
    warnings = 0
    errors = 0

    os.makedirs(ctpa_path, exist_ok=True)

    if len(sys.argv) > 1:
        file_list = sys.argv[1:]
    else:
        file_list = [i for i in os.listdir(ctpa_path)]
        if len(file_list) == 0:
            print(f"Place files containing one CTPA chunk in {ctpa_path}.")
            return

    os.makedirs(translate_path, exist_ok=True)
    os.makedirs(backups_path, exist_ok=True)

    for file in file_list:
        translate_csv_file = os.path.join(translate_path, file + ".csv")
        # If a CSV for the file already exists, do not process.
        if os.path.exists(translate_csv_file):
            print(f"[Warning] {translate_csv_file} already exists; not overwriting.")
            warnings += 1
            continue

        with open(os.path.join(ctpa_path, file), "rb") as data:
            if data.read(4) != b"CTPA":
                print(f"[Error] {file}: Not a CTPA file.")
                errors += 1
                continue

            data.seek(8)
            text_count = struct.unpack("<I", data.read(4))[0]
            text_location = struct.unpack("<I", data.read(4))[0] + 8

            text_entries = []

            for i in range(text_count):
                data.seek(text_location + (i * 4))
                data_location = struct.unpack("<I", data.read(4))[0] + 8

                if data_location == 8:
                    text_entries.append(["0x0",""])
                else:
                    data.seek(data_location)
                    text = read_string(data)

                    text_entries.append([str(i) for i in [hex(data_location - 8), text]])

            print(
                f"{file}: Text offset table location: {hex(text_location)}, entries: {text_count}."
            )

            with open(translate_csv_file, "w", encoding="utf-8") as output_file:
                for i in text_entries:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                translate_csv_files_written += 1
            backup_csv_file = os.path.join(backups_path, file + ".csv")

            # Create backup copies of the script CSV files, but do not overwrite existing copies.
            if not os.path.exists(backup_csv_file):
                copyfile(
                    translate_csv_file,
                    backup_csv_file,
                )
                backup_files_written += 1

    if translate_csv_files_written > 0:
        print(
            f"\n{translate_csv_files_written} CSV file(s) written to {translate_path}."
        )

    else:
        print("No files written.")

    if backup_files_written > 0:
        print(f"{backup_files_written} CSV file(s) written to {backups_path}.")

    if errors > 0 or warnings > 0:
        print(
            f"\n{errors} error(s) and {warnings} warning(s) raised. See output for details."
        )


if __name__ == "__main__":
    main()
