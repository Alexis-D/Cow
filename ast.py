#!/usr/bin/env python
#-*- coding: utf-8 -*-

class Node(object):
    '''Represent a node in an ast.'''
    def __init__(self, arg=None, args=None):
        self.arg = arg
        self.args = args

    def eval(self, ctx=[]):
        raise NotImplementedError('eval should be overwritten by '
                                  'subclasses.')

    def getContext(self, ctx, key, fun=False):
        '''Return the var key in the nearest context.'''
        for c in reversed(ctx):
            if key in c:
                if fun and issubclass(type(c[key]), FunNode):
                    return c[key]
                elif not fun and not issubclass(type(c[key]), FunNode):
                    return c[key]

        raise KeyError('var {} is not declared.'.format(key))

    def setContext(self, ctx, key, value):
        '''Set the var key to value. Create it if it didn't exist
           before.'''
        for i, c in enumerate(reversed(ctx)):
            if key in c:
                ctx[len(ctx) - i - 1][key] = value
                break
        else:
            ctx[-1][key] = value

    def getArg(self):
        return self._arg

    def setArg(self, arg):
        self._arg = arg

    def getArgs(self):
        return self._args

    def setArgs(self, args):
        self._args = args

    # for single arg node
    arg = property(getArg, setArg)
    # for multiple args node
    args = property(getArgs, setArgs)

class OpNode(Node):
    '''Represent operators.'''
    def __init__(self, fun):
        super().__init__()
        self._fun = fun

    def eval(self, ctx=[]):
        '''Apply the associated fun to the args.'''
        return self._fun(*[x.eval(ctx) for x in self.args])

class AssignNode(Node):
    def __init__(self, fun=lambda a, b: b, simple=True):
        super().__init__()
        self.fun = fun
        self.simple = simple

    def eval(self, ctx=[]):
        if len(self.args) != 2:
            raise TypeError('assignement needs 2 arguments ({} given).'\
                            .format(len(self.args)))
        name, val = self.args
        
        if issubclass(type(name), IdNode):
            if self.simple:
                val = val.eval(ctx)

            else:
                val = self.fun(self.getContext(ctx, name.name),
                            val.eval(ctx))

            self.setContext(ctx, name.name, val)

        else:
            for n, e in zip(name, val):
                a = AssignNode(self.fun, self.simple)
                a.args = (n, e)
                a.eval(ctx)

        return val
    
    def getFun(self):
        return self._fun
    
    def setFun(self, fun):
        self._fun = fun

    def getSimple(self):
        return self._simple

    def setSimple(self, simple):
        self._simple = simple

    fun = property(getFun, setFun)

class AssignListNode(Node):
    def eval(self, ctx=[]):
        if len(self.args) != 3:
            raise TypeError('list assignement needs 3 arguments '
                            '({} given).'.format(len(self.args)))

        name, idx, val = self.args
        l = self.getContext(ctx, name.name)
        val = val.eval(ctx)
        l[idx.eval(ctx)] = val
        return val

class IfNode(Node):
    '''Represent a control structure.'''
    def __init__(self, if_=True):
        '''if if_ = False, work like unless'''
        super().__init__()
        self._if = if_

    def eval(self, ctx=[]):
        ctx.append({})

        if len(self.args) == 2:
            self.args += (NullNode(),)

        cond, body, otherwise = self.args
        cond = cond.eval(ctx)

        if (self._if and cond) or (not self._if and not cond):
            r = body.eval(ctx)
        else:
            r = otherwise.eval(ctx)

        ctx.pop()
        return r

class AndNode(Node):
    '''Represent and and or, not a 'normal' op, because e.g.:
       a() or b() if a() is true, b shouldn't be called.'''
    def __init__(self, and_=True):
        super().__init__()
        self._and = and_

    def eval(self, ctx=[]):
        a, b = self.args

        if self._and:
            return a.eval(ctx) and b.eval(ctx)
        else:
            return a.eval(ctx) or b.eval(ctx)

