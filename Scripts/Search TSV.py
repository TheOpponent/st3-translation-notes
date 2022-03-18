import sys

def main():

    with open(r'c:\Users\Normal\Documents\Scripts\st3-translation-notes\Scripts\tsv\test.tsv',encoding="utf-8") as file1, open(r'c:\Users\Normal\Documents\Scripts\st3-translation-notes\Scripts\tsv\LIPSYNC1.tsv',encoding="utf-8") as file2:
        tsv1 = file1.readlines()
        # tsv1 = ['すまないが、急いでいるので//要件は大使館の職員にでも//伝えておいていただけるかな。']
        tsv2 = file2.readlines()

    for line in tsv1:
        line = line.split("\t")[1][:-1]
        search_enumerate(line,tsv2)


def search_enumerate(str,enumerated_list):
    for text in enumerated_list:
        if str in text:
            print(f"{str}")
            return
    
    # return f"{str} not found."

if __name__ == "__main__":
    main()
