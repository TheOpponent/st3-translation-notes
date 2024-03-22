// Based on the PRSTools by ToriningenGames, adapted as a shared library.
// https://github.com/ToriningenGames/PRSTools
//
// PRSTools original license:
//
// MIT License
//
// Copyright (c) 2024 Orion Chandler
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.


#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#define matchlim 0x2000
enum mode { m_none, m_direct, m_long, m_short0, m_short1, m_short2, m_short3, m_done };

struct compnode {
        enum mode type;
        uint16_t offset;
        uint16_t size;
        uint8_t data;
};

// Compression functions.

int findMatch(uint8_t *sourcedata, int insize, int index, int *offset)
{
        //Start at the prior byte, seek back to beginning of potential offset
        //Find the longest match
        //There are more efficient ways to do this, but...
        int matchlen = 0;
        for (int i = 1; matchlen < 255 && i < matchlim; i++) {
                int len = 0;
                if (i > index) break;
                while (sourcedata[index+len] == sourcedata[index+len-i]) {
                        len++;
                        if (index+len == insize) break;
                        if (len == 255) break;
                }
                if (len > matchlen) {
                        *offset = i;
                        matchlen = len;
                }
        }
        return matchlen;
}

int findShortMatch(uint8_t *sourcedata, int insize, int index, int *offset)
{
        //Seek for short matches only!
        int matchlen = 0;
        for (int i = 1; matchlen < 5 && i < 256; i++) {
                int len = 0;
                if (i > index) break;
                while (sourcedata[index+len] == sourcedata[index+len-i]) {
                        len++;
                        if (index+len == insize) break;
                        if (len == 5) break;
                }
                if (len > matchlen) {
                        *offset = i;
                        matchlen = len;
                }
        }
        return matchlen;
}

void compress(uint8_t *source, int insize, struct compnode *nodes)
{
        int nodein = 0;
        //Compress each byte
        for (int i = 0; i < insize; i++) {
                int offset;
                int size = findMatch(source, insize, i, &offset);
                //Check type of copy
                if (size > 5 || (size > 2 && offset > 255)) {
                        //Long copy
                        nodes[nodein].type = m_long;
                        nodes[nodein].offset = 0x2000-offset;
                        nodes[nodein].size = size-1;
                        i += nodes[nodein++].size;
                } else {
                        //Short copy?
                        size = findShortMatch(source, insize, i, &offset);
                        if (size > 1) {
                                //Short copy
                                nodes[nodein].type = m_short0;
                                nodes[nodein].offset = 256-offset;
                                size = size > 5 ? 5 : size;
                                i += size-1;
                                size -= 2;
                                nodes[nodein++].type += size;
                        } else {
                                //Literal
                                nodes[nodein].type = m_direct;
                                nodes[nodein++].data = source[i];
                        }
                }
        }
        nodes[nodein].type = m_done;
}

void addControl(uint8_t **c, uint8_t **d, struct compnode *node)
{
        uint8_t *control = *c;
        uint8_t *data = *d;
        static int bits = 0;
        switch (node->type) {
                case m_direct :
                        if (!bits) {
                                //no room in control byte
                                control = data++;
                                *control = 0;
                                bits = 8;
                        }
                        *control |= 1 << (8-bits);
                        bits--;
                        *data++ = node->data;
                        break;
                case m_short0 :
                case m_short1 :
                case m_short2 :
                case m_short3 :
                        //Handle the control byte first
                        if (!bits) {
                                //no room in control byte
                                control = data++;
                                *control = 0;
                                bits = 8;
                        }
                        if (bits == 1) {
                                //Not enough room for the front half
                                //Control split across two bytes
                                *control |= 0 << (8-bits);
                                control = data++;
                                *control = 0;
                                bits = 8;
                                *control |= 0 << (8-bits);
                                bits--;
                        } else {
                                //Room for front half
                                *control |= 0 << (8-bits);
                                bits--;
                                *control |= 0 << (8-bits);
                                bits--;
                        }
                        //Get the size
                        int shortsize = node->type - m_short0;
                        if (!bits) {
                                //no room in control byte
                                control = data++;
                                *control = 0;
                                bits = 8;
                        }
                        if (bits == 1) {
                                //Not enough room for the back half
                                //Control split across two bytes
                                *control |= (!!(shortsize & 2)) << (8-bits);
                                control = data++;
                                *control = 0;
                                bits = 8;
                                *control |= (shortsize & 1) << (8-bits);
                                bits--;
                        } else {
                                //Room for back half
                                *control |= (!!(shortsize & 2)) << (8-bits);
                                bits--;
                                *control |= (shortsize & 1) << (8-bits);
                                bits--;
                        }
                        //Data goes here
                        *data++ = node->offset;
                        break;
                case m_long :
                        if (!bits) {
                                //no room in control byte
                                control = data++;
                                *control = 0;
                                bits = 8;
                        }
                        if (bits == 1) {
                                //Control split across two bytes
                                *control |= 0 << (8-bits);
                                control = data++;
                                *control = 0;
                                bits = 8;
                                *control |= 1 << (8-bits);
                                bits--;
                        } else {
                                //Plenty of space
                                *control |= 0 << (8-bits);
                                bits--;
                                *control |= 1 << (8-bits);
                                bits--;
                        }
                        //What kind of size are we looking at?
                        if (node->size > 8) {
                                //Big size
                                *data++ = (node->offset & 0x1F) << 3;
                                *data++ = (node->offset & 0x1FE0) >> 5;
                                *data++ = node->size;
                        } else {
                                //Small size
                                *data = (node->size-1) & 0x07;
                                *data++ |= (node->offset & 0x1F) << 3;
                                *data++ = (node->offset & 0x1FE0) >> 5;
                        }
                        break;
                case m_done :
                        if (!bits) {
                                //no room in control byte
                                control = data++;
                                *control = 0;
                                bits = 8;
                        }
                        if (bits == 1) {
                                //Control split across two bytes
                                *control |= 0 << (8-bits);
                                control = data++;
                                *control = 0;
                                bits = 8;
                                *control |= 1 << (8-bits);
                                bits--;
                        } else {
                                //Plenty of space
                                *control |= 0 << (8-bits);
                                bits--;
                                *control |= 1 << (8-bits);
                                bits--;
                        }
                        *data++ = 0;
                        *data++ = 0;
        }
        *c = control;
        *d = data;
}

