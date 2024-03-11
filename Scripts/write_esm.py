import csv
import os
import re
import struct
import sys

from utils.utils import ascii_to_sjis

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path,"translate")
source_path = os.path.join(path,"source")
output_path = os.path.join(path,"output")

def main():

    os.makedirs(output_path, exist_ok=True)

    with open(os.path.join(source_path,"ESM.bin"),"rb") as esm_file:

        # Check signature.
        header = esm_file.read(4)
        if header != b'CTPA':
            print(f"{repr(esm_file)}: Not ESM strings data.")
            return

        # Set address and limits.
        esm_file.seek(8)
    
        string_length = esm_file.read(4)
        string_location = struct.unpack("<I",esm_file.read(4))[0]        # Location of table of offsets for text area at the end of the file, + 8.
        binary_length = esm_file.read(4)                             
        binary_location = struct.unpack("<I",esm_file.read(4))[0]        # Location of table of offsets for binary data associated with subroutines, + 8.
        value3 = esm_file.read(4)
        value4 = esm_file.read(4)

        new_offsets = bytearray()
        new_strings = bytearray()

        # Seek to first string offset.
        esm_file.seek(string_location + 8)
        current_offset = struct.unpack("<I",esm_file.read(4))[0]

        # Read CSV file.
        with open(os.path.join(translate_path,"ESM.bin.csv"),encoding="utf-8") as file:
            csv_file = csv.reader(file,delimiter="|")

            for i in csv_file:
                if re.fullmatch(r'[A-zÀ-ÿ0-9œ`~!@#$%^&*(){}_|+\-×÷=?;:<>°\'",.\[\]/—–‘’“”☆★ ]+',i[1],re.I):
                    # Only translate strings that contain only non-Japanese characters.
                    line_encoded = ascii_to_sjis(i[1],line_id=i[0])
                else:
                    # Otherwise, assume string is unchanged Japanese text and encode as-is.
                    line_encoded = i[1].encode(encoding="shift_jis_2004") + b'\x00'

                # Pad to 4-byte alignment.
                while len(line_encoded) % 4 != 0:
                    line_encoded += b'\x00'

                new_strings += line_encoded
                new_offsets += struct.pack("<I",current_offset) 
                # Increase next offset by the length of the string in bytes.
                current_offset += len(line_encoded)

        # Output new offset table and strings.
        output_binary = bytearray()

        # Read remaining data.
        esm_file.seek(binary_location + 8)
        output_binary = new_offsets + new_strings + esm_file.read()
        binary_location = 32 + len(new_offsets) + len(new_strings)

        # Reconstruct header.
        output_header = b'CTPA' + struct.pack("<I", len(output_binary) + 24) + string_length + struct.pack("<I",string_location) + binary_length + struct.pack("<I",binary_location - 8) + value3 + value4

        with open(os.path.join(output_path,"ESM.bin.out"),"wb") as file:
            file.write(output_header + output_binary)
            print(f"ESM.bin: {len(output_binary)} ({hex(len(output_binary))}) bytes written.")
            

if __name__ == "__main__":
    main()
