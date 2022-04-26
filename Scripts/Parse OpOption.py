# This script reads the OpOption.bin file, located within the archive SYSLIST.AFS, in the 'source' subdirectory.
# It outputs a CSV file in the 'translate' subdirectory using pipe characters | as the delimiter. 
# Each row contains: string offset, string. The strings begin with a list of parameters in ASCII:
# !i!h=nnn!v=nnn!xnnn!y=nnn
# This is followed by the string in Shift-JIS, then !d!o, then byte 00.

import os
import sys
import re

path = os.path.join(os.path.realpath(os.path.dirname(sys.argv[0])))
source_path = os.path.join(path,"source")
translate_path = os.path.join(path, "translate")

def main():
    if not os.path.exists(translate_path):
        os.makedirs(translate_path)

    try:
        with open(os.path.join(source_path,"OpOption.bin"),"rb") as f:

            table_data = []

            # Read only the unique strings. 
            f.seek(9677)
            for i in range(41):
                offset = hex(f.tell())
                text = ""

                # Read string.
                byte_string = b''
                while True:
                    bytes = f.read(1)
                    if bytes == b'\x00': # Strings are terminated with single byte 00.
                        text = byte_string.decode("shift_jis_2004")
                        break
                    byte_string += bytes

                # Wrap parameters in curly brackets.
                text = re.split("(![!a-z0-9=]+)([^!]*)",text)
                new_text = ""
                for i in text:
                    if i != "":
                        if i.startswith("!"):
                            new_text += "{" + i + "}"
                        else:
                            new_text += i
                            
                table_data.append([offset,new_text])

            with open(os.path.join(translate_path, "OpOption.bin.csv"),"w", encoding="utf-8") as txt_output:
                for i in table_data:
                    txt_output.write("|".join([i[0],i[1]]) + "\n")

        print(f"OpOption.bin: Entries: {len(table_data)}.")

    except FileNotFoundError:
        print("OpOption.bin not found in source directory.")


if __name__ == "__main__":
    main()