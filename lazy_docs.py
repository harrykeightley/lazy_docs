import argparse
import os
import sys
from model import *

DEFAULT_OUTPUT_FOLDER = os.getcwd() 

def main():
    parser = argparse.ArgumentParser(description="Generate docs for python file")
    parser.add_argument("file", help="The file to generate docs for.")
    parser.add_argument("-o", "--out", dest="output_folder", default=DEFAULT_OUTPUT_FOLDER,
        help="Save file containing current marking state")

    args = parser.parse_args()
    
    file = args.file
    out = args.output_folder

    # Argument error handling
    if not os.path.isdir(out):
        print("Not a valid output folder", file=sys.stderr)
        return
    
    if not file.endswith('.py'):
        print("Not a valid python file.", file=sys.stderr)
        return
    
    # Generate model of file
    transcriber = Transcriber([file])

    # Generate docs from model
    markers = {}
    f = LatexFormatter(transcriber.traverse_modules(), markers)
    f.export()

if __name__ == "__main__":
    main()