#!/usr/bin/env python3
import sys
import re

def prune_prompt(content: str) -> str:
    # Remove markdown comments <!-- ... -->
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    # Strip trailing whitespace on each line
    lines = content.splitlines()
    lines = [line.rstrip() for line in lines]
    # Collapse multiple blank lines to a single blank line
    result = []
    prev_blank = False
    for line in lines:
        is_blank = line.strip() == ''
        if is_blank and prev_blank:
            continue
        prev_blank = is_blank
        result.append(line)
    return '\n'.join(result)

def main():
    input_text = sys.stdin.read()
    output = prune_prompt(input_text)
    sys.stdout.write(output)

if __name__ == '__main__':
    main()