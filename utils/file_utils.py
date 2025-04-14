import fileinput
import sys


# Remove a specific line in a file:
def remove_line_in_file(file_name, ln):
    for line_number, line in enumerate(fileinput.input(file_name, inplace=1, backup=".backup")):
        if line_number != ln:
            sys.stdout.write(line)
    fileinput.close()
