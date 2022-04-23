# This script reads a CSV file in the translate subdirectory and inserts the strings within into a LIPSYNC*.LIP with a corresponding filename in the source subdirectory.
# It outputs files in the 'output' subdirectory with extension .LIP.

import os
import sys
import csv
import struct
from utils import *

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path,"translate")
lip_path = os.path.join(path,"source")
output_path = os.path.join(path,"output")

def main():

    # Only process CSV files for which a LIP file with the same base name exists.
    for translate_file in os.listdir(translate_path):
        translate_base_name = os.path.splitext(translate_file)[0]
        if os.path.splitext(translate_file)[1] == ".csv" and os.path.isfile(lip_source := os.path.join(lip_path,translate_base_name)):
            with open(lip_source,"rb") as lip_file:

                # Check signature.
                if lip_file.read(4) != b'ALPD':
                    print(f"{lip_file}: Not LIP file.")
                    continue

                # Set address and limits.
                file_size = struct.unpack("<I",lip_file.read(4))[0]
                line_count = struct.unpack("<I",lip_file.read(4))[0]

                # Copy padding.
                lip_file.seek(file_size + 8)
                padding = lip_file.read()

                # Get offsets. Offsets are 8 bytes before actual data being pointed to.
                # lip_file.seek(12)
                # lip_properties = []
                # for i in range(line_count):
                #     lip_properties.append((struct.unpack("<I",lip_file.read(4))[0],struct.unpack("<I",lip_file.read(4))[0],struct.unpack("<I",lip_file.read(4))[0]))

                # if len(lip_properties) == 0:
                #     print(f"{lip_file}: No offsets found.")
                #     continue
                # current_offset = lip_properties[0][1]

                # Set current_offset to first offset in list.
                new_offsets = bytearray()
                new_strings = bytearray()

                # Assume first offset is located in second 4-byte value of first entry in offset table.
                lip_file.seek(16)
                current_offset = struct.unpack("<I",lip_file.read(4))[0]

                # Read CSV file.
                with open(os.path.join(translate_path,translate_file),encoding="utf-8") as file:
                    csv_file = csv.reader(file,delimiter="|")

                    for i in csv_file:
                        # Encode current string from csv. Terminate strings with byte 00.
                        voice_index = struct.pack("<I",int(i[0]))
                        new_offsets += voice_index

                        if i[2].isascii():
                            # Check if entire line consists of ASCII characters.
                            line_encoded = ascii_to_sjis(i[2],line_id=i[1])
                        else:
                            # Otherwise, assume string is unchanged Japanese text and encode as-is.
                            line_encoded = i[2].encode(encoding="shift_jis_2004") + b'\x00'
                        cmd_sequence = bytes.fromhex(i[4]) + b'\x00'

                        new_strings += line_encoded + cmd_sequence

                        # Increase next offset by the length of the string in bytes.
                        new_offsets += struct.pack("<I",current_offset)
                        current_offset += len(line_encoded)

                        new_offsets += struct.pack("<I",current_offset)
                        current_offset += len(cmd_sequence)

                # Output new offset table and strings.
                output_binary = bytearray()

                # Calculate new file size and repack line_count.
                while True:
                    new_strings += b'\x40'
                    if (len(new_offsets + new_strings) + 8) % 4 == 0:
                        new_length = struct.pack("<I",len(new_offsets + new_strings) + 4)
                        break

                output_binary += b'ALPD' + new_length + struct.pack("<I",line_count) + new_offsets + new_strings + padding

                with open(os.path.join(output_path,translate_base_name),"wb") as output_file:
                    output_file.write(output_binary)
                    print(f"{translate_base_name}: {len(output_binary)} ({hex(len(output_binary))}) bytes written.")


if __name__ == "__main__":
    main()
