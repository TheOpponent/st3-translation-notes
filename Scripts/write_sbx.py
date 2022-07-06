# This script reads a CSV file in the translate subdirectory and inserts the strings 
# within into an SBXU or SBN file with a corresponding filename in the source subdirectory.
# It outputs files in the 'output' subdirectory with the corresponding extension.
# This assumes all string offsets are contiguous.
#
# The first line in a CSV file contains a blank string. 
# The offset of this line is used as the starting point.

import csv
import os
import re
import struct
import sys
from utils import prs
from utils.utils import ascii_to_sjis

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path,"translate")
sbx_path = os.path.join(path,"source")
output_path = os.path.join(path,"output")

def main():

    files_written = 0
    warnings = 0

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    if len(sys.argv) > 1:
        file_list = []
        for i in sys.argv[1:]:
            file_list.append((i + ".csv" if not i.endswith(".csv") else i))

    else:
        file_list = os.listdir(translate_path)

    # Only process CSV files for which a SBX with the same base name exists.
    for translate_file in file_list:
        translate_base_name = os.path.splitext(translate_file)[0]
        if os.path.splitext(translate_file)[1] == ".csv" and os.path.exists(sbx_source := os.path.join(sbx_path,translate_base_name)):

            # If source is SBX, change sbx_source to SBXU file.
            if sbx_source.lower().endswith(".sbx"):
                sbx_source = os.path.splitext(sbx_source)[0] + ".SBXU"

            with open(sbx_source,"rb") as sbx_file:

                # Check signature and set file_type.
                header = sbx_file.read(16)
                if header[0:4] == b'ASCR' and header[8:12] == b'\xBA\xAF\x55\xCC':
                    file_type = os.path.splitext(sbx_source)[1]
                else:
                    print(f"Not SBX or SBN file: {repr(sbx_file.name)}")
                    continue

                # Set address and limits.
                sbx_file.seek(12)
                offset_table_address = struct.unpack("<I",sbx_file.read(4))[0] + 8
                # line_count = struct.unpack("<I",sbx_file.read(4))[0]

                # The first string is empty, which will cause the second offset to be 1 greater than the first.
                new_offsets = bytearray()
                new_strings = bytearray()

                # Assume first offset is located in second 4-byte value of first entry in offset table.
                # Skip next 4 bytes, which is the line count.
                sbx_file.seek(offset_table_address + 4)
                current_offset = struct.unpack("<I",sbx_file.read(4))[0]

                # Read CSV file.
                with open(os.path.join(translate_path,translate_file),encoding="utf-8") as file:
                    csv_file = csv.reader(file,delimiter="|")

                    for i in csv_file:
                        if i[1] != "code" and re.fullmatch(r'[A-zÀ-ÿ0-9œ`~!@#$%^&*(){}_|+\-×÷=?;:<>°\'",.\[\]/—–‘’“”☆★ ]+',i[2],re.I):
                            # Only translate strings that are not type "code" and contain only non-Japanese characters.
                            # ascii_to_sjis will pass warning counts, which will be reported at the end of this script's execution.
                            line_encoded, warning = ascii_to_sjis(i[2],line_id=i[0],filename=translate_file)
                            warnings += warning
                        else:
                            # Otherwise, assume string is unchanged Japanese text or a subroutine name and encode as-is.
                            line_encoded = i[2].encode(encoding="shift_jis_2004") + b'\x00'

                        new_strings += line_encoded
                        # Subtract 1 from current_offset to compensate for first empty string.
                        new_offsets += struct.pack("<I",current_offset - 1) 

                        # Increase next offset by the length of the string in bytes.
                        current_offset += len(line_encoded)

                # Output new offset table and strings.
                output_binary = bytearray()

                # Copy data preceding offset table location.
                sbx_file.seek(8)
                output_binary = sbx_file.read(offset_table_address - 8) + new_offsets + new_strings

                while True:
                    output_binary += b'\x40'
                    if len(output_binary) % 4 == 0:
                        break

                # Recompress SBXU files.
                if file_type.lower() == ".sbxu":
                    output_header = b''
                    output_binary = prs.compress(b'ASCR' + struct.pack("<I", len(output_binary)) + output_binary)
                else:
                    output_header = b'ASCR' + struct.pack("<I", len(output_binary))

                with open(os.path.join(output_path,translate_base_name),"wb") as file:
                    file.write(output_header + output_binary + b'EOFC\x00\x00\x00\x00')
                    print(f"{translate_base_name}: {len(output_binary)} ({hex(len(output_binary))}) bytes written.")

                files_written += 1

        else:
            print(f"{translate_file}: No matching SBXU or SBN file found.")
            continue

    if files_written > 0:
        print(f"\n{str(files_written)} file(s) written to {output_path}.")

        if warnings > 0:
            print(f"{str(warnings)} warning(s) raised. See output for details.")


if __name__ == "__main__":
    main()