class WhileNode(Node):
    '''Represent a while loop.'''
    def __init__(self, while_=True):
        '''if while_ == False, act like until.'''
        super().__init__()
        self._while = while_

    def eval(self, ctx=[]):
        if len(self.args) != 2:
            raise TypeError('while takes 2 arguments ({} given).'\
                            .format(len(self.args)))
        ctx.append({})

        cond, body = self.args
        r = None

        if self._while:
            while cond.eval(ctx):
                r = body.eval(ctx)
        else:
            while not cond.eval(ctx):
                r = body.eval(ctx)

        ctx.pop()
        return r

class RootNode(Node):
    '''Represent a list of instruction, contains a list of expression.'''
    def eval(self, ctx=[]):
        ctx.append({})
        r = None

        for node in self.args:
            r = node.eval(ctx)

        ctx.pop()
        return r

class FunNode(Node):
    def __init__(self, name, argsnames, body):
        self.name = name
        self.argsnames = argsnames
        self._body = body

    def eval(self, oldctx=[], ctx=[], args=[]):
        ctx.append({})

        for argname, val in zip(self.argsnames, args):
            self.setContext(ctx, argname.name, val.eval(oldctx))

        r = self._body.eval(ctx)
        ctx.pop()
        return r

    def getName(self):
        return self._name

    def setName(self, name):
        self._name = name

    def getArgsName(self):
        return self._argsnames

    def setArgsName(self, argsnames):
        self._argsnames = argsnames

    name = property(getName, setName)
    argsnames = property(getArgsName, setArgsName)

class CallFunNode(Node):
    def _cleanContext(self, ctx):
        newctx = []

        for c in ctx:
            keys = {}
            for key in c:
                if issubclass(type(c[key]), FunNode):
                    keys[key] = c[key]

            newctx.append(keys)
        
        return newctx

    def eval(self, ctx):
        name, exprlist = self.args
        fun = self.getContext(ctx, name.name, fun=True)
        newctx = self._cleanContext(ctx)
        return fun.eval(ctx, newctx, exprlist) 

class DefFunNode(Node):
    def eval(self, ctx=[]):
        name, argsname, body = self.args
        self.setContext(ctx, name.name, FunNode(name.name, argsname,
                        body))

class IdNode(Node):
    '''Represent an identificator, can be a variable, or a method.'''
    def __init__(self, name):
        super().__init__()
        self.name = name

    def eval(self, ctx=[]):
        return self.getContext(ctx, self.name)

    def getName(self):
        return self._name

    def setName(self, name):
        self._name = name

    name = property(getName, setName)

class IncNode(Node):
    '''Represent ++ and --.'''
    def __init__(self, inc=True, pre=True):
        super().__init__()
        self.inc = inc
        self.pre = pre

    def eval(self, ctx=[]):
        name = self.arg.name
        val = self.getContext(ctx, name)
        nval = val + (1 if self.inc else -1)

        self.setContext(ctx, name, nval)

        if self.pre:
            return nval

        else:
            return val

    def getInc(self):
        return self._inc

    def setInc(self, inc):
        self._inc = inc

    def getPre(self):
        return self._pre

    def setPre(self, pre):
        self._pre = pre

    inc = property(getInc, setInc)
    pre = property(getPre, setPre)

class ValueNode(Node):
    '''Represent a constant/single value.'''
    def eval(self, ctx=[]):
        return self.arg

class BoolNode(ValueNode):
    pass

class IntegerNode(ValueNode):
    pass

class FloatNode(ValueNode):
    pass

class StringNode(ValueNode):
    pass

class NullNode(ValueNode):
    '''Will be set to None, see Node.__init__.'''
    pass

class ListNode(Node):
    def eval(self, ctx=[]):
        return [x.eval(ctx) for x in self.arg]

