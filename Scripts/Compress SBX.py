# Uses the prs.net implementation of PRS compression:
# https://github.com/FraGag/prs.net/blob/master/FraGag.Compression.Prs/Prs.Impl.cs
# This script adds wrapping required by Sakura Taisen 3.
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
import struct
import sys
import clr 

path = os.path.realpath(os.path.dirname(sys.argv[0]))
assembly_path = os.path.join(path,os.path.normpath(r".\lib\FraGag.Compression.Prs.dll"))
clr.AddReference(assembly_path)
import FraGag.Compression as Prs

def compress(input_file):

    with open(input_file,"rb") as file:
        if os.path.getsize(0):
            print(f"{input_file}: Unable to read all bytes.")
            return

        input_data = file.read()
        raw_length = len(input_data)
        compressed_data = bytearray(Prs.Prs.Compress(input_data))

        while True:
            if len(compressed_data) % 4 != 0:
                compressed_data.append(0)
            else:
                break

        output_length = len(compressed_data)
        # padded_length includes first 8 bytes of footer.
        padded_length = output_length + 8

        compressed_data.extend([67, 80, 82, 83, 0, 0, 0, 0, 69, 79, 70, 67, 0, 0, 0, 0]) # Footer: CPRS....EOFC....

        # The header of the output includes the padded length, input data length, and unpadded length.
        output_data = b''.join([b'ASCR',struct.pack("<I",padded_length),struct.pack("<I",raw_length),struct.pack("<I",output_length),compressed_data])

    return output_data


def main():

    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]

        output_data = compress(input_file)

        with open(output_file,"wb") as file:
            file.write(output_data)

    else:
        print("Specify input and output file.")
        return

    print(f"{input_file}: Wrote {len(output_data)} bytes.")

if __name__ == "__main__":
    main()