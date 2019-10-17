from z3 import *

def BitVecVar(name, valtype):
    if "32" in valtype:
        return BitVec(name, 32)
    elif "64" in valtype:
        return BitVec(name, 64)
    else:
        raise Exception("wrong type")