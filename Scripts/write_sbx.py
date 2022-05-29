# This script reads a CSV file in the translate subdirectory and inserts the strings within into an uncompressed SBX or SBN script 
# with a corresponding filename with extension .SBX.bin or .SBN in the source subdirectory.
# It outputs files in the 'output' subdirectory with the corresponding extension. Pass SBX output files to a PRS compressor.
# This assumes all string offsets are contiguous.
# The first line in a script extraction contains a blank string. The offset of this line is used as the starting point.

import csv
import os
import re
import struct
import sys

from utils.utils import ascii_to_sjis, swap_bytes

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path,"translate")
sbx_path = os.path.join(path,"source")
output_path = os.path.join(path,"output")

def main():

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Only process CSV files for which a SBX with the same base name exists.
    for translate_file in os.listdir(translate_path):
        translate_base_name = os.path.splitext(translate_file)[0]
        if os.path.splitext(translate_file)[1] == ".csv" and os.path.isfile(sbx_source := os.path.join(sbx_path,translate_base_name)):
            with open(sbx_source,"rb") as sbx_file:

                # Check signature. If the first 4 bytes or first 4 bytes after an 8-byte header contain a valid BA AF 55 CC signature, set the offset accordingly.
                header = sbx_file.read(12)
                if header[0:4] == b'\xBA\xAF\x55\xCC':
                    offset = 0
                    file_type = "sbx"
                elif header[0:4] == b'ASCR' and header[8:12] == b'\xBA\xAF\x55\xCC':
                    offset = 8
                    file_type = "sbn"
                else:
                    print(f"{repr(sbx_file)}: Not uncompressed SBX or SBN file.")
                    continue

                # Set address and limits.
                sbx_file.seek(offset + 4)
                offset_table_address = struct.unpack("<I",sbx_file.read(4))[0] + offset
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
                        if i[1] != "code" and re.fullmatch(r'[A-zÀ-ÿ0-9œ`~!@#$%^&*()_|+\-×÷=?;:<>°\'",.<>\[\]/—–‘’“”☆★ ]+',i[2],re.I):
                            # Only translate strings that are not type "code" and contain only non-Japanese characters.
                            line_encoded = ascii_to_sjis(i[2],line_id=i[0])
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
                sbx_file.seek(offset)
                output_binary = sbx_file.read(offset_table_address - offset) + new_offsets + new_strings

                while True:
                    output_binary += b'\x40'
                    if len(output_binary) % 4 == 0:
                        break

                if file_type == "sbn":
                    # SBN files require a header containing the data area size and the EOFC footer.
                    output_header = b'ASCR' + struct.pack("<I", len(output_binary))
                    output_footer = b'EOFC\x00\x00\x00\x00'
                else:
                    # SBX files will be compressed later and have that information added after PRS compression.
                    output_header = b''
                    output_footer = b''

                with open(os.path.join(output_path,translate_base_name + ".out"),"wb") as file:
                    file.write(output_header + output_binary + output_footer)
                    print(f"{translate_base_name}: {len(output_binary)} ({hex(len(output_binary))}) bytes written. PRS data: {swap_bytes(len(output_binary))}")

        else:
            print(f"{translate_file}: No matching uncompressed SBX or SBN file found.")
            continue


if __name__ == "__main__":
    main()
