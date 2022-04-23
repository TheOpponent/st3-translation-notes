# This script reads a CSV file in the translate subdirectory and inserts the strings within into an uncompressed SBX script with a corresponding filename with extension .SBX.bin in the source subdirectory.
# It outputs files in the 'output' subdirectory with extension .SBX. Pass these output files to a PRS compressor.
# This assumes all string offsets are contiguous.
# The first line in a script extraction contains a blank string. The offset of this line is used as the starting point.

import os
import sys
import csv
import struct
from utils import *

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
        if os.path.splitext(translate_file)[1] == ".csv" and os.path.isfile(sbx_source := os.path.join(sbx_path,translate_base_name + ".bin")):
            with open(sbx_source,"rb") as sbx_file:

                # Check signature.
                if sbx_file.read(4) != b'\xBA\xAF\x55\xCC':
                    print(f"{sbx_file}: Not uncompressed SBX file.")
                    continue

                # Set address and limits.
                offset_table_address = struct.unpack("<I",sbx_file.read(4))[0]
                line_count = struct.unpack("<I",sbx_file.read(4))[0]

                # Get offsets.
                # offsets = []
                # sbx_file.seek(offset_table_address)
                # for i in range(line_count):
                #     offsets.append(struct.unpack("<I",sbx_file.read(4))[0])

                # if len(offsets) == 0:
                #     print(f"{sbx_file}: No offsets found.")
                #     continue

                # current_offset = offsets[0]

                # The first string is empty, which will cause the second offset to be 1 greater than the first.
                new_offsets = bytearray()
                new_strings = bytearray()

                # Assume first offset is located in second 4-byte value of first entry in offset table.
                sbx_file.seek(offset_table_address)
                current_offset = struct.unpack("<I",sbx_file.read(4))[0]
                
                # Read CSV file.
                with open(os.path.join(translate_path,translate_file),encoding="utf-8") as file:
                    csv_file = csv.reader(file,delimiter="|")

                    for i in csv_file:
                        if i[1] != "code" and i[2].isascii():
                            # Only translate strings that are not type "code" and contain only ASCII characters.
                            line_encoded = ascii_to_sjis(i[2],line_id=i[0])
                        else:
                            # Otherwise, assume string is unchanged Japanese text or a subroutine name and encode as-is.
                            line_encoded = i[2].encode(encoding="shift_jis_2004") + b'\x00'

                        new_strings += line_encoded
                        new_offsets += struct.pack("<I",current_offset)

                        # Increase next offset by the length of the string in bytes.
                        current_offset += len(line_encoded)

                # Output new offset table and strings.
                output_binary = bytearray()

                # Copy data preceding offset table location.
                sbx_file.seek(0)
                output_binary = sbx_file.read(offset_table_address) + new_offsets + new_strings

                while True:
                    output_binary += b'\x40'
                    if len(output_binary) % 4 == 0:
                        break
            
                with open(os.path.join(output_path,translate_base_name + ".out"),"wb") as file:
                    file.write(output_binary)
                    print(f"{translate_base_name}: {len(output_binary)} ({hex(len(output_binary))}) bytes written. PRS data: {swap_bytes(len(output_binary))}")

        else:
            print(f"{translate_file}: No matching uncompressed SBX file found.")
            continue


if __name__ == "__main__":
    main()
