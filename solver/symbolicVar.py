from z3 import *

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

