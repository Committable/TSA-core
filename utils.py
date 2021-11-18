import shlex
import subprocess
import os
import re
import six
from z3 import is_expr, BitVecVal, simplify, BitVecNumRef, FPNumRef, BitVecRef, sat, unsat, If


def run_command(cmd):
    FNULL = open(os.devnull, 'w')
    solc_p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=FNULL)
    return solc_p.communicate()[0].decode('utf-8', 'strict')


def run_command_with_err(cmd):
    FNULL = open(os.devnull, 'w')
    solc_p = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = solc_p.communicate()
    out = out.decode('utf-8', 'strict')
    err = err.decode('utf-8', 'strict')
    return out, err


def compare_versions(version1, version2):
    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split(".")]

    version1 = normalize(version1)
    version2 = normalize(version2)

    return (version1 > version2) - (version1 < version2)


def custom_deepcopy(input_dict):
    output = {}
    for key in input_dict:
        if isinstance(input_dict[key], list):
            output[key] = list(input_dict[key])
        elif isinstance(input_dict[key], dict):
            output[key] = custom_deepcopy(input_dict[key])
        else:
            output[key] = input_dict[key]
    return output


# simplify a expression if possible
def convert_result(value):
    value = simplify(value) if is_expr(value) else value
    try:
        value = int(str(value))
    except:
        pass
    return value


def is_bit_vec(value):
    return isinstance(value, BitVecRef) or isinstance(value, BitVecNumRef)


def is_decidable(value):
    return not (isinstance(value, six.integer_types)
                or isinstance(value, float)
                or isinstance(value, BitVecNumRef)
                or isinstance(value, FPNumRef))


def is_all_real(*args):
    for element in args:
        if is_expr(element):
            return False
    return True


def to_unsigned(number):
    if number < 0:
        return number + 2 ** 256
    return number


def to_symbolic(number, bits=256):
    if not is_expr(number):
        return BitVecVal(number, bits)
    return number


# if it's sat return True, else(i.e unsat\unknown\timeoutError) False
# todo: check the difference of unsat\unknow\timeoutError
def check_sat(solver):
    if solver.getHasTimeOut():
        return False
    try:
        if solver.check() == sat:
            return True
    except Exception:
        return False


# if it's unsat return True, else(i.e sat\unknown\timeoutError) False
def check_unsat(solver):
    if solver.getHasTimeOut():
        return False
    try:
        if solver.check() == unsat:
            return True
    except Exception:
        solver.setHasTimeOut(True)
        return False


def to_signed(number):
    if number >= 2 ** 255:
        return (2 ** 256 - number) * (-1)
    else:
        return number


def ceil32(x):
    return x if x % 32 == 0 else x + 32 - (x % 32)


def from_bool_to_bit_vec(value):
    return simplify(If(value, BitVecVal(1, 32), BitVecVal(0, 32)))

def isSymbolic():
    pass

def isBitVec():
    pass

def isDecisiable():
    pass

def isAllReal():
    pass

def from_bool_to_BitVec():
    pass