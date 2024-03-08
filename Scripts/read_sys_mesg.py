# Copy the data from 1ST_READ.BIN from 0x21f7dc-0x223d09 into a new file
# named sys_mesg.bin and place it in the working directory.
#
# This script will read that file and output a CSV file containing the
# addresses of system messages, followed by the strings for the messages
# themselves.

import struct

from utils.utils import read_string

ENTRIES_COUNT = 148
STRINGS_COUNT = 134
BASE_OFFSET = 0x8C22F7DC

entries = []
strings = {}
location = 0
text = ""

# TODO: Read 1ST_READ.BIN directly instead.
with open("sys_mesg.bin", "rb") as file:
    for i in range(0, ENTRIES_COUNT):
        entries.append(
            (struct.unpack("<I", file.read(4))[0], struct.unpack("<I", file.read(4))[0])
        )

    # Seek to start of strings block.
    file.seek(1295)

    # Read strings.
    for i in range(0, STRINGS_COUNT):
        byte_string = b""
        location = file.tell()

        strings[location] = read_string(file)

with open("sys_mesg.bin.csv", "w", encoding="utf-8") as output_file:
    for i in entries:
        output_file.write("|".join([str(i[0]), hex(i[1])]) + "\n")

    output_file.write("-----\n")

    for k, v in strings.items():
        output_file.write("|".join([hex(k + BASE_OFFSET), v]) + "\n")
