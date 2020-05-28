import shlex
import subprocess
import json
import mmap
import os
import errno
import signal
import csv
import re
import difflib
import six
import logging

from z3 import *
from solver.symbolicVar import *


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
        return [int(x) for x in re.sub(r'(\.0+)*$','', v).split(".")]
    version1 = normalize(version1)
    version2 = normalize(version2)

    return (version1 > version2) - (version1 < version2)

def custom_deepcopy(input):
    output = {}
    for key in input:
        if isinstance(input[key], list):
            output[key] = list(input[key])
        elif isinstance(input[key], dict):
            output[key] = custom_deepcopy(input[key])
        else:
            output[key] = input[key]
    return output


def isReal(value):
    return isinstance(value, six.integer_types) or isinstance(value, float)


def isSymbolic(value):
    return not (isinstance(value, six.integer_types) or isinstance(value, float))


# simplify a expression if possible and convert a z3 type to int if possible
def convertResult(value):
    value = simplify(value) if is_expr(value) else value
    try:
        value = int(str(value))
    except Exception:
        pass
    return value


def isBitVec(value):
    return isinstance(value, z3.BitVec) or isinstance(value, z3.BitVecNumRef)

def isDecisiable(value):
    return not (isinstance(value, six.integer_types) or isinstance(value, float) or isinstance(value, z3.BitVecNumRef) or isinstance(value, z3.FPNumRef))

def isAllReal(*args):
    for element in args:
        if isSymbolic(element):
            return False
    return True

def to_unsigned(number):
    if number < 0:
        return number + 2**256
    return number

def to_symbolic(number, bits=256):
    if isReal(number):
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
        return False


def to_signed(number):
    if number >= 2**255:
        return (2**256 - number) * (-1)
    else:
        return number

def ceil32(x):
    return x if x % 32 == 0 else x + 32 - (x % 32)

def from_bool_to_BitVec(value):
    return simplify(If(value, BitVecVal(1, 32), BitVecVal(0, 32)))