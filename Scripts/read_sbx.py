# Based on the scripts from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695 by ZetpeR xax007@yandex.ru.
#
# This script reads uncompressed SBX files with extension .SBX.bin, such as those output by the Decompress SBX script, 
# and SBN files in the 'source' subdirectory.
# It outputs CSV files in the 'translate' subdirectory, using pipe characters | as delimiters.
#
# Two CSV values are written for each file, one for the strings and one for the binary data.
# Rows for the strings contain: string offset, string type ("code" or "dialogue"), Shift-JIS text.
# Rows for binary data contain: four data values, data offset, subroutine name from strings, bytes.


import os
import sys
import struct
from utils import sbx

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path,"source")
translate_path = os.path.join(path, "translate")

def main():

    if not os.path.exists(translate_path):
        os.makedirs(translate_path)

    for file in os.listdir(source_path):

        # If first 4 bytes does not contain signature BA AF 55 CC, skip the file.
        with open(os.path.join(source_path,file),"rb") as f:

            # Read files in working directory. Uncompressed SBX files begin at 0; SBN files contain the ASCR header in the first 8 bytes and should be skipped.
            # if file.lower().endswith(('.sbx')):
                # input_data = sbx.decompress(f)
                # offset = 0
            if file.lower().endswith(('.sbx.bin')):
                # input_data = f.read()
                offset = 0
            elif file.lower().endswith(('.sbn')):
                # input_data = f.read()
                offset = 8
            else:
                continue
            
            f.seek(offset)
            signature = f.read(4)

            if signature != b'\xBA\xAF\x55\xCC':
                print("Not decompressed SBX or SBN:",file)
                continue

            string_location = struct.unpack("<I",f.read(4))[0] + offset   # Location of table of offsets for text area at the end of the file.
            string_length = struct.unpack("<I",f.read(4))[0]              # Number of strings in this file.
            binary_location = struct.unpack("<I",f.read(4))[0] + offset   # Location of table of offsets for binary data associated with subroutines.
            binary_length = struct.unpack("<I",f.read(4))[0]              # Number of entries in the binary data table.
            
            # The last set of strings are subroutines that correspond to the number of entries in the binary data table. 
            # Strings will be copied into this list and referenced during the writing of the binary data table CSV.
            strings = []                                                   
                                                                        
            # Read strings in this file.
            # First offset is equal to the location of the offset table added to the total length of the offsets in this table.
            string_data = []
            data_location = string_location + (string_length * 4)
            
            for i in range(string_length):
                f.seek(string_location + (i * 4)) # Seek to location of offset table.
                data_location = struct.unpack("<I",f.read(4))[0] + string_location

                # Retrieve text.
                f.seek(data_location)
                byte_string = bytearray()
                
                # Parse each string at the addresses in the 4-byte offset list. Script text is read as Shift_JIS-2004.
                # https://en.wikipedia.org/wiki/Shift_JIS#Shift_JISx0213_and_Shift_JIS-2004
                while True:
                    bytes = f.read(1)
                    if bytes == b'\x00': # Strings are null-terminated.
                        byte_string_decoded = byte_string.decode("shift_jis_2004")
                        if byte_string_decoded.isascii():
                            string_type = "code"
                        else:
                            string_type = "dialogue"
                        break
                    byte_string += bytes

                string_data.append([str(i) for i in [hex(data_location),string_type,byte_string_decoded]])
                strings.append(byte_string_decoded)

            with open(os.path.join(translate_path, file + ".csv"),"w", encoding="utf-8") as output_file:
                for i in string_data:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                    

            # Read the binary data table and output raw values in a separate CSV file.
            binary_data = []
            data_location = binary_location + (binary_length * 16)

            for i in range(binary_length):
                f.seek(binary_location + (i * 16))
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
                
                binary_data.append([str(i) for i in [data_index,data2,data3,data4,hex(data_location),strings[-(binary_length - i)],data_raw]])

                # As there is no offset table for the binary data, reset data_location for next chunk by using the end of the current chunk.
                data_location = f.tell()

            with open(os.path.join(translate_path, file + "_16.csv"),"w", encoding="utf-8") as output_file:
                for i in binary_data:
                    output = "|".join(i)
                    output_file.write(output + "\n")

        print(f"{file.split('.')[0]}: Text offset table location: {hex(string_location)}, entries: {string_length}. 16-byte table location: {hex(binary_location)}, entries: {binary_length}. Text start location: {string_data[0][0]}.")


if __name__ == "__main__":
    main()