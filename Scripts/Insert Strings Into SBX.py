# This script reads a TSV file in the tsv subdirectory and inserts the strings within into an uncompressed SBX script with a corresponding filename with extension .SBX.bin in the source subdirectory.
# It outputs files in the 'output' subdirectory with extension .SBX.final. Pass these output files to a PRS compressor.
# This assumes all string offsets are contiguous.
# The first line in a script extraction contains a blank string. The offset of this line is used as the starting point.

import os
import sys
import csv
import struct

path = os.path.realpath(os.path.dirname(sys.argv[0]))
tsv_path = os.path.join(path,"tsv")
sbx_path = os.path.join(path,"source")
output_path = os.path.join(path,"output")

def main():

    # Only process TSV files for which a SBX with the same base name exists.
    for tsv_file in os.listdir(tsv_path):
        if os.path.isfile(sbx_source := os.path.join(sbx_path,os.path.splitext(tsv_file)[0] + ".bin")):
            with open(sbx_source,"rb") as sbx_file:

                # Check signature.
                if sbx_file.read(4) != b'\xBA\xAF\x55\xCC':
                    print(f"{sbx_file}: Not uncompressed SBX file.")
                    continue

                # Set address and limits.
                offset_table_address = struct.unpack("<I",sbx_file.read(4))[0]
                line_count = struct.unpack("<I",sbx_file.read(4))[0]

                offsets = []
                sbx_file.seek(offset_table_address)
                # Get offsets.
                for i in range(line_count):
                    offsets.append(struct.unpack("<I",sbx_file.read(4))[0])

                if len(offsets) == 0:
                    print(f"{sbx_file}: No offsets found.")
                    continue

                # Set current_offset to first offset in list.
                # The first string is empty, which will cause the second offset to be 1 greater than the first.
                new_offsets = bytearray()
                new_strings = bytearray()
                current_offset = offsets[0]

                # Read TSV file.
                with open(os.path.join(tsv_path,tsv_file),encoding="utf-8") as file:
                    tsv = csv.reader(file,delimiter="\t")

                    for i in tsv:
                        # Encode current string from tsv. Terminate strings with byte 00.
                        line_encoded = i[1].encode(encoding="shift_jis_2004") + b'\x00'

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
            
                with open(os.path.join(output_path,os.path.splitext(tsv_file)[0] + ".out"),"wb") as file:
                    file.write(output_binary)
                    print(f"{os.path.splitext(tsv_file)[0]}: {len(output_binary)} ({hex(len(output_binary))}) bytes written. PRS data: {swap_bytes(len(output_binary))}")

        else:
            print(f"{tsv_file}: No matching uncompressed SBX file found.")
            continue


def swap_bytes(value):
    """Convert hex string to little-endian bytes."""

    str = hex(value)[2:].zfill(8)

    return str[6:8] + str[4:6] + str[2:4] + str[0:2]


if __name__ == "__main__":
    main()
