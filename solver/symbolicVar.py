from z3 import *
from z3.z3util import *

def produce_symbolic_var(name, valtype):
    if "i32" == valtype:
        return BitVec(name, 32)
    elif "i64" == valtype:
        return BitVec((name, 64))
    elif "f64" == valtype:
        return FP(name,Float32())
    elif "f32" == valtype:
        return FP(name, Float64())
    else:
        raise Exception("wrong type")


# roughly compare expr1 and expr2, if expr1 is the subexpression of expr2 return exp2 - expr1, else return None
# we simply expect that if expr1 is the subexpression of expr2, then (expr2 - expr1) doesn't contains any vars in expr1
def subexpression(expr1, expr2):
    assert is_expr(expr1)
    assert is_expr(expr2)

    expr3 = simplify(expr2 - expr1)
    vars3 = get_vars(expr3)
    vars1 = get_vars(expr1)

    for var in vars3:
        if var in vars1:
            return None

    return expr3


