import os

import six

import global_params
import log


class Source:

    def __init__(self, file_path):
        self.file_path = file_path
        self.content = self._load_content(
        )  # the all file content in string type
        self.line_break_positions = self._load_line_break_positions(
        )  # the position of all '\n'
        self.index = 0

    def _load_content(self):
        if not os.path.exists(self.file_path):
            content = ''
        else:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        return content

    def get_content(self):
        return self.content

    def is_in_source(self, i):
        return bool(i == self.index)

    def get_content_from_line(self, line):
        if line < 1 or line > len(self.line_break_positions):
            return ''
        end = self.line_break_positions[line - 1]
        if line == 1:
            start = 0
        else:
            start = self.line_break_positions[line - 2] + 1
        return self.content[start:end]

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

    def _load_line_break_positions(self):
        return [i for i, letter in enumerate(self.content) if letter == '\n']


class SourceMap:

    def __init__(self, cname, input_type, parent_file, contract_evm_info,
                 ast_helper, source):
        if input_type == global_params.LanguageType.SOLIDITY:
            self.input_type = input_type

            self.parent_file = parent_file  # absolute path of source file
            self.ast_helper = ast_helper  # ast helper of the source file
            self.source = source  # source of source file
            # the index of source file as there may be multiple
            # source files, e.g. imported files
            self.index = 0
            # contract's name, there may be multi-contracts in a source file
            self.cname = cname

            if ('deployedBytecode' in contract_evm_info) and (
                    'sourceMap' in contract_evm_info['deployedBytecode']):
                self.source_map = contract_evm_info['deployedBytecode'][
                    'sourceMap']
            else:
                log.mylogger.warning('source map is None for contract %s in %s',
                                     cname, parent_file)
                self.source_map = None
            if 'methodIdentifiers' in contract_evm_info and contract_evm_info[
                    'methodIdentifiers']:
                self.func_to_sig = contract_evm_info['methodIdentifiers']
                self.sig_to_func = self._get_sig_to_func()
            else:
                log.mylogger.warning(
                    'methodIdentifiers is None for contract %s in %s', cname,
                    parent_file)
                self.func_to_sig = None
                self.sig_to_func = None

            self.instr_positions = {}
            self.positions = self._get_positions()

            self.var_names = self._get_var_names()
            self.func_call_names = self._get_func_call_names()
            self.callee_src_pairs = self._get_callee_src_pairs()
            self.func_name_to_params = self._get_func_name_to_params()
        else:
            raise NotImplementedError('There is no such type of input')

    def get_lines_from_pc(self, pc):
        if pc not in self.instr_positions:
            return []
        position = self.instr_positions[pc]
        if position['f'] != self.index:
            return []
        return self.source.get_lines_from_position(
            position['s'], position['s'] + position['l'])

    def in_src_file(self, i):
        return bool(i == self.index)

    def get_contents_from_pc(self, pc):
        if pc not in self.instr_positions:
            return ''
        position = self.instr_positions[pc]
        if position['f'] != self.index:
            return ''
        return self.source.get_content()[position['s']:position['s'] +
                                         position['l']]

    def _get_var_names(self):
        return self.ast_helper.extract_state_variable_names(
            f'{self.parent_file}:{self.cname}')

    def _get_func_call_names(self):
        func_call_srcs = self.ast_helper.extract_func_call_srcs(
            f'{self.parent_file}:{self.cname}')
        func_call_names = []
        for src in func_call_srcs:
            src = src.split(':')
            start = int(src[0])
            end = start + int(src[1])
            func_call_names.append(self.source.content[start:end])
        return func_call_names

    def _get_callee_src_pairs(self):
        return self.ast_helper.get_callee_src_pairs(
            f'{self.parent_file}:{self.cname}')

    def _get_func_name_to_params(self):
        func_name_to_params = self.ast_helper.get_func_name_to_params(
            f'{self.parent_file}:{self.cname}')
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

    def get_filename(self):
        return self.parent_file

    def _get_sig_to_func(self):
        func_to_sig = self.func_to_sig
        return dict((sig, func) for func, sig in six.iteritems(func_to_sig))

    def _get_positions(self):
        if self.input_type == global_params.LanguageType.SOLIDITY:
            if self.source_map:
                source_map_position = self.source_map.split(';')
                # get index of source file, and it is the 'f' of first element
                if len(source_map_position[0].split(':')) >= 3:
                    self.index = int(source_map_position[0].split(':')[2])
                    self.source.index = self.index
                else:
                    log.mylogger.warning(
                        'cannot get the file index from sourcemap')

                positions = []
                p = {'s': -1, 'l': -1, 'f': -1, 'j': '-', 'm': 0}
                for x in source_map_position:
                    if x == '':
                        positions.append(p.copy())
                    else:
                        n_p = x.split(':')
                        length = len(n_p)
                        if length > 0 and n_p[0] != '':
                            p['s'] = int(n_p[0])
                        if length > 1 and n_p[1] != '':
                            p['l'] = int(n_p[1])
                        if length > 2 and n_p[2] != '':
                            p['f'] = int(n_p[2])
                        if length > 3 and n_p[3] != '':
                            p['j'] = n_p[3]
                        if length == 5 and n_p[4] != '':
                            p['m'] = int(n_p[4])
                        if length > 5:
                            raise AssertionError(
                                f'source map error for contract {self.cname}, '
                                f'file: {self.parent_file}')
                        positions.append(p.copy())
                return positions
        else:
            raise NotImplementedError(f'There is no such type of input: '
                                      f'{self.input_type}')
