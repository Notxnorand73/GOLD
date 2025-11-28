import re, sys

# ---------------- Lexer ----------------
class Token:
    def __init__(self, type, value):
        self.type = type
        self.value = value
    def __repr__(self):
        return f"Token({self.type},{self.value})"

def lex(code):
    # Remove comments outside strings
    def remove_comments(line):
        in_str = False
        result = ''
        i = 0
        while i < len(line):
            c = line[i]
            if c == '"' and (i==0 or line[i-1] != '\\'):
                in_str = not in_str
            if c == '#' and not in_str:
                break
            result += c
            i += 1
        return result

    lines = code.splitlines()
    code = '\n'.join(remove_comments(l) for l in lines)

    token_spec = [
        ('FLOAT', r'\d+\.\d+'),
        ('INT',   r'\d+'),
        ('STRING', r'"(\\.|[^"])*"'),
        ('ID', r'[A-Za-z_@]\w*'),
        ('OP', r'==|!=|<=|>=|<|>|\+|\-|\*|\/|%|\*\*|=|\(|\)|,|\.'),
        ('NEWLINE', r'\n'),
        ('SKIP', r'[ \t]+'),
        ('MISMATCH', r'.')
    ]
    tok_regex = '|'.join(f'(?P<{name}>{regex})' for name,regex in token_spec)
    tokens = []
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        if kind in ('SKIP','NEWLINE'): continue
        elif kind=='MISMATCH': raise RuntimeError(f'Unexpected: {value}')
        else: tokens.append(Token(kind,value))
    tokens.append(Token('EOF',''))
    return tokens

# ---------------- Parser ----------------
class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.cur = tokens[0]

    def _advance(self):
        self.pos += 1
        if self.pos < len(self.tokens):
            self.cur = self.tokens[self.pos]
        else:
            self.cur = Token('EOF','')

    def _eat(self, type, value=None):
        if self.cur.type != type or (value is not None and self.cur.value != value):
            raise SyntaxError(f'Expected {type} {value}, got {self.cur.type} {self.cur.value}')
        val = self.cur
        self._advance()
        return val

    def parse_block(self):
        stmts=[]
        while self.cur.type!='EOF' and not (self.cur.type=='ID' and self.cur.value.lower()=='end'):
            stmt=self.parse_stmt()
            if stmt: stmts.append(stmt)
            else: self._advance()
        if self.cur.type=='ID' and self.cur.value.lower()=='end': self._advance()
        return ('block',stmts)

    def parse_stmt(self):
        stmt = None
        if self.cur.type=='ID':
            val = self.cur.value.lower()
            if val=='var':
                self._advance()
                name = self._eat('ID').value
                expr = None
                if self.cur.type=='OP' and self.cur.value=='=':
                    self._advance()
                    expr = self.parse_expr()
                stmt = ('var', name, expr)
            elif val=='writes' or val=='print':
                self._advance()
                args = []
                while self.cur.type in ('ID','INT','FLOAT','STRING'):
                    args.append(self.parse_expr())
                stmt = (val, args)
            elif val=='if':
                self._advance()
                self._eat('OP','(')
                cond = self.parse_expr()
                self._eat('OP',')')
                blk = self.parse_block()
                stmt = ('if', cond, blk, None)
            elif val=='while':
                self._advance()
                self._eat('OP','(')
                cond = self.parse_expr()
                self._eat('OP',')')
                blk = self.parse_block()
                stmt = ('while', cond, blk)
            elif val=='[':  # possible list.enumerate
                # parse list literal
                self._advance()  # skip '['
                items = []
                while self.cur.type != 'OP' or self.cur.value != ']':
                    items.append(self.parse_expr())
                    if self.cur.type=='OP' and self.cur.value==',':
                        self._advance()
                self._eat('OP',']')
                # check for .enumerate
                if self.cur.type=='OP' and self.cur.value=='.':
                    self._advance()
                    if self.cur.type=='ID' and self.cur.value.lower()=='enumerate':
                        self._advance()
                        var_name = self._eat('ID').value
                        blk = self.parse_block()
                        stmt = ('enumerate', items, var_name, blk)
            else:
                # function calls
                name = self._eat('ID').value
                args = []
                while self.cur.type in ('ID','INT','FLOAT','STRING'):
                    args.append(self.parse_expr())
                stmt = ('call_stmt', name, args)
        return stmt

    # ---------------- Expressions ----------------
    def parse_expr(self, min_prec=0):
        t = self.cur
        if t.type=='OP' and t.value=='(':
            self._advance()
            lhs = self.parse_expr()
            self._eat('OP',')')
        elif t.type in ('INT','FLOAT','STRING','ID'):
            lhs = ('var' if t.type=='ID' else t.type.lower(), t.value)
            self._advance()
        else:
            raise SyntaxError(f'Unexpected token: {t.type}, value: {t.value}')

        while self.cur.type=='OP' and self.get_precedence(self.cur.value)>=min_prec:
            op = self.cur.value
            op_prec = self.get_precedence(op)
            self._advance()
            rhs = self.parse_expr(op_prec+1)
            lhs = ('binop', op, lhs, rhs)
        return lhs

    def get_precedence(self, op):
        prec={'||':1,'&&':2,'==':3,'!=':3,'<':3,'<=':3,'>':3,'>=':3,'+':4,'-':4,'*':5,'/':5,'%':5,'**':6}
        return prec.get(op,-1)