int compress_store(uint8_t *data, struct compnode *nodes)
{
        uint8_t *start = data;
        uint8_t *control = data;
        //While there are nodes
        for (; nodes->type != m_done; nodes++) {
                addControl(&control, &data, nodes);
        }
        //One more for the terminus
        addControl(&control, &data, nodes);
        return data - start;
}

int prs_compress(uint8_t *indata, int insize, uint8_t **outdata) {
    struct compnode *nodes = malloc(sizeof(*nodes) * insize + 1);
    if (!nodes) {
        return -1;
    }

    compress(indata, insize, nodes);
    // Allocate memory for the output data with space to spare for safety.
    // If compressed data is larger than input, most likely compressed
    // data was used in input, which should be considered an error.
    *outdata = malloc(insize * 2);
    if (!*outdata) {
        free(nodes);
        return -1;
    }
    int outsize = compress_store(*outdata, nodes);
    free(nodes);
    return outsize;
}

// Decompression functions

enum mode getControl(uint8_t **indata)
{
        static uint8_t control;
        static int bits = 0;
        if (!bits) {
                control = **indata;
                (*indata)++;
                bits = 8;
        }
        if (control & 1) {
                //Literal
                control >>= 1;
                bits--;
                return m_direct;
        }
        control >>= 1;
        bits--;
        if (!bits) {
                control = **indata;
                (*indata)++;
                bits = 8;
        }
        if (control & 1) {
                //Long copy
                control >>= 1;
                bits--;
                return m_long;
        }
        //Short copy
        control >>= 1;
        bits--;
        if (!bits) {
                control = **indata;
                (*indata)++;
                bits = 8;
        }
        int len = 0;
        len = control & 1 ? 2 : 0;
        control >>= 1;
        bits--;
        if (!bits) {
                control = **indata;
                (*indata)++;
                bits = 8;
        }
        len += control & 1 ? 1 : 0;
        control >>= 1;
        bits--;
        return m_short0 + len;
}

void decompress(uint8_t *indata, int insize, struct compnode *nodes)
{
        int foundEnd = 0;
        uint8_t *start = indata;
        for (int i = 0; i < insize; i++) {
                switch (nodes->type = getControl(&indata)) {
                        case m_direct :
                                nodes->data = *indata++;
                                nodes++;
                                break;
                        case m_short0 :
                        case m_short1 :
                        case m_short2 :
                        case m_short3 :
                                nodes->offset = *indata++;
                                nodes++;
                                break;
                        case m_long :
                                nodes->size = *indata & 0x07;
                                nodes->offset = (*indata++ & 0xF8) >> 3;
                                nodes->offset |= *indata++ << 5;
                                //Special detect for the end phrase
                                if (!nodes->size && !nodes->offset) {
                                        foundEnd = 1;
                                        if (indata - start < insize) {
                                                fprintf(stderr, "Warning: Extra input data found!\n");
                                        }
                                        //Escape this loop
                                        i = insize;
                                        break;
                                }
                                if (!nodes->size) {
                                        nodes->size = *indata++;
                                } else {
                                        nodes->size++;
                                }
                                nodes++;
                                break;
                }
        }
        if (!foundEnd) {
                fprintf(stderr, "Warning: Input not terminated correctly!\n");
                nodes->type = m_long;
                nodes->offset = 0;
                nodes->size = 0;
        }
}

int decompress_store(uint8_t *data, struct compnode *nodes)
{
        int size;
        uint8_t *start = data;
        for (; nodes->type != m_long || nodes->offset != 0 || nodes->size != 0; nodes++) {
                switch (nodes->type) {
                        case m_direct :
                                *data++ = nodes->data;
                                break;
                        case m_short3 :
                                size = 5; if (0)
                        case m_short2 :
                                size = 4; if (0)
                        case m_short1 :
                                size = 3; if (0)
                        case m_short0 :
                                size = 2;
                                for (int i = 0; i < size; i++) {
                                        *data = *(data-(256-nodes->offset));
                                        data++;
                                }
                                break;
                        case m_long :
                                size = nodes->size + 1;
                                for (int i = 0; i < size; i++) {
                                        *data = *(data-(0x2000-nodes->offset));
                                        data++;
                                }
                                break;
                }
        }
        return data - start;
}

int prs_decompress(uint8_t *indata, int insize, uint8_t *outdata, int outsize) {
    struct compnode *nodes = malloc(sizeof(*nodes) * insize);
    if (!nodes) {
        return -1;
    }

    decompress(indata, insize, nodes);
    *outdata = malloc(outsize);
    if (!*outdata) {
        free(nodes);
        return -1;
    }

    decompress_store(outdata, nodes);
    free(nodes);
    return 0;
}
