import os
import re
import sys

def preprocess_gold(code):
    lines = code.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue  # skip comments and blank lines

        # Remove 'var' keyword
        line = re.sub(r'^\s*var\s+', '', line)

        # Convert Gold lambda: name -> (var)(expr) -> Ruby lambda
        line = re.sub(r'(\w+)\s*->\s*\((.*?)\)\((.*?)\)', r'\1 = ->(\2) { \3 }', line)

        # Replace writes with puts
        match = re.match(r'^\s*writes\s+(.+)', line)
        if match:
            expr = match.group(1)
            expr = re.sub(r'(\b\w+\b)(?=[^a-zA-Z0-9_]*[+-/*]?)', r'\1.to_s', expr)
            line = f'puts {expr}'

        # Replace print with Ruby print
        line = re.sub(r'^print\s+', 'print ', line)

        # Replace control structures
        line = re.sub(r'\bif (.+?) then\b', r'if \1', line)
        line = re.sub(r'\belsif (.+?) then\b', r'elsif \1', line)
        line = re.sub(r'\belse then\b', r'else', line)
        line = re.sub(r'\bwhile (.+)', r'while \1', line)
        line = re.sub(r'\bunless (.+)', r'unless \1', line)
        line = re.sub(r'\bfor (\w+) in (.+)', r'for \1 in \2', line)

        # Convert .enumerate
        m = re.match(r'^\s*(\[.*\])\.enumerate (\w+)', line)
        if m:
            arr = m.group(1)
            var = m.group(2)
            line = f'{arr}.each_with_index do |{var}, index|'

        # Replace end if not part of Ruby syntax already
        if stripped == 'end':
            line = 'end'

        result.append(line)

    return "\n".join(result)

def run_gold_file(filename):
    try:
        with open(filename, 'r') as f:
            code = f.read()

        ruby_code = preprocess_gold(code)

        # Write to temporary Ruby file
        tmp_file = "tmp_gold.rb"
        with open(tmp_file, 'w') as f:
            f.write(ruby_code)

        # Run Ruby
        os.system(f"ruby {tmp_file}")

        # Optional: remove temporary file
        # os.remove(tmp_file)

    except Exception as e:
        print(f"[Gold Error] {e}")
def splash():
    print(r"""
  .oooooo.      .oooooo.   ooooo        oooooooooo.          ooooo
 d8P'  `Y8b    d8P'  `Y8b  `888'        `888'   `Y8b         `888'
888           888      888  888          888      888         888
888           888      888  888          888      888         888
888     ooooo 888      888  888          888      888         888
`88.    .88'  `88b    d88'  888       o  888     d88'         888
 `Y8bood8P'    `Y8bood8P'  o888ooooood8 o888bood8P'          o888o
""")
if __name__ == "__main__":
    splash()
    if len(sys.argv) > 1:
        run_gold_file(sys.argv[1])
    else:
        print("Usage: python gold_interpreter.py <file.gold>")
