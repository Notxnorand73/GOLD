import sys
import re
import os
import tempfile

GOLD_LOGO = r"""
  .oooooo.      .oooooo.   ooooo        oooooooooo.          ooooo
 d8P'  `Y8b    d8P'  `Y8b  `888'        `888'   `Y8b         `888'
888           888      888  888          888      888         888
888           888      888  888          888      888         888
888     ooooo 888      888  888          888      888         888
`88.    .88'  `88b    d88'  888       o  888     d88'         888
 `Y8bood8P'    `Y8bood8P'  o888ooooood8 o888bood8P'          o888o
"""

def remove_comments(code):
    """Remove comments, keeping # inside strings"""
    lines = code.splitlines()
    new_lines = []
    for line in lines:
        in_str = False
        new_line = ""
        i = 0
        while i < len(line):
            if line[i] == '"' and (i == 0 or line[i-1] != '\\'):
                in_str = not in_str
            if not in_str and line[i] == '#':
                break  # comment starts
            new_line += line[i]
            i += 1
        if new_line.strip() != "":
            new_lines.append(new_line)
    return "\n".join(new_lines)

def convert_expr(expr):
    """Add .to_s to variables or numbers, skip quoted strings"""
    # Handle concatenation with '+'
    parts = re.split(r'(\+)', expr)
    for i, part in enumerate(parts):
        p = part.strip()
        if not p or p == '+':
            continue
        # Skip quoted strings
        if p.startswith('"') and p.endswith('"'):
            continue
        # Otherwise, add .to_s
        parts[i] = f"{p}.to_s"
    return "".join(parts)

def convert_line(line):
    line = line.strip()
    # writes -> puts
    if line.startswith("writes "):
        expr = line[len("writes "):].strip()
        expr = convert_expr(expr)
        return f"puts {expr}"
    # print -> print
    elif line.startswith("print "):
        expr = line[len("print "):].strip()
        return f"print {expr}"
    # var assignment -> normal Ruby assignment
    elif line.startswith("var "):
        rest = line[len("var "):].strip()
        # Replace = if missing spaces
        rest = re.sub(r"^\s*(\w+)\s*=\s*(.+)$", r"\1 = \2", rest)
        return rest
    # Simple if / elsif / else / end
    elif line.startswith("if "):
        cond = line[len("if "):].strip()
        cond = re.sub(r"\s+then$", "", cond)
        return f"if {cond}"
    elif line.startswith("elsif "):
        cond = line[len("elsif "):].strip()
        cond = re.sub(r"\s+then$", "", cond)
        return f"elsif {cond}"
    elif line.startswith("else"):
        return "else"
    elif line == "end":
        return "end"
    # while / unless / for / etc.
    elif line.startswith("while "):
        cond = line[len("while "):].strip()
        return f"while {cond}"
    elif line.startswith("unless "):
        cond = line[len("unless "):].strip()
        return f"unless {cond}"
    elif line.startswith("for "):
        m = re.match(r"for (\w+) in (.+)", line)
        if m:
            var, lst = m.groups()
            return f"{lst}.each do |{var}|"
    # Enumerate
    elif ".enumerate " in line:
        m = re.match(r"(\[.*\])\.enumerate (\w+)", line)
        if m:
            lst, var = m.groups()
            return f"{lst}.each_with_index do |item, {var}|"
    # Lambda
    elif "->" in line:
        # name -> (var)(expr)
        m = re.match(r"(\w+)\s*->\s*\((\w+)\)\((.+)\)", line)
        if m:
            name, var, expr = m.groups()
            return f"{name} = lambda {{ |{var}| {expr} }}"
    # Fallback
    return line

def gold_to_ruby(code):
    code = remove_comments(code)
    ruby_lines = []
    for line in code.splitlines():
        conv = convert_line(line)
        ruby_lines.append(conv)
    return "\n".join(ruby_lines)

def run_gold_file(filename):
    print(GOLD_LOGO)
    try:
        with open(filename, "r") as f:
            code = f.read()
        ruby_code = gold_to_ruby(code)
        # Write to temp Ruby file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".rb", mode="w", encoding="utf-8")
        tmp.write(ruby_code)
        tmp.close()
        # Execute Ruby
        os.system(f"ruby {tmp.name}")
        os.unlink(tmp.name)
    except Exception as e:
        print(f"[Gold Error] {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_gold_file(sys.argv[1])
    else:
        print("Usage: python Gold.py <file.gold>")
