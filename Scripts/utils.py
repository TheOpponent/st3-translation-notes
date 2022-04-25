# Helper functions for translation scripts.

import re

def ascii_to_sjis(input_str,*args,**kwargs):
    """Converts a string of ASCII characters to 
    byte-swapped Shift-JIS and null-terminate it."""

    table = {'A':b'\x82\x60',
    'B':b'\x82\x61',
    'C':b'\x82\x62',
    'D':b'\x82\x63',
    'E':b'\x82\x64',
    'F':b'\x82\x65',
    'G':b'\x82\x66',
    'H':b'\x82\x67',
    'I':b'\x82\x68',
    'J':b'\x82\x69',
    'K':b'\x82\x6A',
    'L':b'\x82\x6B',
    'M':b'\x82\x6C',
    'N':b'\x82\x6D',
    'O':b'\x82\x6E',
    'P':b'\x82\x6F',
    'Q':b'\x82\x70',
    'R':b'\x82\x71',
    'S':b'\x82\x72',
    'T':b'\x82\x73',
    'U':b'\x82\x74',
    'V':b'\x82\x75',
    'W':b'\x82\x76',
    'X':b'\x82\x77',
    'Y':b'\x82\x78',
    'Z':b'\x82\x79',
    'a':b'\x82\x7A',
    'b':b'\x82\x7B',
    'c':b'\x82\x7C',
    'd':b'\x82\x7D',
    'e':b'\x82\x7E',
    'f':b'\x82\x80',
    'g':b'\x82\x87',
    'h':b'\x82\x88',
    'i':b'\x82\x89',
    'j':b'\x82\x8A',
    'k':b'\x82\x8B',
    'l':b'\x82\x8C',
    'm':b'\x82\x8D',
    'n':b'\x82\x8E',
    'o':b'\x82\x8F',
    'p':b'\x82\x90',
    'q':b'\x82\x91',
    'r':b'\x82\x92',
    's':b'\x82\x93',
    't':b'\x82\x94',
    'u':b'\x82\x95',
    'v':b'\x82\x96',
    'w':b'\x82\x97',
    'x':b'\x82\x98',
    'y':b'\x82\x99',
    'z':b'\x82\x9A',
    ' ':b'\x81\x40',
    '.':b'\x81\x44',
    ',':b'\x81\x43',
    ':':b'\x81\x46',
    ';':b'\x81\x47',
    '?':b'\x81\x48',
    '!':b'\x81\x49',
    '"':b'\x81\x4A',
    '—':b'\x81\x5C', # Em dash
    '–':b'\x81\x5B', # En dash
    '-':b'\x81\x5D', # Dash
    '/':b'\x81\x5E',
    '~':b'\x81\x60',
    #'...':'8163', # Ellipsis
    #'\'':'8165', # Opening single quotation
    #'\'':'8166', # Closing single quotation
    #'"':'8167', # Opening double quotation
    #'"':'8168', # Closing double quotation
    '(':b'\x81\x69',
    ')':b'\x81\x6A',
    '[':b'\x81\x6D',
    ']':b'\x81\x6E',
    # '{':'816F',
    # '}':'8170',
    '{':b'',
    '}':b'', # Ignore curly brackets as they are used for control codes.
    '+':b'\x81\x7B',
    '-':b'\x81\x7C', # Minus
    '×':b'\x81\x7E', # Multiplication sign
    '÷':b'\x81\x80', 
    '=':b'\x81\x81', 
    '<':b'\x81\x83', 
    '>':b'\x81\x84', 
    '°':b'\x81\x8B', 
    '\'':b'\x81\x8C', # Arc minute symbol; can be used as apostrophe
    '$':b'\x81\x90',
    '%':b'\x81\x93',
    '#':b'\x81\x94',
    '&':b'\x81\x95',
    '*':b'\x81\x96',
    '@':b'\x81\x97',
    '☆':b'\x81\x99',
    '★':b'\x81\x9A',
    #'!?':'81AC',
    #'!!':'81AD',
    '0':b'\x82\x40',
    '1':b'\x82\x41',
    '2':b'\x82\x42',
    '3':b'\x82\x43',
    '4':b'\x82\x44',
    '5':b'\x82\x45',
    '6':b'\x82\x46',
    '7':b'\x82\x47',
    '8':b'\x82\x48',
    '9':b'\x82\x49',
    '\\':b'\x2F\x2F'
    }

    input_str = linebreak(input_str,line_id=kwargs.get("line_id",None))[0]

    output = bytearray()

    i = 0
    while i < len(input_str):
        if input_str[i] != "{":
            output += table[input_str[i]]
        else:
            # If { is encountered, parse as a control code and paste characters directly rather than translating them.
            while input_str[i+1] != "}": # Check next character and stop pasting when } is next.
                i += 1
                output += bytes(input_str[i],"shift_jis_2004")
            
        i += 1

    output += b'\x00' # Terminate string.

    return output


def linebreak(input_str,line_id=None,length_limit=30,last_line_length_limit=28,line_limit=4):
        """Break lines according to length_limit. Default length is 30.
        A backslash character is inserted at line breaks, 
        which is translated in ascii_to_sjis to byte 2F2F.
        
        Control code sequences are not counted in word length,
        assuming they consist of {} containing only letters, numbers,
        commas, and @. Because of the need for non-printable control 
        codes, the standard text wrapping functions cannot be used.
        
        Returns a tuple containing the output string and the number of 
        lines.
        """
        
        output = ""
        current_length = 0
        lines = 1
        
        # Split input string into an enumerated list of each word. Forced line breaks are split into their own word.
        input_str = list(enumerate(input_str.replace(r"\n"," \\ ").split(" "),1))

        for i in input_str:
            word_length = len(i[1]) - sum([len(p) for p in re.findall("{[a-zA-Z0-9,@]+}",i[1])]) # Do not count control code sequences in word length.

            # Insert word that is not a forced line break.
            if i[1] != "\\":
                if current_length + word_length + 1 <= length_limit:
                    output += i[1]
                    current_length += word_length + 1
                else:
                    output = output.rstrip() + "\\" + i[1]
                    lines += 1
                    current_length = word_length
                # Add a space if there are more words remaining, or break otherwise.
                if i[0] < len(input_str):
                    output += " "
                else:
                    break
            else:
                output = output.rstrip() + "\\" # Remove space inserted by previous word.
                lines += 1
                current_length = 0

        if lines == line_limit and current_length > last_line_length_limit:
            if line_id is not None:
                print(f"WARNING: Last line limit overflow at line {line_id}: {output}")
            else:
                print(f"WARNING: Last line limit overflow: {output}")

        if lines > line_limit:
            if line_id is not None:
                print(f"WARNING: Line break overflow at line {line_id}: {output}")
            else:
                print(f"WARNING: Line break overflow: {output}")

        return (output,lines)


def swap_bytes(value):
    """Convert hex string to little-endian bytes."""

    str = hex(value)[2:].zfill(8)

    return str[6:8] + str[4:6] + str[2:4] + str[0:2]    


if __name__ == "__main__":
    input_str = input("String: ")
    print(ascii_to_sjis(input_str).hex())