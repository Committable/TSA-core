import os
import sys

import graphviz
import six

from runtime import basic_block
from utils import util, global_params, log


class EvmRuntime:
    terminal_opcode = {
        'STOP', 'RETURN', 'SUICIDE', 'REVERT', 'ASSERTFAIL', 'INVALID'
    }
    jump_opcode = {'JUMP', 'JUMPI'}
    block_jump_types = {'terminal', 'conditional', 'unconditional', 'falls_to'}

    def __init__(self,
                 context,
                 platform=None,
                 opcodes=None,
                 source_map=None,
                 src_file=None,
                 input_type=None,
                 binary=None):
        self.context = context
        # disassemble file of contract in string like
        # 'PUSH1 0x55 PUSH1 0x23 PUSH1 0xB'
        self.opcodes = opcodes
        # SourceMap class of solidity of the contract
        self.source_map = source_map
        # specified blockchain platform, eg. ethereum, xuper-chain,
        # fisco-bcos, for specific analysis
        self.platform = platform
        self.src_file = src_file  # complete path of solidity file
        # input file defined in file global_params.py and assigned in cmd
        self.input_type = input_type
        self.binary = binary  # runtime evm bytes of the contract

        self.start_block_to_func_sig = {}

    def build_cfg(self):
        if self.input_type == global_params.LanguageType.SOLIDITY:
            # 1. transfer from token string to
            tokens = self.opcodes.split(' ')
            file_contents = []
            content = []
            pc = 0
            for token in tokens:
                if token.startswith('0x') and len(
                        content) == 2 and content[1].startswith('PUSH'):
                    content.append(token)
                else:
                    if content:
                        file_contents.append(' '.join(content))
                        if content[1].startswith('PUSH'):
                            pc += int(content[1].split('PUSH')[1])
                        content = []
                        pc += 1
                    content.append(str(pc))
                    if token.startswith('0x'):
                        content.append('INVALID')
                    else:
                        content.append(token)
            if content:
                file_contents.append(' '.join(content))

            self._collect_vertices(file_contents)
            self._construct_bb()
            self._construct_static_edges()
        elif self.input_type == global_params.LanguageType.EVM:
            pass
        else:
            log.mylogger.error('Unknown file type %s', self.input_type)
            raise NotImplementedError(f'Unknown file type {self.input_type}')

    # the algorithm is tricky and may fail if compiler modify the feature
    def get_start_block_to_func_sig(self):
        state = 0
        func_sig = None
        for pc, instr in six.iteritems(self.instructions):
            instr = ' '.join(instr.split(' ')[1:])
            if state == 0 and instr.startswith('PUSH4'):
                func_sig = instr.split(' ')[1][2:]
                state += 1
            elif state == 1 and instr.startswith('DUP'):
                continue
            elif state == 1 and instr.startswith('EQ'):
                state += 1
            elif state == 2 and instr.startswith('PUSH'):
                state = 0
                pc = instr.split(' ')[1]
                pc = int(pc, 16)
                self.start_block_to_func_sig[pc] = func_sig
            else:
                state = 0
        return self.start_block_to_func_sig

    def _collect_vertices(self, file_contents):
        if self.source_map and self.source_map.positions:
            idx = 0
            positions = self.source_map.positions
            length = len(positions)

        self.end_ins_dict = {}
        self.instructions = {}
        self.jump_type = {}

        tok_string = None
        current_block = 0
        is_new_block = True
        inst_pc = None

        for value in file_contents:
            line_parts = value.split(' ')

            last_tok_string = tok_string
            tok_string = line_parts[1]

            last_inst_pc = inst_pc
            inst_pc = int(line_parts[0])

            if self.source_map and self.source_map.positions:
                if idx < length:  # TODO(Chao): Use before define?
                    self.source_map.instr_positions[
                        inst_pc] = self.source_map.positions[idx]
                else:
                    # no use for bytecodes has no position in runtime sourcemap
                    break
                idx += 1

            self.instructions[inst_pc] = value

            if is_new_block:
                current_block = inst_pc
                is_new_block = False

            if tok_string in EvmRuntime.terminal_opcode:
                self.jump_type[current_block] = 'terminal'
                self.end_ins_dict[current_block] = inst_pc
                is_new_block = True
            elif tok_string == 'JUMP':
                self.jump_type[current_block] = 'unconditional'
                self.end_ins_dict[current_block] = inst_pc
                is_new_block = True
            elif tok_string == 'JUMPI':
                self.jump_type[current_block] = 'conditional'
                self.end_ins_dict[current_block] = inst_pc
                is_new_block = True
            elif tok_string == 'JUMPDEST':
                # last instruction don't indicate a new block
                if last_tok_string and (last_tok_string
                                        not in EvmRuntime.terminal_opcode) and (
                                            last_tok_string
                                            not in EvmRuntime.jump_opcode):
                    self.end_ins_dict[current_block] = last_inst_pc
                    self.jump_type[current_block] = 'falls_to'
                    current_block = inst_pc

        # last instruction don't indicate a block termination
        # TODO(Yang): why we need this and how does this happen?
        if current_block not in self.end_ins_dict and inst_pc:
            self.end_ins_dict[current_block] = inst_pc
            self.jump_type[current_block] = 'terminal'

        for key in self.end_ins_dict:
            if key not in self.jump_type:
                self.jump_type[key] = 'falls_to'

        self.get_start_block_to_func_sig()

    def _construct_bb(self):
        self.vertices = {}
        self.edges = {}

        for start_address, end_address in self.end_ins_dict.items():
            block = basic_block.BasicBlock(start_address, end_address)

            changed = False
            lines = set()
            start = sys.maxsize
            end = 0
            for i in range(start_address, end_address + 1):
                if i in self.instructions:
                    block.add_instruction(self.instructions[i])
                    if self.source_map is not None and self.source_map.instr_positions:
                        if self.source_map.in_src_file(
                                self.source_map.instr_positions[i]['f']):
                            t_start = self.source_map.instr_positions[i]['s']
                            t_end = (self.source_map.instr_positions[i]['s'] +
                                     self.source_map.instr_positions[i]['l'])
                            i_lines = self.source_map.get_lines_from_pc(i)
                            changed = changed or util.intersect(
                                self.context.diff, i_lines)
                            for x in i_lines:
                                lines.add(x)
                            if t_start < start:
                                start = t_start
                            if t_end > end:
                                end = t_end
            if start != sys.maxsize and end != 0 and start <= end:
                block.set_position(f'{start}:{end - start}')
            else:
                block.set_position('')
            block.set_lines(list(lines))
            block.set_changed(changed)
            block.set_block_type(self.jump_type[start_address])

            self.vertices[start_address] = block
            self.edges[start_address] = []

    def _construct_static_edges(self):
        key_list = sorted(self.jump_type.keys())
        length = len(key_list)
        for i, key in enumerate(key_list):
            if (self.jump_type[key] != 'terminal' and
                    self.jump_type[key] != 'unconditional' and i + 1 < length):
                target = key_list[i + 1]
                self.edges[key].append(target)
                self.vertices[target].set_jump_from(key)
                self.vertices[key].set_falls_to(target)
            # match [push 0x... jump/jumpi] pattern for jump target
            if self.jump_type[key] == 'conditional' or self.jump_type[
                    key] == 'unconditional':
                instrs = self.vertices[key].get_instructions()
                if len(instrs) > 1 and 'PUSH' in instrs[-2]:
                    target = int(instrs[-2].split(' ')[2], 16)
                    if target not in self.vertices:
                        raise ValueError(f'unrecognized target address '
                                         f'{target:d}')
                    self.edges[key].append(target)

                    self.vertices[target].set_jump_from(key)
                    self.vertices[key].set_jump_targets(target)

    def print_cfg(self):
        file_name = 'cfg' + self.src_file.split('/')[-1].split('.')[0]
        g = graphviz.Digraph('G', filename=file_name)
        g.attr(rankdir='TB')
        g.attr(overlap='scale')
        g.attr(splines='polyline')
        g.attr(ratio='fill')

        # TODO(Chao): Avoid using str append (+) in loop,
        #  instead use str join for str list
        for block in self.vertices.values():
            start = block.get_start_address()
            end = block.get_end_address()
            label = f'{start}-{end}\n'
            if start != end:
                label = (f'{label}{self.instructions[start]}\n...\n'
                         f'{self.instructions[end]}')
            else:
                label = label + self.instructions[start]

            block_type = block.get_block_type()

            start = str(start)
            if block_type == 'falls_to':
                g.node(name=start, label=label)
                g.edge(start, str(block.get_falls_to()),
                       color='black')  # black for falls to
            elif block_type == 'unconditional':
                g.node(name=start, label=label, color='blue')
                for target in block.get_jump_targets():
                    g.edge(start, str(target),
                           color='blue')  # blue for unconditional jump
            elif block_type == 'conditional':
                g.node(name=start, label=label, color='green')
                g.edge(start, str(block.get_falls_to()), color='red')
                for target in block.get_jump_targets():
                    g.edge(start, str(target),
                           color='green')  # blue for unconditional jump
            elif block_type == 'terminal':
                g.node(name=start, label=label, color='red')

        g.render(f'{file_name}_cfg',
                 format='png',
                 directory=global_params.DEST_PATH,
                 view=True)

    def print_visited_cfg(self, visited_edges):
        g = graphviz.Digraph(name='ControlFlowGraph', format='pdf')

        # TODO(Chao): Avoid using str append (+) in loop,
        #  instead use str join for str list
        for block in self.vertices.values():
            start = block.get_start_address()
            end = block.get_end_address()
            label = f'{start}-{end}\n'
            if start != end:
                label = (f'{label}{self.instructions[start]}\n...\n'
                         f'{self.instructions[end]}')
            else:
                label = label + self.instructions[start]
            # label = ''
            # list.sort(block.lines)
            # if len(block.lines) >= 3:
            #     label = self.source_map.source.get_content_from_line(
            #     block.lines[0]) + '\n' + '...\n' +
            #     self.source_map.source.get_content_from_line(block.lines[-1])
            # else:
            #     for line in block.lines:
            #         label = label + '\n' +
            #         self.source_map.source.get_content_from_line(line)

            block_type = block.get_block_type()

            start = str(start)
            color = 'black'
            if block_type == 'falls_to':
                g.node(name=start, label=label)
                if (int(start), block.get_falls_to()) in visited_edges:
                    e_label = str(visited_edges[(int(start),
                                                 block.get_falls_to())])
                    color = 'blue'
                else:
                    e_label = '0'

                g.edge(start,
                       str(block.get_falls_to()),
                       color=color,
                       label=e_label)  # black for falls to
            elif block_type == 'unconditional':
                g.node(name=start, label=label, color='blue')
                for target in block.get_jump_targets():
                    if (int(start), target) in visited_edges:
                        e_label = str(visited_edges[(int(start), target)])
                        color = 'blue'
                    else:
                        e_label = '0'
                    g.edge(start, str(target), color=color,
                           label=e_label)  # blue for unconditional jump
            elif block_type == 'conditional':
                g.node(name=start, label=label, color='green')
                if (int(start), block.get_falls_to()) in visited_edges:
                    e_label = str(visited_edges[(int(start),
                                                 block.get_falls_to())])
                    color = 'red'
                else:
                    e_label = '0'
                g.edge(start,
                       str(block.get_falls_to()),
                       color=color,
                       label=e_label)
                for target in block.get_jump_targets():
                    if (int(start), target) in visited_edges:
                        e_label = str(visited_edges[(int(start), target)])
                        color = 'green'
                    else:
                        e_label = '0'
                    g.edge(start, str(target), color=color,
                           label=e_label)  # blue for unconditional jump
            elif block_type == 'terminal':
                g.node(name=start, label=label, color='red')

        g.render(os.path.join(
            global_params.DEST_PATH,
            f'cfg{self.src_file.split("/")[-1].split(".")[0]}.gv'),
                 view=False)
