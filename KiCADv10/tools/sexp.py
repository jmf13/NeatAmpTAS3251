"""Minimal KiCad S-expression parser / writer.

Atoms are kept as Python str. Quoted strings become Q instances (a str subclass)
so they are written back quoted.
"""
import re


class Q(str):
    pass


def esc(s):
    return Q(s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n'))


_tok = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))', re.S)


def parse(text):
    stack = [[]]
    pos = 0
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == '':
                break
            raise ValueError('parse error at %d: %r' % (pos, text[pos:pos + 40]))
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            x = stack.pop()
            stack[-1].append(x)
        elif m.group(3) is not None:
            stack[-1].append(Q(m.group(3)))  # kept raw (still escaped)
        else:
            stack[-1].append(m.group(4))
    return stack[0][0]


def _atom(a):
    if isinstance(a, Q):
        return '"' + a + '"'
    if isinstance(a, float):
        s = ('%.4f' % a).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    return str(a)


def dump(x, ind=0):
    if not isinstance(x, list):
        return _atom(x)
    if all(not isinstance(c, list) for c in x):
        return '(' + ' '.join(_atom(c) for c in x) + ')'
    head = []
    i = 0
    while i < len(x) and not isinstance(x[i], list):
        head.append(_atom(x[i]))
        i += 1
    out = '(' + ' '.join(head)
    for c in x[i:]:
        out += '\n' + '\t' * (ind + 1) + dump(c, ind + 1)
    return out + '\n' + '\t' * ind + ')'


def find(x, key):
    for c in x:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None


def findall(x, key):
    return [c for c in x if isinstance(c, list) and c and c[0] == key]


def prop(sym, name):
    for p in findall(sym, 'property'):
        if p[1] == name:
            return p
    return None
