# This script reads a CSV file in the translate subdirectory and inserts the strings
# within into an SBXU or SBN file with a corresponding filename in the source subdirectory.
# It outputs files in the 'output' subdirectory with the corresponding extension.
# This assumes all string offsets are contiguous.
#
# The first line in a CSV file contains a blank string.
# The offset of this line is used as the starting point.

import csv
import os
import struct
import sys

from utils import prs
from utils.ascr import ParsingError, write_ascr

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path, "translate")
source_path = os.path.join(path, "source")
sbxu_path = os.path.join(source_path, "sbxu")
output_path = os.path.join(path, "output2")


def main():
    files_written = 0
    warnings = 0
    errors = 0

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    if len(sys.argv) > 1:
        file_list = []
        for i in sys.argv[1:]:
            file_list.append((i + ".csv" if not i.endswith(".csv") else i))

    else:
        file_list = [
            i for i in os.listdir(translate_path) if i.casefold().endswith(".csv")
        ]

    # Only process CSV files for which a SBX with the same base name exists.
    for translate_file in file_list:
        translate_base_name = os.path.splitext(translate_file)[0]

        # If source is SBX, search for SBXU file.
        if translate_base_name.casefold().endswith(".sbx"):
            source_file = os.path.join(
                sbxu_path, os.path.splitext(translate_base_name)[0] + ".SBXU"
            )
            script_type = "sbx"
        elif translate_base_name.casefold().endswith(".sbn"):
            source_file = os.path.join(source_path, translate_base_name)
            script_type = "sbn"
        else:
            print(f"{translate_file}: CSV file is not a SBXU or SBN translation sheet.")
            continue

        with open(
            os.path.join(translate_path, translate_file), encoding="utf-8"
        ) as file:
            strings = list(csv.reader(file, delimiter="|"))

        with open(source_file, "rb") as ascr_data:
            try:
                if script_type == "sbx":
                    new_ascr, new_warnings = write_ascr(
                        ascr_data, strings, add_header=False, filename=translate_file
                    )
                    # Add original header size of 8 to length of new ASCR data for
                    # uncompressed data size in PRS header.
                    output = prs.compress(
                        b"ASCR" + struct.pack("<I", len(new_ascr) + 8) + new_ascr
                    )
                elif script_type == "sbn":
                    output, new_warnings = write_ascr(
                        ascr_data, strings, filename=translate_file
                    )
            except ParsingError as e:
                print(f"Error: {e}")
                errors += 1
                continue

        warnings += new_warnings

        with open(os.path.join(output_path, translate_base_name), "wb") as file:
            file.write(output)
            print(
                f"{translate_base_name}: {len(output)} ({hex(len(output))}) bytes written."
            )

        files_written += 1

    if files_written > 0:
        print(f"\n{str(files_written)} file(s) written to {output_path}.")

        if warnings > 0:
            print(f"{str(warnings)} warning(s) raised. See output for details.")


if __name__ == "__main__":
    main()
