#!/usr/bin/env python3
# -*- coding: utf-8 -*-

### Edited/translated from http://chief-net.ru/forum/topic.php?forum=2&topic=77&postid=1527319695#1527319695
### Original comments:
# ZetpeR xax007@yandex.ru
# Для распаковки скриптов .SBX игры Sakura Taisen 3 PC
# Алгоритм распаковки сжатия принадлежит
# SEGA PRS Decompression (LZS variant)
# Credits:
# based on information/comparing output with
# Nemesis/http://www.romhacking.net/utils/671/
# puyotools/http://code.google.com/p/puyotools/
# fuzziqer software prs/http://www.fuzziqersoftware.com/projects.php


import os, sys
import struct
from array import array

path = os.path.realpath(os.path.dirname(sys.argv[0]))

def main():
    if not os.path.exists(path + "\\Unpack"):
        os.makedirs(path + "\\Unpack")

    for mult_file in os.listdir(path):
        if mult_file.lower().endswith(('.sbx')):
            Unpack(mult_file)

def Unpack(mult_file):
    # Read files in working directory. If first 4 bytes does not contain signature 'ASCR', skip the file.
    f = open(path + "\\" + mult_file,"rb")
    if f.read(4) != b'ASCR':
        print("Not SBX:",mult_file)
        return

    # Read bytes as little-endian, unsigned integers.
    size_2 = struct.unpack("<I",f.read(4))[0] # Compressed data size and header. This value represents all of the compressed data ending with the 'CPRS' signature and the preceding and following 00 bytes.
    size = struct.unpack("<I",f.read(4))[0] # Uncompressed data size.
    size_comp = struct.unpack("<I",f.read(4))[0] # Compressed data size. This value contains only the actual data without the 'CPRS' signature.
    fd = f.read(size_comp)
    # Remaining bytes may contain padding bytes of 00.
    f.read(16) # Footer: CPRS....EOFC....
    print(f"{mult_file}: Unpacked size: {size}. Compressed size: {size_comp}. Compressed size with header: {size_2}.")

    bytes = bytearray(fd)
    prs = DecompressPrs(bytes) 
    data = prs.decompress()

    # Output decompressed files in Unpack subdirectory.
    f2 = open(path + "\\Unpack\\" + mult_file + ".bin","wb")
    f2.write(data)
    f2.close()
    f.close()

class DecompressPrs:
    def __init__(self, data):
        self.ibuf = array("B", data)
        self.obuf = array("B")

        self.iofs = 0
        self.bit = 0
        self.cmd = 0
   
    def getByte(self):
        val = self.ibuf[self.iofs]
        self.iofs += 1
        return val
   
    def getBit(self):
        if self.bit == 0:
            self.cmd = self.getByte()
            self.bit = 8
        bit = self.cmd & 1
        self.cmd >>= 1
        self.bit -= 1
        return bit

    def decompress(self):
        while self.iofs < len(self.ibuf):
            cmd = self.getBit()
            if cmd:
                self.obuf.append(self.ibuf[self.iofs])
                self.iofs += 1
            else:
                t = self.getBit()
                if t:
                    a = self.getByte()
                    b = self.getByte()

                    offset = ((b << 8) | a) >> 3
                    amount = a & 7
                    if self.iofs < len(self.ibuf):
                        if amount == 0:
                            amount = self.getByte() + 1
                        else:
                            amount += 2

                    start = len(self.obuf) - 0x2000 + offset
                else:
                    amount = 0
                    for j in range(2):
                        amount <<= 1
                        amount |= self.getBit()
                    offset = self.getByte()
                    amount += 2

                    start = len(self.obuf) - 0x100 + offset
                for j in range(amount):
                    if start < 0:
                        self.obuf.append(0)
                    elif start < len(self.obuf):
                        self.obuf.append(self.obuf[start])
                    else:
                        self.obuf.append(0)
                    start += 1

        return self.obuf.tobytes()

if __name__ == "__main__":
    main()