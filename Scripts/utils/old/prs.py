# PRS compression functions.
# This module is a pure Python port of the prs.net implementation:
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
#
#
# The compression and lookbehind functions are a new implementation by
# https://github.com/chipx86, used with permission.
#
# This implementation adds wrapping required by Sakura Taisen 3.

import struct
import sys
import time
from array import array
from collections import defaultdict, deque
from io import BytesIO


class Prs:
    """Class for input file to compress or decompress."""

    def __init__(self, data):
        self.input_buffer = bytearray(data)
        self.output_buffer = BytesIO()
        self.output_buffer_len = 0
        self.current_data = array("B")

        # The first 8 bytes of a file to be processed contain a 4-byte signature,
        # followed by the file length. These are not included in the input_dict.
        self.signature = self.input_buffer[0:4]
        self.input_length = len(self.input_buffer) - 8
        self.input_dict = self.input_buffer[8:]

        self.bit_position = 0
        self.control_byte = 0

        self.output_length = 0
        self.padded_length = 0

    def put_control_bit(self, *bits):
        control_byte = self.control_byte
        bit_position = self.bit_position

        for i in bits:
            control_byte >>= 1
            control_byte |= i << 7
            bit_position += 1

            if bit_position >= 8:
                self.flush(control_byte)
                self.current_data = array("B")
                control_byte = 0
                bit_position = 0

        self.control_byte = control_byte
        self.bit_position = bit_position

    def copy(self, offset, size):
        # Mode 1: Short copy mode.
        if offset >= -256 and size <= 5:
            size -= 2
            self.put_control_bit(0, 0, (size >> 1) & 1)
            self.current_data.append(offset & 255)
            self.put_control_bit(size & 1)
        else:
            # Mode 2: Long copy, short size.
            if size <= 9:
                self.put_control_bit(0)
                self.current_data.extend(
                    [((offset << 3) & 248) | ((size - 2) & 7), ((offset >> 5) & 255)]
                )
                self.put_control_bit(1)
            # Mode 3: Long copy, long size.
            else:
                self.put_control_bit(0)
                self.current_data.extend(
                    [((offset << 3) & 248), ((offset >> 5) & 255), (size - 1)]
                )
                self.put_control_bit(1)

    def flush(self, control_byte):
        """Write compressed data to output_buffer."""

        output_buffer = self.output_buffer
        output_buffer.write(bytes([control_byte]))
        output_buffer.write(self.current_data)
        self.output_buffer_len += len(self.current_data) + 1

    def check(self, offset=0):
        if (
            self.current_lookbehind_length <= 256
            and (self.position + self.current_lookbehind_length + offset)
            <= self.input_length
            and self.input_dict[
                self.current_lookbehind_position
                + self.current_lookbehind_length
                + offset
                - 1
            ]
            == self.input_dict[
                self.position + self.current_lookbehind_length + offset - 1
            ]
        ):
            self.current_lookbehind_length += 1
            return 1
        else:
            return 0

    def lookbehind(self, position, byte_pos_cache, window, input_dict, input_length):
        """Scan the input_buffer in reverse to determine lookbehind offset and length."""
        lookbehind_offset = 0
        lookbehind_length = 0

        current_byte = input_dict[position]
        byte_position_cache_keys = [(current_byte,)]

        if position + 1 < input_length:
            byte2 = input_dict[position + 1]
            byte_position_cache_keys.append((current_byte, byte2))

            if position + 2 < input_length:
                byte3 = input_dict[position + 2]
                byte_position_cache_keys.append(
                    (
                        current_byte,
                        byte2,
                        byte3,
                    )
                )

                if position + 3 < input_length:
                    byte_position_cache_keys.append(
                        (
                            current_byte,
                            byte2,
                            byte3,
                            input_dict[position + 3],
                        )
                    )

        seen_positions = set()

        # ChipX86: In the original code, we were comparing against the
        #          larger of 0 and (position - 8176). In the ported code,
        #          we were comparing within a range. What we want is to
        #          figure out the cap and then compare against that
        #          directly (once -- not per-iteration).
        #
        #          Update: We're now iterating based on a byte position cache
        #          lookup table.
        for cache_key in reversed(byte_position_cache_keys):
            byte_positions = byte_pos_cache[cache_key]

            if not byte_positions:
                continue

            for i, current_lookbehind_position in enumerate(reversed(byte_positions)):
                if current_lookbehind_position < position - window:
                    # We're done, and we have some older entries outside the window
                    # we can clear out to save memory.
                    if i > 0:
                        # We have some to clear out, but some remain.
                        for j in range(len(byte_positions) - i):
                            byte_positions.popleft()
                    else:
                        # Everything in this cache is obsolete. Delete it.
                        del byte_pos_cache[cache_key]

                    break

                # ChipX86: Avoid looking at any positions we've already
                #          checked.
                if current_lookbehind_position in seen_positions:
                    continue

                seen_positions.add(current_lookbehind_position)

                # ChipX86: In the old code, once we got to this logic, we always
                #          had a value of 2 here. No need to set to 1 and then +=.
                #          We're now setting to the value we'd have at this point.
                #
                # Update: We know we've already covered a certain span via the
                #         cache, so start checking beyond that.
                current_lookbehind_length = len(cache_key) + 1

                # ChipX86: Update: Slight change to ordering of checks. The <= 256
                #          is rarely the limiting factor, so do it last.
                while (
                    position + current_lookbehind_length <= input_length
                    and (
                        input_dict[position + current_lookbehind_length - 1]
                        == input_dict[
                            current_lookbehind_position + current_lookbehind_length - 1
                        ]
                    )
                    and current_lookbehind_length <= 256
                ):
                    current_lookbehind_length += 1

                current_lookbehind_length -= 1

                # ChipX86: Tiny optimization: Perform the cheapest checks
                #          first. This will be the first length comparison,
                #          then the >= 3. The (>= 2 and ...) involves
                #          multiple conditionals, and its >= 2 applies when
                #          >= 3, so avoid that in the >= 3 case.
                #
                #          Also, this first comparison used to compare
                #          against self.lookbehind_length, but the ported
                #          code does not. With this change, we get
                #          different output, but I save 2 more seconds
                #          locally. Would need to verify the final output.
                if current_lookbehind_length > lookbehind_length and (
                    current_lookbehind_length >= 3
                    or (
                        current_lookbehind_length >= 2
                        and current_lookbehind_position - position >= -256
                    )
                ):
                    lookbehind_offset = current_lookbehind_position - position
                    lookbehind_length = current_lookbehind_length

            if lookbehind_length > 0:
                # ChipX86: We found a match. Don't check any smaller byte
                #          caches.
                break

        return lookbehind_offset, lookbehind_length

    def compress(self):
        input_dict = self.input_dict
        input_length = self.input_length
        position = 0
        window = 8176

        # ChipX86: We're maintaining a sliding byte cache. This maps bytes
        #          to lists of positions, in ascending order.
        #
        #          The approach is that we take is to add to the cache for each
        #          new position, taking all bytes between the old marked
        #          position and the new one and recording their positions. We
        #          leave old positions outside the window in the cache, and
        #          lazily clear them out in lookbehind() when we encounter
        #          them.
        #
        #          This has an absolute worst cast of 256 * 8176 entries *
        #          storage space for a number (which varies). I calculate that
        #          as about 83MB or so.
        #
        #          BUT that's a pathological case. That requires 8176 bytes of
        #          '0' in a row, then 8176 bytes of '1', then 8176 of '2', etc.
        #          In reality, this will be far less. In the dataset provided
        #          for testing, this caps out at ~500KB.
        #
        #          The performance is orders of magnitude faster than the
        #          brute-force approach, massively narrowing the search space
        #          for any byte.
        byte_pos_cache = defaultdict(lambda: deque([], window))
        byte_pos_cache_start_pos = 0

        while position < input_length:
            for i in range(byte_pos_cache_start_pos, position):
                byte = input_dict[i]
                byte_pos_cache[byte].append(i)

                try:
                    byte2 = input_dict[i + 1]
                    byte_pos_cache[(byte, byte2)].append(i)

                    byte3 = input_dict[i + 2]
                    byte_pos_cache[(byte, byte2, byte3)].append(i)

                    byte4 = input_dict[i + 3]
                    byte_pos_cache[(byte, byte2, byte3, byte4)].append(i)
                except IndexError:
                    pass

            byte_pos_cache_start_pos = position

            lookbehind_offset, lookbehind_length = self.lookbehind(
                position=position,
                byte_pos_cache=byte_pos_cache,
                window=window,
                input_dict=input_dict,
                input_length=input_length,
            )

            # Mode 0: Direct single byte read.
            if lookbehind_length == 0:
                self.current_data.append(input_dict[position])
                position += 1
                self.put_control_bit(1)
            # Perform copy operations.
            else:
                self.copy(lookbehind_offset, lookbehind_length)
                position += lookbehind_length

        self.put_control_bit(0, 1)

        if self.bit_position != 0:
            self.flush((self.control_byte << self.bit_position) >> 8)

        output_buffer = self.output_buffer
        output_buffer.write(b"\0\0")
        output_buffer_len = self.output_buffer_len + 2

        while True:
            if output_buffer_len % 4 != 0:
                output_buffer.write(b"\0")
                output_buffer_len += 1
            else:
                break

        self.output_length = output_buffer_len
        self.padded_length = self.output_length + 8

        output_buffer.write(
            bytes([67, 80, 82, 83, 0, 0, 0, 0, 69, 79, 70, 67, 0, 0, 0, 0])
        )  # Footer: CPRS....EOFC....

        return output_buffer.getvalue()

    def decompress(self):
        input_length = struct.unpack("<I", self.input_buffer[12:16])[0]
        self.uncompressed_size = self.input_buffer[8:12]
        output_buffer = self.output_buffer

        # Compressed files in Sakura Taisen 3 have a 16-byte header,
        # which is not included in decompression.
        self.input_data = BytesIO(self.input_buffer[16:])

        output_buffer.write(self.signature)
        output_buffer.write(self.uncompressed_size)

        self.bit_position = 9

        self.current_byte = self.input_data.read(1)
        while self.input_data.tell() < input_length:
            if self.get_control_bit() != 0:
                output_buffer.write(self.input_data.read(1))
                continue

            if self.get_control_bit() != 0:
                lookbehind_offset = ord(self.input_data.read(1))
                lookbehind_offset |= ord(self.input_data.read(1)) << 8
                # Break at end of compressed data.
                if lookbehind_offset == 0:
                    break

                lookbehind_length = lookbehind_offset & 7
                lookbehind_offset = (lookbehind_offset >> 3) | -8192

                if lookbehind_length == 0:
                    lookbehind_length = ord(self.input_data.read(1)) + 1
                else:
                    lookbehind_length += 2

            else:
                lookbehind_length = 0
                lookbehind_length = (lookbehind_length << 1) | self.get_control_bit()
                lookbehind_length = (lookbehind_length << 1) | self.get_control_bit()
                lookbehind_offset = ord(self.input_data.read(1)) | -256
                lookbehind_length += 2

            for _ in range(0, lookbehind_length):
                write_position = output_buffer.tell()
                output_buffer.seek(write_position + lookbehind_offset)
                byte = output_buffer.read(1)
                output_buffer.seek(write_position)
                output_buffer.write(byte)

        return output_buffer.getvalue()

    def get_control_bit(self):
        current_byte = ord(self.current_byte)
        bit_position = self.bit_position
        bit_position -= 1

        if bit_position == 0:
            current_byte = ord(self.input_data.read(1))
            bit_position = 8

        flag = current_byte & 1
        current_byte >>= 1
        self.current_byte = chr(current_byte)
        self.bit_position = bit_position

        return flag


