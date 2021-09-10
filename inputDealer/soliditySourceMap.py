import ast
import json
import global_params
import six
import os
import logging
from inputDealer.solidiytAstHelper import AstHelper
from utils import run_command

logger = logging.getLogger(__name__)


class Source:
    def __init__(self, filename):
        self.filename = filename
        self.content = self._load_content()  # the all file content in string type
        self.line_break_positions = self._load_line_break_positions()  # the position of all "\n"

    def _load_content(self):
        with open(os.path.join(global_params.SRC_DIR, self.filename), 'r') as f:
            content = f.read()
        return content

    def _load_line_break_positions(self):
        return [i for i, letter in enumerate(self.content) if letter == '\n']


class SourceMap:
    parent_file = ""  # relative path of .sol file
    sources = {}
    position_groups = {}  # map from contract name to legacyAssembly of contract
    ast_helper = None  # AstHelper of parentfile
    func_to_sig_by_contract = {}

    def __init__(self, cname="", input_type="", parent_file="", sources=None):
        if input_type == global_params.SOLIDITY:
            SourceMap.parent_file = parent_file
            SourceMap.position_groups[cname] = sources["contracts"][parent_file][cname]['evm']['legacyAssembly']
            SourceMap.ast_helper = AstHelper(parent_file, input_type, sources["sources"])
            SourceMap.func_to_sig_by_contract[cname] = sources["contracts"][parent_file][cname]['evm']["methodIdentifiers"]

            self.cname = cname
            self.input_type = input_type
            self.source = SourceMap._get_source()
            self.sig_to_func = self._get_sig_to_func()

            SourceMap.ast_helper.set_source(self.source)

            self.instr_positions = {}
            self.positions = self._get_positions()

            self.var_names = self._get_var_names()
            self.func_call_names = self._get_func_call_names()
            self.callee_src_pairs = self._get_callee_src_pairs()
            self.func_name_to_params = self._get_func_name_to_params()
            self.sig_to_func = self._get_sig_to_func()
        else:
            raise Exception("There is no such type of input")

        return

    def _get_var_names(self):
        return SourceMap.ast_helper.extract_state_variable_names(SourceMap.parent_file+":"+self.cname)

    def _get_func_call_names(self):
        func_call_srcs = SourceMap.ast_helper.extract_func_call_srcs(SourceMap.parent_file+":"+self.cname)
        func_call_names = []
        for src in func_call_srcs:
            src = src.split(":")
            start = int(src[0])
            end = start + int(src[1])
            func_call_names.append(self.source.content[start:end])
        return func_call_names

    def _get_callee_src_pairs(self):
        return SourceMap.ast_helper.get_callee_src_pairs(SourceMap.parent_file+":"+self.cname)

    def _get_func_name_to_params(self):
        func_name_to_params = SourceMap.ast_helper.get_func_name_to_params(SourceMap.parent_file+":"+self.cname)
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

    def _get_sig_to_func(self):
        func_to_sig = SourceMap.func_to_sig_by_contract[self.cname]['hashes']
        return dict((sig, func) for func, sig in six.iteritems(func_to_sig))

    def get_source_code(self, pc):
        try:
            pos = self.instr_positions[pc]
        except Exception as err:
            logger.error(str(err))
            return ""
        begin = pos['begin']
        end = pos['end']
        return self.source.content[begin:end]

    def get_source_code_from_src(self, src):
        src = src.split(":")
        start = int(src[0])
        end = start + int(src[1])
        return self.source.content[start:end]

    def get_buggy_line(self, pc):
        try:
            pos = self.instr_positions[pc]
        except Exception as err:
            logger.error(str(err))
            return ""
        location = self.get_location(pc)
        begin = self.source.line_break_positions[location['begin']['line'] - 1] + 1
        end = pos['end']
        return self.source.content[begin:end]

    def get_buggy_line_from_src(self, src):
        pos = self._convert_src_to_pos(src)
        location = self.get_location_from_src(src)
        begin = self.source.line_break_positions[location['begin']['line'] - 1] + 1
        end = pos['end']
        return self.source.content[begin:end]

    def get_location(self, pc):
        pos = self.instr_positions[pc]
        return self._convert_offset_to_line_column(pos)

    def get_location_from_src(self, src):
        pos = self._convert_src_to_pos(src)
        return self._convert_offset_to_line_column(pos)

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

    def _convert_src_to_pos(self, src):
        pos = {}
        src = src.split(":")
        pos['begin'] = int(src[0])
        length = int(src[1])
        pos['end'] = pos['begin'] + length - 1
        return pos

    def _get_sig_to_func(self):
        func_to_sig = SourceMap.func_to_sig_by_contract[self.cname]
        return dict((sig, func) for func, sig in six.iteritems(func_to_sig))

    @classmethod
    def _get_source(cls):
        if SourceMap.parent_file not in SourceMap.sources:
            SourceMap.sources[SourceMap.parent_file] = Source(SourceMap.parent_file)
        return SourceMap.sources[SourceMap.parent_file]

    @classmethod
    def _load_position_groups_standard_json(cls):
        with open('standard_json_output', 'r') as f:
            output = f.read()
        output = json.loads(output)
        return output["contracts"]

    @classmethod
    def _load_position_groups(cls):
        if cls.allow_paths:
            cmd = "solc --combined-json asm %s %s --allow-paths %s" % (cls.remap, cls.parent_filename, cls.allow_paths)
        else:
            cmd = "solc --combined-json asm %s %s" % (cls.remap, cls.parent_filename)
        out = run_command(cmd)
        out = json.loads(out)
        return out['contracts']

    def _get_positions(self):
        try:
            if self.input_type == global_params.SOLIDITY:
                asm = SourceMap.position_groups[self.cname]['.data']['0']
            else:
                raise Exception("There is no such type of input")
            positions = asm['.code']
            while(True):
                try:
                    positions.append(None)
                    positions += asm['.data']['0']['.code']
                    asm = asm['.data']['0']
                except:
                    break
            return positions
        except Exception as err:
            logger.info("has no positions for bytecodes")
            return None

    def _convert_offset_to_line_column(self, pos):
        ret = {}
        ret['begin'] = None
        ret['end'] = None
        if pos['begin'] >= 0 and (pos['end'] - pos['begin'] + 1) >= 0:
            ret['begin'] = self._convert_from_char_pos(pos['begin'])
            ret['end'] = self._convert_from_char_pos(pos['end'])
        return ret

    def _convert_from_char_pos(self, pos):
        line = self._find_lower_bound(pos, self.source.line_break_positions)
        if self.source.line_break_positions[line] != pos:
            line += 1
        begin_col = 0 if line == 0 else self.source.line_break_positions[line - 1] + 1
        col = pos - begin_col
        return {'line': line, 'column': col}

    def _find_lower_bound(self, target, array):
        start = 0
        length = len(array)
        while length > 0:
            half = length >> 1
            middle = start + half
            if array[middle] <= target:
                length = length - 1 - half
                start = middle + 1
            else:
                length = half
        return start - 1

    def get_filename(self):
        return self.cname.split(":")[0]


