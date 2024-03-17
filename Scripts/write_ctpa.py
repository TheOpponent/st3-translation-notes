# Given a source CTPA data chunk, create a new chunk from a list of strings.
# Offsets are recalculated, and all other data is retained.

import csv
import re
import os
import struct
import sys

from utils.ascr import ascii_to_sjis, ASCRError

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path, "translate", "ctpa")
ctpa_path = os.path.join(path, "source", "ctpa")
output_path = os.path.join(path, "output", "ctpa")

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
        file_list = [i for i in os.listdir(translate_path)]

    for translate_file in file_list:
        translate_base_name = os.path.splitext(os.path.basename(translate_file))[0]
        os.makedirs(output_path, exist_ok=True)

        if len(sys.argv) > 1:
            source_file = os.path.join(
                ctpa_path, os.path.basename(translate_base_name)
            )
        else:
            source_file = os.path.join(
                ctpa_path, translate_base_name
            )
        if not os.path.exists(source_file):
            print(
                f"[Error] {translate_file}: Source file not found in {ctpa_path}."
            )
            errors += 1
            continue
        with open(
            os.path.join(translate_path, translate_file),
            encoding="utf-8",
        ) as file:
            strings = list(csv.reader(file, delimiter="|"))

        with open(source_file, "rb") as ctpa_data:
            header = ctpa_data.read(32)
            if header[0:4] != b"CTPA":
                raise ASCRError("Not a CTPA chunk.")
            
            offset_table_address = struct.unpack("<I",header[12:16])[0] + 8
            second_table_address = struct.unpack("<I",header[20:24])[0] + 8
            ctpa_data.seek(second_table_address)
            second_table = ctpa_data.read()
            
            new_offsets = bytearray()
            new_strings = bytearray()

            ctpa_data.seek(offset_table_address)
            current_offset = struct.unpack("<I", ctpa_data.read(4))[0] + 8

            for i in enumerate(strings):
                try:
                    offset, new_text = i[1]
                except ValueError as e:
                    ctpa_data.close()
                    raise ASCRError(f"Error parsing line {i[0]}: {e}")
                
                if current_offset == 0:
                    new_offsets += b"\x00\x00\x00\x00"
                    continue
                else:
                    current_offset

                if re.fullmatch(
                    r'[A-zÀ-ÿ0-9œ`~!@#$%^&*(){}_|+\-×÷=?;:<>°\'",.\[\]/—–‘’“”☆★ ]+',
                    new_text,
                    re.I,
                ):
                    # Only translate strings that contain only non-Japanese characters.
                    line_encoded, warning = ascii_to_sjis(
                        new_text, line_id=i[0], filename=translate_file
                    )
                    warnings += warning
                else:
                    line_encoded = new_text.encode(encoding="shift_jis")
                    line_encoded += b"\x00"

                if (padding := len(line_encoded) % 4) != 0:
                    line_encoded += b"\x00" * (4 - padding)

                new_strings += line_encoded
                new_offsets += struct.pack("<I", current_offset - 8)
                current_offset += len(line_encoded)

            new_data = bytearray()
            new_second_table_location = struct.pack("<I",len(new_strings) + len(new_offsets) + 24)
            new_data.extend(header[8:20])
            new_data.extend(new_second_table_location)
            new_data.extend(header[24:])
            new_data.extend(new_offsets)
            new_data.extend(new_strings)
            new_data.extend(second_table)

            output = bytearray(b"CTPA")
            output.extend(struct.pack("<I",len(new_data)))
            output.extend(new_data)

        with open(
            os.path.join(output_path, translate_base_name),
            "wb",
        ) as file:
            file.write(output)
            print(
                f"{translate_base_name}: {len(new_data)} ({hex(len(new_data))}) bytes written."
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