def compress(input_file):
    input_dict = Prs(input_file)
    compressed_data = input_dict.compress()

    # The header of the output includes the padded length, input length, and unpadded length.
    output_data = b"".join(
        [
            input_dict.signature,
            struct.pack("<I", input_dict.padded_length),
            struct.pack("<I", input_dict.input_length),
            struct.pack("<I", input_dict.output_length),
            compressed_data,
        ]
    )

    return output_data


def decompress(input_file):
    input_data = Prs(input_file)
    return input_data.decompress()


def main():
    start_time = time.time()

    if len(sys.argv) >= 4:
        with open(sys.argv[2], "rb") as input_file:
            input_data = input_file.read()
            if len(input_data) == 0:
                print(f"{input_file}: Unable to read all bytes.")

        if sys.argv[1] == "-c":
            output_data = compress(input_data)

        elif sys.argv[1] == "-d":
            output_data = decompress(input_data)

        if output_data:
            with open(sys.argv[3], "wb") as output_file:
                output_file.write(output_data)
                print(f"Wrote {len(output_data)} bytes.")
                return

        print("Finished in ", time.time() - start_time, "seconds.")

    else:
        print("Usage: [-c] [-d] INPUT_FILE OUTPUT_FILE")


if __name__ == "__main__":
    main()
