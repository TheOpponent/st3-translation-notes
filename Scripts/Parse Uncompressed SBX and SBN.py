# This script reads uncompressed SBX files with extension .SBX.bin, such as those output by the Decompress SBX script, and SBN files in the 'source' subdirectory.
# It outputs CSV files in the 'translate' subdirectory, using pipe characters | as delimiters. These files contain the offset address in hex and text converted to UTF-8.

### Based on the scripts from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695
### Original comments:
# ZetpeR xax007@yandex.ru
# Вынемание текста из распакованных скриптов .SBX.bin игры Sakura Taisen 3 PC
# В файле S1106.SBX строчка текста 81 40 90 EC FA B1 83 71 83 8D 83 86 83 4C не распаковывается кодировкой shift_jis остальные распаковываются
# При использование кодировки shift_jis_2004 различия только в файлах S1003.SBX и S1106.SBX

import os
import sys
import struct
from utils import swap_bytes

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path,"source")
translate_path = os.path.join(path, "translate")

def main():

    if not os.path.exists(translate_path):
        os.makedirs(translate_path)

    for file in os.listdir(source_path):
        # Read files in working directory. Uncompressed SBX files begin at 0; SBN files contain the ASCR header in the first 8 bytes and should be skipped.
        if file.lower().endswith(('.sbx.bin')):
            offset = 0
        elif file.lower().endswith(('.sbn')):
            offset = 8
        else:
            continue

        # If first 4 bytes does not contain signature BA AF 55 CC, skip the file.
        with open(os.path.join(source_path,file),"rb") as f:
            f.seek(offset)
            signature = f.read(4)
            if signature != b'\xBA\xAF\x55\xCC':
                print("Not decompressed SBX or SBN:",file)
                continue

            table_4_location = struct.unpack("<I",f.read(4))[0] + offset   # Location of table of offsets for text area at the end of the file.
            table_4_length = struct.unpack("<I",f.read(4))[0]              # Number of lines in the 4-byte offset table.
            table_16_location = struct.unpack("<I",f.read(4))[0] + offset  # Location of table of offsets for data associated with subroutines.
            table_16_length = struct.unpack("<I",f.read(4))[0]             # Number of lines in the 16-byte offset table.

            # Read the 4-byte offset table and load the addresses into a list.
            table_4_data = []
            f.seek(table_4_location) # Seek to location of offset table.
            for i in range(table_4_length):
                offset_text = struct.unpack("<I",f.read(4))[0] + table_4_location # Read data at offset.
                table_4_data.append(offset_text)

            # Parse each string at the addresses in the 4-byte offset list. Script text is read as Shift_JIS-2004.
            # https://en.wikipedia.org/wiki/Shift_JIS#Shift_JISx0213_and_Shift_JIS-2004
            with open(os.path.join(translate_path, file + ".csv"),"w", encoding="utf-8") as txt_output:
                for i in table_4_data:
                    f.seek(i)
                    byte_string = bytearray()
                    while True:
                        bytes = f.read(1)
                        if bytes == b'\x00': # Strings are null-terminated.
                            byte_string_decoded = byte_string.decode("shift_jis_2004")
                            if byte_string_decoded.isascii():
                                string_type = "code"
                            else:
                                string_type = "dialogue"
                            txt_output.write(f"{hex(i)}|{string_type}|{byte_string_decoded}\n")
                            break
                        byte_string += bytes

            # Read the 16-byte table and output raw values in a separate CSV file.
            table_16_data = []
            data_location = table_16_location + (table_16_length * 16)
            for i in range(table_16_length):
                f.seek(table_16_location + (i * 16))
                data_index = struct.unpack("<I",f.read(4))[0] # Data index.
                data2 = struct.unpack("<I",f.read(4))[0] # Data value 2, purpose currently unknown.
                data3 = struct.unpack("<I",f.read(4))[0] # Data value 3, purpose currently unknown.
                data4 = struct.unpack("<I",f.read(4))[0] # Data value 4, purpose currently unknown.
                
                # Retrieve data.
                f.seek(data_location)
                byte_string = bytearray()
                while True:
                    # Read 4 bytes at a time. If the last 2 bytes are 40 40, continue with the next data chunk.
                    bytes = f.read(4)
                    byte_string += bytes
                    if bytes[2:] == b'\x40\x40':
                        data_raw = byte_string.hex(" ")
                        break

                table_16_data.append([str(i) for i in [data_index,data2,data3,data4,hex(data_location),data_raw]])

                # Reset data_location for next chunk.
                data_location = f.tell()

            with open(os.path.join(translate_path, file + "_16.csv"),"w", encoding="utf-8") as txt_output:
                for i in table_16_data:
                    output = "|".join(i)
                    txt_output.write(output + "\n")

        print(f"{file.split('.')[0]}: 4-byte table location: {hex(table_4_location)}, entries: {table_4_length}. 16-byte table location: {hex(table_16_location)}, entries: {table_16_length}. Dialogue start location: {hex(table_4_data[0])}.")


if __name__ == "__main__":
    main()