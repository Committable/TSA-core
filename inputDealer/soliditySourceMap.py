import ast
import global_params
import six
import os
import logging

from inputDealer.solidiytAstHelper import AstHelper

logger = logging.getLogger(__name__)


class Source:
    def __init__(self, filename, index):
        self.index = index
        self.filename = filename
        self.content = self._load_content()  # the all file content in string type
        self.line_break_positions = self._load_line_break_positions()  # the position of all "\n"

    def _load_content(self):
        with open(os.path.join(global_params.SRC_DIR, self.filename), 'r') as f:
            content = f.read()
        return content

    def get_content(self):
        return self.content

    def _load_line_break_positions(self):
        return [i for i, letter in enumerate(self.content) if letter == '\n']

    def get_lines_from_position(self, start, end):  # [start,end)
        lines = []
        last = 0
        for n in range(0, len(self.line_break_positions)):
            if start < self.line_break_positions[n] and end > last:
                lines.append(n + 1)
            if end < self.line_break_positions[n]:
                break
            last = self.line_break_positions[n]

        return lines


class SourceMap:
    index_to_filename = {}
    sources = {}
    ast_helper = None  # AstHelper for all

    def __init__(self, cname="", input_type="", parent_file="", sources=None):
        if input_type == global_params.SOLIDITY:
            index = int(sources["sources"][parent_file][global_params.AST]["src"].split(":")[-1])
            SourceMap.index_to_filename[index] = parent_file

            if not SourceMap.ast_helper:
                SourceMap.ast_helper = AstHelper(input_type, sources["sources"])

            if 'legacyAssembly' in sources["contracts"][parent_file][cname]['evm']:
                self.position_groups = sources["contracts"][parent_file][cname]['evm']['legacyAssembly']
            else:
                self.positions_groups = None
            self.source_map = sources["contracts"][parent_file][cname]['evm']['deployedBytecode']['sourceMap']
            if "methodIdentifiers" in sources["contracts"][parent_file][cname]['evm']:
                self.func_to_sig = sources["contracts"][parent_file][cname]['evm']["methodIdentifiers"]
                self.sig_to_func = self._get_sig_to_func()
            else:
                self.func_to_sig = None
                self.sig_to_func = None

            self.parent_file = parent_file
            self.cname = cname
            self.input_type = input_type

            self.source = self._get_source(index)

            SourceMap.ast_helper.set_source(parent_file, self.source)

            self.instr_positions = {}
            self.positions = self._get_positions()

            self.var_names = self._get_var_names()
            self.func_call_names = self._get_func_call_names()
            self.callee_src_pairs = self._get_callee_src_pairs()
            self.func_name_to_params = self._get_func_name_to_params()
        else:
            raise Exception("There is no such type of input")

        return

    def _get_var_names(self):
        return self.ast_helper.extract_state_variable_names(self.parent_file+":"+self.cname)

    def _get_func_call_names(self):
        func_call_srcs = SourceMap.ast_helper.extract_func_call_srcs(self.parent_file+":"+self.cname)
        func_call_names = []
        for src in func_call_srcs:
            src = src.split(":")
            start = int(src[0])
            end = start + int(src[1])
            func_call_names.append(self.source.content[start:end])
        return func_call_names

    def _get_callee_src_pairs(self):
        return SourceMap.ast_helper.get_callee_src_pairs(self.parent_file+":"+self.cname)

    def _get_func_name_to_params(self):
        func_name_to_params = SourceMap.ast_helper.get_func_name_to_params(self.parent_file+":"+self.cname)
        if func_name_to_params:
            for func_name in func_name_to_params:
                calldataload_position = 0
                for param in func_name_to_params[func_name]:
                    if param['type'] == 'ArrayTypeName':
                        param['position'] = calldataload_position
                        calldataload_position += param['value']
                    else:
                        param['position'] = calldataload_position
                        calldataload_position += 1
        return func_name_to_params

    def get_parameter_or_state_var(self, var_name):
        try:
            names = [
                node.id for node in ast.walk(ast.parse(var_name))
                if isinstance(node, ast.Name)
            ]
            if names[0] in self.var_names:
                return var_name
        except:
            return None
        return None

    def _get_sig_to_func(self):
        func_to_sig = self.func_to_sig
        return dict((sig, func) for func, sig in six.iteritems(func_to_sig))

    def _get_source(self, index):
        if self.parent_file not in SourceMap.sources:
            SourceMap.sources[self.parent_file] = Source(self.parent_file, index)
        return SourceMap.sources[self.parent_file]

    def _get_positions(self):
        if self.input_type == global_params.SOLIDITY:
            source_map_position = self.source_map.split(";")
            new_positions = []
            p = {"s": -1, "l": -1, "f": -1, "j": "-", "m": 0}
            for x in source_map_position:
                if x == "":
                    new_positions.append(p.copy())
                else:
                    n_p = x.split(":")
                    length = len(n_p)
                    if length > 0 and n_p[0] != "":
                        p["s"] = int(n_p[0])
                    if length > 1 and n_p[1] != "":
                        p["l"] = int(n_p[1])
                    if length > 2 and n_p[2] != "":
                        p["f"] = int(n_p[2])
                    if length > 3 and n_p[3] != "":
                        p["j"] = n_p[3]
                    if length == 5 and n_p[4] != "":
                        p["m"] = int(n_p[4])
                    if length > 5:
                        raise Exception("source map error")
                    new_positions.append(p.copy())
        else:
            raise Exception("There is no such type of input")
        return new_positions

    def get_filename(self):
        return self.parent_file


