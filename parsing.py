#!/usr/bin/env python
#-*- coding: utf-8 -*-

import ast
import ply.yacc as yacc
import operator

from lexing import tokens

### grammar ############################################################

### prog def ###########################################################
def p_prog(p):
    '''prog : '''
    p[0] = []

def p_prog_nl(p):
    '''prog : prog NEWLINE'''
    p[0] = p[1]

def p_prog_one_expr(p):
    '''prog : expr'''
    p[0] = [p[1]]

def p_prog_many_exprs(p):
    '''prog : prog expr'''
    p[1].append(p[2])
    p[0] = p[1]

### expr def ###########################################################
def p_expr(p):
    '''expr : INTEGER
            | FLOAT
            | STRING
            | TRUE
            | FALSE
            | NULL
            | ID'''
    p[0] = p[1]

def p_expr_parens(p):
    '''expr : LPAREN expr RPAREN'''
    p[0] = p[2]

def p_expr_unary_op(p):
    '''expr : UNARY_OP expr'''
    p[1].args = (p[2],)
    p[0] = p[1]

def p_expr_unary_plus(p):
    '''expr : ADD_OP expr %prec UNARY_PLUS'''
    p[1].args = (p[2],)
    p[0] = p[1]

def p_expr_binary_op(p):
    '''expr : expr BINARY_OP expr
            | expr ADD_OP expr
            | expr MUL_OP expr
            | expr AND expr
            | expr OR expr
            | expr RANGE_OP expr
            | expr INDEX_OP expr
            | expr POW_OP expr
            | expr COMP_OP expr
            | expr EQ_OP expr
            | expr BIT_OR expr
            | expr BIT_XOR expr
            | expr BIT_AND expr
            | expr BIT_SHIFT expr'''
    p[2].args = (p[1], p[3])
    p[0] = p[2]

def p_list(p):
    '''expr : LSQUARE_BRACKET exprlist RSQUARE_BRACKET'''
    p[0] = ast.ListNode(arg=p[2])

def p_expr_assign_list(p):
    '''expr : ID LSQUARE_BRACKET expr RSQUARE_BRACKET ASSIGN_OP expr'''
    p[0] = ast.AssignListNode(p[5].fun)
    p[0].args = (p[1], p[3], p[6])

def p_expr_assign_op(p):
    '''expr : ID ASSIGN_OP expr'''
    p[2].args = (p[1], p[3])
    p[0] = p[2]

def p_expr_muli_assign(p):
    '''expr : ID COMMA idlist ASSIGN_OP expr COMMA exprlist'''
    p[4].args = ((p[1],) + p[3], (p[5],) + p[7])
    p[0] = p[4]

def p_pre_inc(p):
    '''expr : INC_OP ID '''
    p[1].pre = True
    p[1].arg = p[2]
    p[0] = p[1]

def p_post_inc(p):
    '''expr : ID INC_OP'''
    p[2].pre = False
    p[2].arg = p[1]
    p[0] = p[2]

def p_if(p):
    '''expr : IF expr COLON prog END
            | UNLESS expr COLON prog END'''
    p[1].args = (p[2], ast.RootNode(args=p[4]))
    p[0] = p[1]

def p_if_elif(p):
    '''expr : IF expr COLON prog ELSE COLON prog END
            | UNLESS expr COLON prog ELSE COLON prog END'''
    p[1].args = (p[2], ast.RootNode(args=p[4]), ast.RootNode(args=p[7]))
    p[0] = p[1]

def p_while(p):
    '''expr : WHILE expr COLON prog END
            | UNTIL expr COLON prog END'''
    p[1].args = (p[2], ast.RootNode(args=p[4]))
    p[0] = p[1]

def p_fun(p):
    '''expr : FUN ID LPAREN idlist RPAREN COLON prog END'''
    p[0] = ast.DefFunNode()
    p[0].args = (p[2], p[4], ast.RootNode(args=p[7]))

def p_fun_call(p):
    '''expr : ID LPAREN exprlist RPAREN'''
    p[0] = ast.CallFunNode()
    p[0].args = (p[1], p[3])

def p_puts(p):
    '''expr : PUTS exprlist'''
    p[1].args = p[2]
    p[0] = p[1]

### idlist def #########################################################
def p_idlist_empty(p):
    '''idlist : '''
    p[0] = ()

def p_idlist_one_arg(p):
    '''idlist : ID'''
    p[0] = (p[1],)

def p_idlist_args(p):
    '''idlist : idlist COMMA ID'''
    p[0] = p[1] + (p[3],)

### exprlist def #######################################################
def p_exprlist_empty(p):
    '''exprlist : '''
    p[0] = ()

def p_exprlist_one_arg(p):
    '''exprlist : expr'''
    p[0] = (p[1],)

def p_exprlist_args(p):
    '''exprlist : exprlist COMMA expr'''
    p[0] = p[1] + (p[3],)

### error? #############################################################
def p_error(p):
    import sys
    print('Syntax error (line #{}) : {} ({}).'.format(p.lineno, p.value,
          p.type),
          file=sys.stderr)
    sys.exit(2)

### precedence table, last elements have the higher precedence #########
precedence = (
              ('left', 'COMMA'),
              ('left', 'ASSIGN_OP'),
              ('left', 'OR'),
              ('left', 'AND'),
              ('left', 'BIT_OR'),
              ('left', 'BIT_XOR'),
              ('left', 'BIT_AND'),
              ('left', 'EQ_OP'),
              ('left', 'COMP_OP'),
              ('left', 'BIT_SHIFT'),
              ('left', 'ADD_OP'),
              ('left', 'MUL_OP'),
              ('left', 'INDEX_OP'),
              ('right', 'UNARY_PLUS', 'UNARY_OP', 'INC_OP'),
              ('left', 'RANGE_OP'),
              ('right', 'POW_OP'),
             )

yacc.yacc(outputdir='yacc_out', errorlog=yacc.NullLogger())

### parse simple source ################################################
if __name__ == '__main__':
    def showAST(res, indent=''):
        '''quick 'n' dirty'''
        if type(res) == ast.RootNode:
            print(indent, res, sep='')
            indent += ' ' * 4
            res = res.args

        for n in res:
            print(indent, n, sep='')

            if 'args' in dir(n) and n.args != None:
                showAST(n.args, indent=indent+' ' * 4)

            if 'arg' in dir(n) and n.arg != None:
                if type(n) == ast.ListNode:
                    for x in n.arg:
                        print(indent+' '*4, x, sep='')
                        if '__iter__' in dir(x.arg):
                            showAST(x.arg, indent=indent+' ' * 8)

    import sys
    with open(sys.argv[1] if len(sys.argv) == 2 else 'quicksort.cow') as f:
        result = yacc.parse(f.read())
        ast.RootNode(args=result).eval()
 
