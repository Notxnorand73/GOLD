import sys
import re

# ---------------- Lexer ----------------
class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value
    def __repr__(self):
        return f"Token({self.type!r},{self.value!r})"

def lex(code):
    token_spec = [
        ('FLOAT',  r'\d+\.\d+'),
        ('INT',    r'\d+'),
        ('STRING', r'"([^"\\]|\\.)*"'),
        ('ID',     r'[A-Za-z_@][A-Za-z0-9_]*'),
        ('OP',     r'\+\+|--|\*\*|==|!=|<=|>=|&&|\|\||[=+\-*/%<>()\[\].]'),
        ('NEWLINE',r'\n'),
        ('SKIP',   r'[ \t]+'),
        ('MISMATCH', r'.'),
    ]
    tok_regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in token_spec)
    get_token = re.compile(tok_regex).match
    pos = 0
    tokens = []
    while pos < len(code):
        mo = get_token(code,pos)
        if not mo: break
        kind = mo.lastgroup
        value = mo.group()
        if kind=='NEWLINE' or kind=='SKIP': pass
        elif kind=='MISMATCH': raise RuntimeError(f'Unexpected: {value}')
        else: tokens.append(Token(kind,value))
        pos = mo.end()
    tokens.append(Token('EOF',''))
    return tokens

# ---------------- Parser ----------------
class Parser:
    def __init__(self,tokens):
        self.tokens = tokens
        self.pos = 0
        self.cur = tokens[0]
    def _advance(self):
        self.pos += 1
        if self.pos<len(self.tokens): self.cur=self.tokens[self.pos]
        else: self.cur=Token('EOF','')
    def _eat(self,type_,val=None):
        t = self.cur
        if t.type != type_ or (val and t.value != val):
            raise SyntaxError(f"Expected {type_} {val}, got {t.type} {t.value}")
        self._advance()
        return t
    def parse_expr(self):
        t = self.cur
        if t.type in ('INT','FLOAT'):
            self._advance(); return ('num',float(t.value) if '.' in t.value else int(t.value))
        elif t.type=='STRING':
            self._advance(); return ('str', t.value[1:-1])
        elif t.type=='ID':
            self._advance(); return ('var', t.value)
        elif t.type=='OP' and t.value=='(':
            self._advance(); node=self.parse_expr(); self._eat('OP',')'); return node
        else: raise SyntaxError(f"Unexpected token: {t.type}, value: {t.value}")
    def parse_block(self):
        stmts=[]
        while self.cur.type!='EOF' and not (self.cur.type=='ID' and self.cur.value.lower()=='end'):
            stmt=self.parse_stmt()
            if stmt: stmts.append(stmt)
            else: self._advance()
        if self.cur.type=='ID' and self.cur.value.lower()=='end': self._advance()
        return ('block', stmts)
    def parse_stmt(self):
        stmt=None
        if self.cur.type=='ID':
            val = self.cur.value.lower()
            if val=='var':
                self._advance()
                name=self._eat('ID').value
                expr=None
                if self.cur.type=='OP' and self.cur.value=='=':
                    self._advance()
                    expr=self.parse_expr()
                stmt=('var',name,expr)
            elif val=='writes' or val=='print':
                cmd = val
                self._advance()
                args=[]
                while self.cur.type in ('STRING','INT','FLOAT','ID'):
                    args.append(self.parse_expr())
                stmt=(cmd,args)
            elif val=='while':
                self._advance()
                self._eat('OP','(')
                cond=self.parse_expr()
                self._eat('OP',')')
                blk=self.parse_block()
                stmt=('while',cond,blk)
            elif val=='if':
                self._advance()
                self._eat('OP','(')
                cond=self.parse_expr()
                self._eat('OP',')')
                blk=self.parse_block()
                stmt=('if',cond,blk)
        return stmt

# ---------------- Evaluator ----------------
class Evaluator:
    def __init__(self, env=None):
        self.env = {} if env is None else env
    def get(self,name):
        return self.env.get(name,None)
    def eval_expr(self,node):
        try:
            if node[0]=='num' or node[0]=='str': return node[1]
            elif node[0]=='var': return self.get(node[1])
        except Exception as e:
            print(f"[Gold Error] {e}")
            return None
    def eval_stmt(self,s):
        try:
            if s[0]=='var':
                val = self.eval_expr(s[2]) if s[2] else None
                self.env[s[1]] = val
            elif s[0]=='writes':
                vals = [self.eval_expr(a) for a in s[1]]
                print(*vals)
            elif s[0]=='print':
                vals = [self.eval_expr(a) for a in s[1]]
                print(*vals,end='')
            elif s[0]=='while':
                max_iter=1000; count=0
                while self.eval_expr(s[1]):
                    self.eval_block(s[2])
                    count+=1
                    if count>=max_iter:
                        raise RuntimeError("Infinite loop detected")
            elif s[0]=='if':
                if self.eval_expr(s[1]):
                    self.eval_block(s[2])
        except Exception as e:
            print(f"[Gold Error] {e}")
    def eval_block(self,b):
        for stmt in b[1]:
            self.eval_stmt(stmt)

# ---------------- REPL / Script ----------------
def repl():
    print('  .oooooo.      .oooooo.   ooooo        oooooooooo.          ooooo')
    print(" d8P'  `Y8b    d8P'  `Y8b  `888'        `888'   `Y8b         `888'")
    print("888           888      888  888          888      888         888")
    print("888           888      888  888          888      888         888")
    print("888     ooooo 888      888  888          888      888         888")
    print("`88.    .88'  `88b    d88'  888       o  888     d88'         888")
    print(" `Y8bood8P'    `Y8bood8P'  o888ooooood8 o888bood8P'          o888o")
    print('Gold REPL — type "exit" to quit')
    env=Evaluator()
    while True:
        try: line=input('> ')
        except EOFError: break
        if line.strip()=='exit': break
        try:
            tokens=lex(line)
            parser=Parser(tokens)
            stmt=parser.parse_stmt()
            if stmt: env.eval_block(('block',[stmt]))
        except Exception as e:
            print(f"[Gold Error] {e}")

def run_file(filename):
    try:
        with open(filename,'r') as f:
            code=f.read()
        # remove comments (ignore # inside strings)
        code = re.sub(r'(?<!")#.*','',code)
        tokens=lex(code)
        parser=Parser(tokens)
        env=Evaluator()
        stmts=[]
        while parser.cur.type!='EOF':
            stmt=parser.parse_stmt()
            if stmt: stmts.append(stmt)
            else: parser._advance()
        env.eval_block(('block',stmts))
    except Exception as e:
        print(f"[Gold Error] {e}")

if __name__=='__main__':
    if len(sys.argv)>1: run_file(sys.argv[1])
    else: repl()
