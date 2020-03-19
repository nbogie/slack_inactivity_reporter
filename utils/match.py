
import re

all_users_lines = []

with open('allusers_applicants.csv') as f:
    all_users_lines = f.read().splitlines()


def printUserLinesFor(firstName):
    for line in all_users_lines:
        if re.search(firstName, line, re.IGNORECASE):
            print("Match: " + firstName + " : " + line)


with open('real_names.txt') as f:
    lines = f.read().splitlines()
    for line in lines:
        first = line.split()[0]
        printUserLinesFor(first)
