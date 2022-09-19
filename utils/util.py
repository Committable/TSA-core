import os
import re
import yaml

from utils import global_params
from utils import log

from z3 import is_expr, BitVecVal, simplify, is_const, unknown


def get_project_name(project_dir):
    return str.split(project_dir, os.sep)[-1]


def remove_prefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]


def change_to_relative(path):
    if path == '':
        return path
    if path[0] == os.sep:
        return path[1:]
    return path


def get_config(config_path):
    with open(config_path, 'r', encoding='utf8') as stream:
        parsed_yaml = yaml.safe_load(stream)
        return parsed_yaml


def generate_output_dir(first, second):
    dir_name = os.path.join(global_params.DEST_PATH, first, second)
    os.makedirs(dir_name, exist_ok=True)
    return dir_name


def compare_versions(version1, version2):

    def normalize(v):
        return [int(x) for x in re.sub(r'(\.0+)*$', '', v).split('.')]

    version1 = normalize(version1)
    version2 = normalize(version2)

    return (version1 > version2) - (version1 < version2)


def intersect(list1, list2):
    for x in list2:
        if x in list1:
            return True
    else:
        return False


def to_symbolic(number, bits=256):
    if not is_expr(number):
        return BitVecVal(number, bits)
    return number


def to_real(value):
    try:
        return int(str(simplify(value)))
    except:  # pylint: disable=bare-except
        return None


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


def is_all_real(*args):
    for element in args:
        if is_expr(element):
            return False
    return True


# simplify a z3 expression if possible, and convert to int if possible
# todo: this is time-consuming, be careful to use this
def convert_result(value):
    if is_expr(value):
        value = simplify(value)
    try:
        if is_const(value):
            value = int(str(value))
    except:  # pylint: disable=bare-except
        pass
    return value


# convert result to int, if not success, return BIG_INT_256
def convert_result_to_int(value):
    if is_expr(value):
        value = simplify(value)
    else:
        return value
    try:
        if is_const(value):
            value = int(str(value))
            return value
    except:  # pylint: disable=bare-except
        pass
    return global_params.BIG_INT_256


def ceil32(x):
    return x if x % 32 == 0 else x + 32 - (x % 32)


def check_sat(solver):
    try:
        ret = solver.check()
    except:  # pylint: disable=bare-except
        log.mylogger.warning('z3 get unknown result')
        return unknown
    return ret


def turn_hex_str_to_decimal_arr(hex_string):
    result = []
    length = len(hex_string)
    for i in range(0, length, 2):
        if i + 1 < length:
            s = hex_string[i:i + 2]
        else:
            s = f'{hex_string[i:i + 1]}0'
        result.append(int(s, 16))
    return result


def get_diff(diff_file, is_before):
    diff = []
    # TODO(Chao): Make try/except block small
    try:
        with open(diff_file, 'r', encoding='utf-8') as input_file:
            differences = input_file.readlines()
        if is_before and differences is not None:
            start = False
            for i in range(0, len(differences)):
                line = differences[i]

                n = re.match(r'([\'|"]?)@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)',
                             line)
                if n:
                    start_line = int(n.group(2))
                    line_num = 0
                    start = True
                    continue
                if start:
                    m = re.match(r'\s*([\'|"]?)(\+|-|\s)(.*)', line)
                    if m and m.group(2) == '-':
                        diff.append(start_line + line_num)
                    if m and m.group(2) != '+':
                        line_num += 1
        elif differences is not None:
            start = False
            for i in range(0, len(differences)):
                line = differences[i]

                n = re.match(r'([\'|"]?)@@ -(\d+),(\d+) \+(\d+),(\d+) @@(.*)',
                             line)
                if n:
                    start_line = int(n.group(4))
                    line_num = 0
                    start = True
                    continue
                if start:
                    m = re.match(r'\s*([\'|"]?)(\+|-|\s)(.*)', line)
                    if m and m.group(2) == '+':
                        diff.append(start_line + line_num)
                    if m and m.group(2) != '-':
                        line_num += 1
    except Exception as err:  # pylint: disable=broad-except
        log.mylogger.error('get diff fail: %s', str(err))
        return []
    return diff