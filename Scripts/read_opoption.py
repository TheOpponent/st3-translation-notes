# This script reads the files OpOption.bin, OpOptionSave.bin, and OpSelectVm.bin,
# located within the archive SYSLIST.AFS, in the 'source' subdirectory.
# It outputs CSV files in the 'translate' subdirectory using pipe characters | as delimiters. 
#
# Each row contains: string offset, string. The strings begin with a list of parameters in ASCII:
# !i!h=nnn!v=nnn!xnnn!y=nnn
# This is followed by the string in Shift-JIS, then !d!o, then byte 00.

import os
import sys
import re
from shutil import copyfile
from utils.utils import read_string

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path,"source")
translate_path = os.path.join(path, "translate")
backups_path = os.path.join(path,"backups")

def main():

    # List containing: file name, location of string table, number of strings.
    op_files = [
        ["OpOption.bin",0x25cd,41],
        ["OpOptionSave.bin",0x615f,127],
        ["OpSelectVm.bin",0x7cb3,11]
    ]

    if not os.path.exists(translate_path):
        os.makedirs(translate_path)

    for filename,string_table,strings in op_files:

        # If a CSV for the file already exists, do not process.
        if os.path.exists(os.path.join(translate_path, filename + ".csv")):
            print(f"{os.path.join(translate_path, filename + '.csv')} already exists; not overwriting.")
            continue

        try:
            with open(os.path.join(source_path,filename),"rb") as f:

                table_data = []

                # Read only the unique strings. 
                f.seek(string_table)
                for i in range(strings):
                    offset = hex(f.tell())
                    text = read_string(f)

                    # Wrap parameters in curly brackets.
                    text = re.split("(![!a-z0-9=+]+)([^!]*)",text)
                    new_text = ""
                    for i in text:
                        if i != "":
                            if i.startswith("!"):
                                new_text += "{" + i + "}"
                            else:
                                new_text += i
                                
                    table_data.append([offset,new_text])

                with open(os.path.join(translate_path, filename + ".csv"),"w", encoding="utf-8") as txt_output:
                    for i in table_data:
                        txt_output.write("|".join([i[0],i[1]]) + "\n")

                if not os.path.exists(os.path.join(backups_path, filename + "csv")):
                    copyfile(os.path.join(translate_path, filename + ".csv"),os.path.join(backups_path, filename + ".csv"))

            print(f"{filename}: Entries: {len(table_data)}.")

        except FileNotFoundError:
            print(f"{filename} not found in {source_path}.")


if __name__ == "__main__":
    main()