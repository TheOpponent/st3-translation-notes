# Uses the prs.net implementation of PRS compression:
# https://github.com/FraGag/prs.net/blob/master/FraGag.Compression.Prs/Prs.Impl.cs
#
# This script decompresses SBX files, which are PRS-compressed files with extra wrapping added.
# Uncompressed files are written into the 'source' subdirectory with extension .SBX.bin.
# Existing files will be overwritten.
#
# prs.net original license:
#
# Copyright (c) 2012, Francis Gagné
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the <organization> nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os
import sys
import struct
import clr

path = os.path.realpath(os.path.dirname(sys.argv[0]))
assembly_path = os.path.join(path,os.path.normpath(r".\lib\FraGag.Compression.Prs.dll"))
clr.AddReference(assembly_path)
from FraGag.Compression import Prs

source_path = os.path.join(path,"source")

def decompress(input_file):

    with open(input_file,"rb") as file:
        signature = file.read(4)
        # Read bytes as little-endian, unsigned integers.
        padded_length = struct.unpack("<I",file.read(4))[0] # Compressed data size and header. This value represents all of the compressed data ending with the 'CPRS' signature and the preceding and following 00 bytes.
        raw_length = struct.unpack("<I",file.read(4))[0] # Uncompressed data size.
        data_length = struct.unpack("<I",file.read(4))[0] # Compressed data size. This value contains only the actual data without the 'CPRS' signature.

        input_data = bytearray(file.read(data_length))
        # Remaining bytes may contain padding bytes of 00.
        # The EOFC footer will only be found in files containing a single chunk of PRS-compressed data.
        file.read(8) # Footer: CPRS....EOFC....

        try:
            output_data = signature + struct.pack("<I",raw_length) + bytes(Prs.Decompress(input_data))
        except:
            print("Unable to decompress:",input_file)
            return None

        print(f"{repr(input_file)}: Uncompressed size: {raw_length}. Compressed size: {data_length}. Compressed size with header: {padded_length}.")

        return output_data


def main():

    if len(sys.argv) == 2:
        print("Specify output file, or pass no arguments to read SBX files in working directory.")
        return

    if not os.path.exists(source_path):
        os.makedirs(source_path)

    if len(sys.argv) >= 3:
        output_data = decompress(sys.argv[1])

        if output_data is not None:
            with open(sys.argv[2],"wb") as output_file:
                output_file.write(bytearray(output_data))

        return

    file_count = 0
    # If input and output files are not specified, read files in working directory.
    for file in [i for i in os.listdir(path) if i.lower().endswith(('.sbx'))]:
        output_data = bytearray(decompress(file))

        # Output decompressed files in 'source' subdirectory.
        with open(os.path.join(source_path,file + ".bin"),"wb") as output_file:
            output_file.write(output_data)

        file_count += 1

    print(f"Decompressed {file_count} files.")


if __name__ == "__main__":
    main()