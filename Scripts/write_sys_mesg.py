# This script reads the CSV file created by read_sys_mesg.py and relocates
# the addresses to a different location, 0x200 bytes apart.
#
# The original table of addresses contain some duplicate entries.
# The output file, sys_mesg_new.bin, contains these new addresses.
# Replace the table in 1ST_READ.BIN starting at 0x21f7dc with the 
# contents of this file.

import struct

ENTRIES_COUNT = 148
STRINGS_COUNT = 134
BASE_OFFSET = 0x8c22f7dc
STARTING_OFFSET = 0x8cd90000

entries = {}
strings = {}
location = 0
text = ""

with open("sys_mesg.bin.csv","r",encoding="utf-8") as input_file:
    for i in range(0,ENTRIES_COUNT):
        entry = input_file.readline().split('|')
        entries[int(entry[0])] = int(entry[1],base=0)

    # Skip separator line.
    input_file.readline()

    for i in range(0,STRINGS_COUNT):
        string = input_file.readline().split('|')
        strings[int(string[0],base=0)] = string[1][0:-1]

new_addresses = {}

index = 0
for i in strings.keys():
    # Change every unique value into a new offset starting from STARTING_OFFSET.
    new_address = STARTING_OFFSET + (index * 0x200)
    new_addresses[i] = new_address
    index += 1

old_addresses = new_addresses.keys()

for i in entries:
    if entries[i] in old_addresses:
        entries[i] = new_addresses[entries[i]]

with open("sys_mesg_new.csv","w",encoding="utf-8") as output_file:
    for k,v in entries.items():
        output_file.write("|".join([str(k),hex(v)]) + "\n")

with open("sys_mesg_new.bin","wb") as output_file:
    for k,v in entries.items():
        output_file.write(struct.pack("<I",k))
        output_file.write(struct.pack("<I",v))