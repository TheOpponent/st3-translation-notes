# Based on the scripts from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695 by ZetpeR xax007@yandex.ru.
#
# This script reads compressed SBX files and uncompressed SBN files in the 'source' subdirectory.
# It outputs CSV files in the 'translate'and `subroutine` subdirectories, using pipe characters | as delimiters.
#
# Two CSV values are written for each file, one for the strings and one for the subroutine binary data.
# Rows for the strings contain: string offset, string type ("code" or "dialogue"), Shift-JIS text.
# Rows for subroutine data contain: four data values, data offset, subroutine name from strings, bytes.

import os
import sys
import struct
from io import BytesIO
from shutil import copyfile
from utils import prs
from utils.utils import read_string

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path,"source")
translate_path = os.path.join(path,"translate")
backups_path = os.path.join(path,"backups")
subroutines_path = os.path.join(path,"subroutines")

def main():

    files_written1 = 0
    backup_files_written = 0
    files_written2 = 0

    if not os.path.exists(source_path):
        os.makedirs(source_path)
        print(f"Place SBX and SBN script files in {source_path}.")
        return

    if not os.path.exists(translate_path):
        os.makedirs(translate_path)
    if not os.path.exists(backups_path):
        os.makedirs(backups_path)

    for file in os.listdir(source_path):

        with open(os.path.join(source_path,file),"rb") as f:

            # Read files in working directory. SBX files must be decompressed first.
            # After decompressing the SBX file, save it in the source subdirectory for later repacking.
            if file.lower().endswith(('.sbx')):
                input_data = prs.decompress(f.read())
                with open(os.path.join(source_path,os.path.splitext(file)[0]) + ".SBXU","wb") as uncompressed_file:
                    uncompressed_file.write(input_data)
                    print(f"Wrote uncompressed SBX file to {uncompressed_file.name}.")

                input_data = BytesIO(input_data)

            elif file.lower().endswith(('.sbn')):
                input_data = f
            else:
                continue
            
            # Skip header.
            input_data.seek(8)
            
            # If first 4 bytes after header does not contain signature BA AF 55 CC, skip the file.
            if input_data.read(4) != b'\xBA\xAF\x55\xCC':
                print("Header not recognized:",file)
                continue

            string_location = struct.unpack("<I",input_data.read(4))[0] + 8   # Location of table of offsets for text area at the end of the file.
            string_length = struct.unpack("<I",input_data.read(4))[0]         # Number of strings in this file.
            subroutines_location = struct.unpack("<I",input_data.read(4))[0] + 8   # Location of table of offsets for binary data associated with subroutines.
            subroutines_length = struct.unpack("<I",input_data.read(4))[0]         # Number of entries in the binary data table.
            
            # The last set of strings are subroutines that correspond to the number of entries in the binary data table. 
            # Strings will be copied into this list and referenced during the writing of the binary data table CSV.
            strings = []                                                   
                                                                        
            # Read strings in this file.
            # First offset is equal to the location of the offset table added to the total length of the offsets in this table.
            string_data = []
            data_location = string_location + (string_length * 4)
            
            for i in range(string_length):
                input_data.seek(string_location + (i * 4)) # Seek to location of offset table.
                data_location = struct.unpack("<I",input_data.read(4))[0] + string_location

                # Retrieve text.
                input_data.seek(data_location)
                text = read_string(input_data)
                if text.isascii():
                    string_type = "code"
                else:
                    string_type = "dialogue"

                string_data.append([str(i) for i in [hex(data_location),string_type,text]])
                strings.append(text)

            with open(os.path.join(translate_path, file + ".csv"),"w", encoding="utf-8") as output_file:
                for i in string_data:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                files_written1 += 1

            # Create backup copies of the script CSV files, but do not overwrite existing copies.
            if not os.path.exists(os.path.join(backups_path, file + ".csv")):
                copyfile(os.path.join(translate_path, file + ".csv"),os.path.join(backups_path, file + ".csv"))
                backup_files_written += 1
                    
            # Read the binary data table and output raw values in a separate CSV file.
            subroutines_data = []
            data_location = subroutines_location + (subroutines_length * 16)

            for i in range(subroutines_length):
                input_data.seek(subroutines_location + (i * 16))
                data_index = struct.unpack("<I",input_data.read(4))[0] # Data index.
                data2 = struct.unpack("<I",input_data.read(4))[0] # Data value 2, purpose currently unknown.
                data3 = struct.unpack("<I",input_data.read(4))[0] # Data value 3, purpose currently unknown.
                data4 = struct.unpack("<I",input_data.read(4))[0] # Data value 4, purpose currently unknown.
                
                # Retrieve data.
                input_data.seek(data_location)
                byte_string = bytearray()
                while True:
                    # Read 4 bytes at a time. If the last 2 bytes are 40 40, continue with the next data chunk.
                    bytes = input_data.read(4)
                    byte_string += bytes
                    if bytes[2:] == b'\x40\x40':
                        data_raw = byte_string.hex(" ")
                        break
                
                subroutines_data.append([str(i) for i in [data_index,data2,data3,data4,hex(data_location),strings[-(subroutines_length - i)],data_raw]])

                # As there is no offset table for the binary data, reset data_location for next chunk by using the end of the current chunk.
                data_location = input_data.tell()

            with open(os.path.join(translate_path, file + "_16.csv"),"w", encoding="utf-8") as output_file:
                for i in subroutines_data:
                    output = "|".join(i)
                    output_file.write(output + "\n")
                files_written2 += 1

            input_data.close()

        print(f"{file}: Text offset table location: {hex(string_location)}, entries: {string_length}. Subroutine table location: {hex(subroutines_location)}, entries: {subroutines_length}. Text start location: {string_data[0][0]}.")

    if files_written1 > 0:
        print(f"\n{files_written1} CSV file(s) written to {translate_path}.")
    
    else:
        print(f"No SBX or SBN files found in {source_path}.")
        return

    if backup_files_written > 0:
        print(f"\n{files_written1} CSV file(s) written to {backups_path}.")

    if files_written2 > 0:
        print(f"{files_written2} CSV file(s) written to {subroutines_path}.")


if __name__ == "__main__":
    main()