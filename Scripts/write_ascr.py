# This script searches for CSV files in the 'translate' subdirectory recursively and inserts the strings
# within into an SBXU, SBN, or ASCR file with a corresponding filename in the 'source' subdirectory, 
# matching the same path structure as the CSV file.
# It outputs files in the 'output' subdirectory with the corresponding extension.
# This assumes all string offsets are contiguous.
#
# The first line in a CSV file contains a blank string.
# The offset of this line is used as the starting point.

import csv
import os
import struct
import sys
from glob import glob

from utils.prs import compress, PRSError
from utils.ascr import ASCRError, write_ascr

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path, "translate")
source_path = os.path.join(path, "source")
sbxu_path = os.path.join(source_path, "sbxu")
output_path = os.path.join(path, "output")


def main():
    files_written = 0
    warnings = 0
    errors = 0

    os.makedirs(output_path, exist_ok=True)

    if len(sys.argv) > 1:
        file_list = []
        for i in sys.argv[1:]:
            file_list.append((i + ".csv" if not i.endswith(".csv") else i))

    else:
        file_list = [i for i in glob(f"{translate_path}/**/*.csv", recursive=True)]

    # Only process CSV files for which a SBX, SBN, or ASCR with the same base name exists.
    # Retain the relative path components found in the translate_path.
    for translate_file in file_list:
        translate_relative_path = os.path.dirname(
            os.path.relpath(translate_file, translate_path)
        )
        translate_base_name = os.path.splitext(os.path.basename(translate_file))[0]

        if translate_relative_path != "":
            os.makedirs(
                os.path.join(output_path, translate_relative_path), exist_ok=True
            )

        # If source is SBX, search for SBXU file.
        if translate_base_name.casefold().endswith(".sbx"):
            source_file = os.path.join(
                sbxu_path, os.path.splitext(translate_base_name)[0] + ".SBXU"
            )
            if not os.path.exists(source_file):
                print(
                    f"[Error] {translate_file}: SBXU file not found in {sbxu_path}."
                )
                errors += 1
                continue
            compressed = True
        elif translate_base_name.casefold().endswith((".sbn", ".ascr")):
            if len(sys.argv) > 1:
                source_file = os.path.join(
                    source_path, os.path.basename(translate_base_name)
                )
            else:
                source_file = os.path.join(
                    source_path, translate_relative_path, translate_base_name
                )
            if not os.path.exists(source_file):
                print(
                    f"[Error] {translate_file}: Source file not found in {source_path}."
                )
                errors += 1
                continue
            compressed = False
        else:
            continue

        with open(
            os.path.join(translate_path, translate_relative_path, translate_file),
            encoding="utf-8",
        ) as file:
            strings = list(csv.reader(file, delimiter="|"))

        with open(source_file, "rb") as ascr_data:
            try:
                if compressed is True:
                    new_ascr, new_warnings = write_ascr(
                        ascr_data, strings, add_header=False, filename=translate_file
                    )
                    # Add original header size of 8 to length of new ASCR data for
                    # uncompressed data size in PRS header.
                    try:
                        output = compress(
                            b"ASCR" + struct.pack("<I", len(new_ascr) + 8) + new_ascr
                        )
                    except PRSError as e:
                        print(f"[Error] {source_file}: {e}")
                        errors += 1
                        continue

                elif compressed is False:
                    output, new_warnings = write_ascr(
                        ascr_data, strings, filename=translate_file
                    )
            except ASCRError as e:
                print(f"[Error] {source_file}: {e}")
                errors += 1
                continue

        warnings += new_warnings

        with open(
            os.path.join(output_path, translate_relative_path, translate_base_name),
            "wb",
        ) as file:
            file.write(output)
            print(
                f"{translate_base_name}: {len(output)} ({hex(len(output))}) bytes written."
            )

        files_written += 1

    if files_written > 0:
        print(f"\n{str(files_written)} file(s) written to {output_path}.")

    if errors > 0 or warnings > 0:
        print(
            f"\n{errors} error(s) and {warnings} warning(s) raised. See output for details."
        )


if __name__ == "__main__":
    main()
