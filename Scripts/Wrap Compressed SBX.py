# Provide a compressed SBX file with no header or footer as argument. The script will prompt for the uncompressed size in bytes.
# The output will add the correct header information and footer and append .final to the filename.

import sys
import struct

def main():

    with open(sys.argv[1],"rb") as file:
        buffer = file.read()
        raw_size = len(buffer)

        # Add at least one 00 byte as padding.
        while True:
            buffer += b'\x00'
            if len(buffer) % 4 == 0:
                buffer += b'CPRS\x00\x00\x00\x00'
                padded_size = len(buffer)
                buffer += b'EOFC\x00\x00\x00\x00'
                break

    uncompressed_size = int(input("Enter uncompressed size: "))

    output = b''.join([b'ASCR',struct.pack("<I",padded_size),struct.pack("<I",uncompressed_size),struct.pack("<I",raw_size),buffer])

    with open(sys.argv[1],"wb") as file:
        file.write(output)


if __name__ == "__main__":
    main()