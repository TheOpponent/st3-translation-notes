# This script reads OpOption.bin.csv translate subdirectory and merges the new strings into OpOption.bin in the source directory.
# It assumes all strings are fully ASCII.
# Output is written into OpOption.bin in the output directory.

import os
import sys
import csv
import struct
from utils.utils import ascii_to_sjis

path = os.path.realpath(os.path.dirname(sys.argv[0]))
source_path = os.path.join(path,"source")
translate_path = os.path.join(path,"translate")
output_path = os.path.join(path,"output")

def main():

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    try:
        with open(os.path.join(source_path,"OpOption.bin"),"rb") as bin_file:

            try:
                with open(os.path.join(translate_path, "OpOption.bin.csv"), encoding="utf-8") as file:
                    csv_file = csv.reader(file,delimiter="|")

                    new_offsets = bytearray()
                    new_strings = bytearray()

                    # First index and offset is at 0x23B0.
                    bin_file.seek(9136)

                    # Create a dict of indexes and offsets. There are 51 indexes and 40 unique offsets,
                    # and all instances of a given offset must be changed to the same value.
                    indexes = []
                    offsets = []
                    for i in range(51):
                        indexes.append(struct.unpack("<I",bin_file.read(4))[0])
                        offsets.append(struct.unpack("<I",bin_file.read(4))[0])

                    old_data = {k:v for (k,v) in zip(indexes,offsets)}

                    # Updated offsets will replace original offsets in the offset table.
                    original_offsets = []
                    new_offsets = []
                    current_offset = offsets[0]
                    for i in csv_file:

                        # Get original offsets.
                        original_offsets.append(int(i[0],0))

                        # Encode current string from csv.
                        line_encoded = ascii_to_sjis(i[1],break_lines=False)[0]

                        new_strings += line_encoded
                        new_offsets.append(current_offset)

                        # Increase next offset by the length of the string in bytes.
                        current_offset += len(line_encoded)

                # Replace original offsets with recalculated offsets.
                recalc_data = {k:v for (k,v) in zip(original_offsets,new_offsets)}
                new_data = {k:recalc_data.get(v,v) for (k,v) in old_data.items()}

                # Encode finalized index and offset pairs.
                final_data = bytearray()
                for (index,offset) in new_data.items():
                    final_data += struct.pack("<I",index)
                    final_data += struct.pack("<I",offset)

                # Write file, copying parts of the original file that will not be edited.                
                bin_file.seek(0)
                output_binary = bin_file.read(9136)
                output_binary += final_data
                bin_file.seek(9544)
                output_binary += bin_file.read(133)
                output_binary += new_strings

                with open(os.path.join(output_path,"OpOption.bin"),"wb") as file:
                    file.write(output_binary)
                    print(f"OpOption.bin: {len(output_binary)} ({hex(len(output_binary))}) bytes written.")

            except FileNotFoundError:
                print("OpOption.bin.csv not found in translate directory.")

    except FileNotFoundError:
        print("OpOption.bin not found in source directory.")


if __name__ == "__main__":
    main()
