#!/usr/bin/env python
#-*- coding: utf-8 -*-

import ast
import operator as op
import ply.lex as lex
import sys

### keywords of our lang ###############################################
keywords = { x: x.upper() for x in (
             'if', 'unless', 'else',
             'while', 'until', 'fun', 'end',
             'and', 'or',
             'true', 'false', 'null',
             'puts',
           )}

keywords_node = { 'if': ast.IfNode,
                  'unless': lambda: ast.IfNode(if_=False),
                  'else': ast.RootNode,
                  'while': ast.WhileNode,
                  'until': lambda: ast.WhileNode(while_=False),
                  'and': ast.AndNode,
                  'or': lambda: ast.AndNode(and_=False),
                }

### define all tokens of our language ##################################
tokens = ( 'INC_OP', 'UNARY_OP', 'BINARY_OP', 'ADD_OP', 'MUL_OP',
           'RANGE_OP', 'POW_OP', 'COMP_OP', 'EQ_OP', 'ASSIGN_OP',
           'BIT_OR', 'BIT_XOR', 'BIT_AND', 'BIT_SHIFT',
           'COLON', 'COMMA', 'NEWLINE',
           'ID', 'INDEX_OP',
           'LPAREN', 'RPAREN', 'LSQUARE_BRACKET', 'RSQUARE_BRACKET',
           'FLOAT', 'INTEGER', 'STRING',
         ) + tuple(keywords.values())

ops = { '+': lambda *a: a[0] if len(a) == 1 else op.add(*a),
        '-': lambda *a: -a[0] if len(a) == 1 else op.sub(*a),
        '*': op.mul, '**': op.pow, '!=': op.ne, '~': op.not_,
        '%': op.mod, '/': op.truediv, '//': op.floordiv, '<': op.lt,
        '<=': op.le, '>': op.gt, '>=': op.ge, '==': op.eq,
        '&': op.and_, '^': op.xor, '|': op.or_, '<<': op.lshift,
        '>>': op.rshift, '..': lambda a, b: list(range(a, b + 1)),
        '...': lambda a, b: list(range(a, b)), 'not': op.not_,
        'in': lambda a, b: op.contains(b, a), 'puts': print,
        'not': lambda a: not a, '!!': op.getitem,
        '@': lambda a: len(a),
      }

inc_ops = { '++': ast.IncNode,
            '--': lambda: ast.IncNode(inc=False),
          }

### regex to match the tokens ##########################################
def t_ASSIGN_OP(t):
    r'=|(?:\+|-|<<|>>|\||\^|\&|\*\*?|%|//?|~)='
    if t.value == '=':
        t.value = ast.AssignNode()

    else: # last assign
        t.value = ast.AssignNode(fun=ops[t.value[:-1]], simple=False)

    return t

def t_INC_OP(t):
    r'\+\+|--'
    t.value = inc_ops[t.value]()
    return t

def t_ADD_OP(t):
    r'\+|-'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_BIT_SHIFT(t):
    r'<<|>>'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_BIT_OR(t):
    r'\|'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_BIT_XOR(t):
    r'\^'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_BIT_AND(t):
    r'\&'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_INDEX_OP(t):
    r'!!'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_COMP_OP(t):
    r'<=?|>=?'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_EQ_OP(t):
    r'==|!='
    t.value = ast.OpNode(ops[t.value])
    return t

def t_POW_OP(t):
    r'\*\*'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_MUL_OP(t):
    r'\*|%|//?'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_RANGE_OP(t):
    r'\.\.\.?'
    t.value = ast.OpNode(ops[t.value])
    return t

def t_UNARY_OP(t):
    # single ~ is unary but ~= is binary
    r'~|@'
    t.value = ast.OpNode(ops[t.value])
    return t

t_COLON = r':'
t_COMMA = r','

t_LPAREN          = r'\('
t_RPAREN          = r'\)'
t_LSQUARE_BRACKET = r'\['
t_RSQUARE_BRACKET = r'\]'

def t_ID(t):
    r'[a-zA-Z_][\w!?]*'
    t.type = keywords.get(t.value, 'ID')

    if t.value in ops:
        if t.value in ['not']: # add other unary ops in this array
            t.type = 'UNARY_OP'
        
        elif t.value in ['in']:
            t.type = 'BINARY_OP'

        t.value = ast.OpNode(ops[t.value])

    elif t.type != 'ID':
        if t.type in ['TRUE', 'FALSE']:
            t.value = ast.BoolNode(True if t.value == 'true' else False)

        elif t.type in ['NULL']:
            t.value = ast.NullNode()

        elif t.value in keywords_node:
            t.value = keywords_node[t.value]()

    else:
        t.value = ast.IdNode(t.value)

    return t

def t_INTEGER(t):
    r'0b[01]+|0o[0-7]+|0x(?:\d|[a-fA-F])+|\d+'

    if len(t.value) > 2:
        if t.value[1] == 'b':
            t.value = int(t.value, 2)
        elif t.value[1] == 'o':
            t.value = int(t.value, 8)
        elif t.value[1] == 'x':
            t.value = int(t.value, 16)
        else:
            t.value = int(t.value)
    else:
        t.value = int(t.value)

    t.value = ast.IntegerNode(arg=t.value)
    return t

def t_FLOAT(t):
    r'\d+\.\d*|\d*\.\d+'
    t.value = ast.FloatNode(arg=t.value)
    return t

def t_STRING(t):
    '''\'[^\']*\'|"[^"]*"'''
    t.value = ast.StringNode(arg=t.value[1:len(t.value) - 1])
    return t

def t_NEWLINE(t):
    r'\n+'
    t.lexer.lineno += len(t.value)
    return t

### ignored chars ######################################################
t_ignore = ' \t'
t_ignore_COMMENT = r'\#.*'

### error handling #####################################################
def t_error(t):
    print('Illegal token \'{}\' (line {}).'.format(t.value, t.lineno),
          file=sys.stderr)
    sys.exit(1)

### build the lexer ####################################################
lexer = lex.lex(errorlog=lex.NullLogger())