# ---------------- Evaluator ----------------
class Evaluator:
    def __init__(self):
        self.env = {}

    def eval_block(self, block):
        _, stmts = block
        for s in stmts:
            self.eval_stmt(s)

    def eval_stmt(self, s):
        try:
            if s[0]=='var':
                val = self.eval_expr(s[2]) if s[2] else None
                self.env[s[1]] = val
            elif s[0]=='writes':
                vals = [self.eval_expr(a) for a in s[1]]
                print(*vals)
            elif s[0]=='print':
                vals = [self.eval_expr(a) for a in s[1]]
                print(*vals, end='')
            elif s[0]=='if':
                cond = self.eval_expr(s[1])
                if cond: self.eval_block(s[2])
            elif s[0]=='while':
                count = 0
                max_iter = 1000
                while self.eval_expr(s[1]):
                    self.eval_block(s[2])
                    count += 1
                    if count>=max_iter:
                        raise RuntimeError("Infinite loop detected")
            elif s[0]=='call_stmt':
                # placeholder for functions
                pass
        except Exception as e:
            print(f"[Gold Error] {e}")

    def eval_expr(self, node):
        if node is None: return None
        t = node[0]
        if t=='int': return int(node[1])
        elif t=='float': return float(node[1])
        elif t=='string': return node[1][1:-1]
        elif t=='var':
            if node[1] in self.env: return self.env[node[1]]
            else: raise NameError(node[1])
        elif t=='binop':
            l = self.eval_expr(node[2])
            r = self.eval_expr(node[3])
            op = node[1]
            if op=='+': return str(l)+str(r) if isinstance(l,str) or isinstance(r,str) else l+r
            if op=='-': return l-r
            if op=='*': return l*r
            if op=='/': return l//r
            if op=='%': return l%r
            if op=='**': return l**r
            if op=='<': return l<r
            if op=='<=': return l<=r
            if op=='>': return l>r
            if op=='>=': return l>=r
            if op=='==': return l==r
            if op=='!=': return l!=r
            if op=='&&': return l and r
            if op=='||': return l or r

# ---------------- REPL / Script ----------------
def repl():
    print("""  
  .oooooo.      .oooooo.   ooooo        oooooooooo.          ooooo
 d8P'  `Y8b    d8P'  `Y8b  `888'        `888'   `Y8b         `888'
888           888      888  888          888      888         888
888           888      888  888          888      888         888
888     ooooo 888      888  888          888      888         888
`88.    .88'  `88b    d88'  888       o  888     d88'         888
 `Y8bood8P'    `Y8bood8P'  o888ooooood8 o888bood8P'          o888o
""")
    env = Evaluator()
    while True:
        try:
            line = input('> ')
            if line.strip()=='exit': break
            tokens = lex(line)
            parser = Parser(tokens)
            stmt = parser.parse_stmt()
            if stmt: env.eval_block(('block',[stmt]))
        except Exception as e:
            print(f"[Gold Error] {e}")
    print("=== Exiting Gold Interpreter ===")

def run_file(filename):
    try:
        with open(filename,'r') as f:
            code = f.read()
        tokens = lex(code)
        parser = Parser(tokens)
        env = Evaluator()
        stmts=[]
        while parser.cur.type!='EOF':
            stmt = parser.parse_stmt()
            if stmt: stmts.append(stmt)
            else: parser._advance()
        env.eval_block(('block',stmts))
    except Exception as e:
        print(f"[Gold Error] {e}")

# ---------------- Entry Point ----------------
if __name__=='__main__':
    try:
        if len(sys.argv)>1:
            run_file(sys.argv[1])
        else:
            repl()
    except KeyboardInterrupt:
        print("\n=== Exiting Gold Interpreter ===")
