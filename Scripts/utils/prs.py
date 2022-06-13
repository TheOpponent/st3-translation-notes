# Functions for PRS compression and decompression.
# This is intended for use with SBX files, which use additional wrapping.
#
# Uses the prs.net implementation of PRS compression:
# https://github.com/FraGag/prs.net/blob/master/FraGag.Compression.Prs/Prs.Impl.cs
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

path = os.path.realpath(os.path.dirname(__file__))
assembly_path = os.path.join(path,os.path.normpath(r"..\lib\FraGag.Compression.Prs.dll"))
clr.AddReference(assembly_path)
from FraGag.Compression import Prs

def compress(input_data):
    """Compresses a bytes object using PRS compression.
    This function adds wrapping required by Sakura Taisen 3.
    
    Returns a bytes object."""

    signature = input_data[0:4]
    raw_length = len(input_data)
    compressed_data = bytearray(Prs.Compress(input_data[8:]))

    while True:
        if len(compressed_data) % 4 != 0:
            compressed_data.append(0)
        else:
            break

    output_length = len(compressed_data)
    # padded_length includes first 8 bytes of footer.
    padded_length = output_length + 8

    # The header of the output includes the padded length, input data length, and unpadded length.
    output_data = b''.join([signature,struct.pack("<I",padded_length),struct.pack("<I",raw_length),struct.pack("<I",output_length),compressed_data,b'CPRS\x00\x00\x00\x00'])

    return output_data


def decompress(input_data):
    """Decompresses a PRS-compressed bytes object that has
    extra wrapping added.
    
    Returns a bytes object."""
    signature = input_data[0:4]
    # Read bytes as little-endian, unsigned integers.
    padded_length = struct.unpack("<I",input_data[4:8])[0] # Compressed data size and header. This value represents all of the compressed data ending with the 'CPRS' signature and the preceding and following 00 bytes.
    raw_length = struct.unpack("<I",input_data[8:12])[0] # Uncompressed data size.
    data_length = struct.unpack("<I",input_data[12:16])[0] # Compressed data size. This value contains only the actual data without the 'CPRS' signature.

    input_data = bytearray(input_data[16:])

    try:
        output_data = signature + struct.pack("<I",raw_length) + bytes(Prs.Decompress(input_data))
    except:
        print("Unable to decompress.")
        return None

    return output_data


def main():

    if len(sys.argv) >= 4:
        with open(sys.argv[2],"rb") as input_file:
            if sys.argv[1] == "-c":
                output_data = compress(input_file.read())

            elif sys.argv[1] == "-d":
                output_data = decompress(input_file.read())

        if output_data:
            with open(sys.argv[3],"wb") as output_file:
                output_file.write(output_data)
                print(f"Wrote {len(output_data)} bytes.")
                return
    
    print("Usage: [-c] [-d] INPUT_FILE OUTPUT_FILE")


if __name__ == "__main__":
    main()