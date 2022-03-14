#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### Edited/translated from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695
### Original comments:
# ZetpeR xax007@yandex.ru
# Вынемание текста из распакованных скриптов .SBX.bin игры Sakura Taisen 3 PC
# В файле S1106.SBX строчка текста 81 40 90 EC FA B1 83 71 83 8D 83 86 83 4C не распаковывается кодировкой shift_jis остальные распаковываются
# При использование кодировки shift_jis_2004 различия только в файлах S1003.SBX и S1106.SBX

# This script reads uncompressed SBX files with extension .SBX.bin in the 'source' subdirectory, such as those output by the Decompress SBX script.
# It outputs tab-separated values (TSV) files in the 'tsv' subdirectory. These files contain the offset address in hex and text converted to UTF-8.

import os
import sys
import struct

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path,"source")

def main():
    if not os.path.exists(path + "tsv"):
        os.makedirs(path + "tsv")

    for mult_file in os.listdir(source_path):
        if mult_file.lower().endswith(('.sbx.bin')):
            Unpack(mult_file)


def Unpack(mult_file):
    # Read files in working directory. If first 4 bytes does not contain signature BA AF 55 CC, skip the file.
    with open(os.path.join(source_path,mult_file),"rb") as f:
        if f.read(4) != b'\xBA\xAF\x55\xCC':
            print("Not decompressed SBX:",mult_file)
            return

        table_4_location = struct.unpack("<I",f.read(4))[0]    # Location of table of offsets for text area at the end of the file. Each offset is a 4-byte address.
        table_4_length = struct.unpack("<I",f.read(4))[0]      # Number of lines in the 4-byte offset table, a 4-byte value.
        table_16_location = struct.unpack("<I",f.read(4))[0]   # Location of table of offsets, purpose currently unknown. Each offset is a 16-byte value.
        table_16_length = struct.unpack("<I",f.read(4))[0]     # Number of lines in the 16-byte offset table, a 4-byte value.

        # Read the 4-byte offset table and load the addresses into a list.
        table_4_data = []
        f.seek(table_4_location) # Seek to location of offset table.
        for i in range(table_4_length):
            offset_text = struct.unpack("<I",f.read(4))[0] + table_4_location
            table_4_data.append(offset_text)

        # Read the offset table and parse each string at the addresses in the list. Script text is read as Shift_JIS-2004.
        # https://en.wikipedia.org/wiki/Shift_JIS#Shift_JISx0213_and_Shift_JIS-2004
        with open(os.path.join(path, "tsv", mult_file[:-4] + ".tsv"),"w", encoding="utf-8") as txt_output:
            for i in table_4_data:
                f.seek(i)
                byte_string = b''
                while True:
                    bytes = f.read(1)
                    if bytes == b'\x00': # Strings are terminated with single byte 00.
                        txt_output.write(hex(i) + "\t" + byte_string.decode("shift_jis_2004") + "\n")
                        break
                    byte_string += bytes

        # TODO: Document and parse 16-byte offset table.

    print(f"{mult_file.split('.')[0]}: 4-byte table location: {hex(table_4_location)}, entries: {table_4_length}. 16-byte table location: {hex(table_16_location)}, entries: {table_16_length}. Dialogue start location: {hex(table_4_data[0])}.")


if __name__ == "__main__":
    main()