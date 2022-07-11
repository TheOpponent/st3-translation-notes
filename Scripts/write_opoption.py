# This script reads OpOption.bin.csv, OpOptionSave.bin.csv, and OpSelectVm.bin.csv in the translate subdirectory 
# and merges the new strings into the respective files in the source directory.
# It assumes all strings are fully ASCII.
# Output is written into the output directory.

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

    # List containing: file name, location of offset table, number of bytes between offset table and string table, number of indexes.
    op_files = [
        ["OpOption.bin",0x23b0,133,51],
        ["OpOptionSave.bin",0x5c4c,155,133],
        ["OpSelectVm.bin",0x7b30,299,11]
    ]

    for filename,offset_table,other_bytes,index_count in op_files:
        try:
            with open(os.path.join(source_path,filename),"rb") as bin_file:
                try:
                    with open(os.path.join(translate_path, filename + ".csv"), encoding="utf-8") as file:
                        csv_file = csv.reader(file,delimiter="|")

                        new_offsets = bytearray()
                        new_strings = bytearray()

                        # Seek to irst index and offset.
                        bin_file.seek(offset_table)

                        # Create a dict of indexes and offsets. There may be more indexes than unique offsets,
                        # and all instances of a given offset must be changed to the same value.
                        indexes = []
                        offsets = []
                        for i in range(index_count):
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
                    output_binary = bin_file.read(offset_table)
                    output_binary += final_data
                    bin_file.seek(offset_table + len(final_data))
                    output_binary += bin_file.read(other_bytes)
                    output_binary += new_strings

                    with open(os.path.join(output_path,filename),"wb") as output_file:
                        output_file.write(output_binary)
                        print(f"{filename}: {len(output_binary)} ({hex(len(output_binary))}) bytes written.")

                except FileNotFoundError:
                    print(f"{filename}.csv not found in translate directory.")

        except FileNotFoundError:
            print(f"{filename} not found in source directory.")


if __name__ == "__main__":
    main()
