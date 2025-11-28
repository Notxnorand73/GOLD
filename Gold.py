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

        # Convert Gold lambda: name -> (var)(expr) -> Ruby: name = ->(var) { expr }
        line = re.sub(r'(\w+)\s*->\s*\((.*?)\)\((.*?)\)', r'\1 = ->(\2) { \3 }', line)

        # Replace writes with puts
        line = re.sub(r'^writes\s+', 'puts ', line)

        # Replace print with print (no newline)
        line = re.sub(r'^print\s+', 'print ', line)

        # Replace .append(x) with << x
        line = re.sub(r'\.append\((.*?)\)', r' << \1', line)

        # Replace .pop() with .pop
        line = re.sub(r'\.pop\(\)', r'.pop', line)

        # Replace .replace({...}) with merge!({...})
        line = re.sub(r'\.replace\((.*?)\)', r'.merge!(\1)', line)

        # Replace .length with .length
        # .keys, .values, .upcase, .downcase, etc. are Ruby compatible already
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
