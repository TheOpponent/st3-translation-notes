# This script takes a file containing ADCG chunks and decompresses them.
# The decompressed ADCG chunks are output in the working directory with the extension .adcg.
# In files that contain them, ADCG headers are preceded by an AGR1 or AGR2 signature, 
# which is followed by 00 00 00 00.

import mmap
import sys
from utils import prs


def extract_adcg(input_file):

    files_written = 0
    with open(input_file,"rb") as f:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as mm:
            while True:
                adcg_pos = mm.find(b'ADCG',mm.tell())
                if adcg_pos != -1:
                    mm.seek(adcg_pos)

                    abs_offset = mm.tell()
                    adcg_prs_data = bytearray()
                    while True:
                        buffer = mm.read(4)
                        adcg_prs_data += buffer
                        if buffer == b'EOFC':
                            adcg_prs_data += mm.read(4)
                            break

                    output_data = prs.decompress(adcg_prs_data)

                    filename = "_" + hex(abs_offset)

                    with open(input_file + filename + ".adcg","wb") as output_file:
                        output_file.write(output_data)
                        print(f"{input_file + filename}: Wrote {len(output_data)} bytes.")
                        files_written += 1

                else:
                    print(f"Wrote {files_written} files.")
                    break


def main():
    if len(sys.argv) > 1:
        for i in sys.argv[1:]:
            extract_adcg(i)
    else:
        print("Specify input file(s) containing ADCG data.")


if __name__ == "__main__":
    main()
