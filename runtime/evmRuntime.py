import logging
import os
import sys

from graphviz import Digraph

from inputDealer.solidityAstWalker import AstWalker
from utils import compare_versions
from runtime.basicBlock import BasicBlock
import disassembler.params
import global_params


log = logging.getLogger()


class EvmRuntime:
    terminal_opcode = {"STOP", "RETURN", "SUICIDE", "REVERT", "ASSERTFAIL", "INVALID"}
    jump_opcode = {"JUMP", "JUMPI"}
    block_jump_types = {"terminal", "conditional", "unconditional", "falls_to"}

    def __init__(self, platform=None, disasm_file=None, source_map=None, source_file=None, input_type=None, evm=None):
        self.disasm_file = disasm_file  # disassemble file of contract in string like "PUSH1 0x55 PUSH1 0x23 PUSH1 0xB"
        self.source_map = source_map  # SourceMap class of solidity of the contract
        # specified block chain platform, eg. ethereum, xuper-chain, fisco-bcos, for specific analysis
        self.platFrom = platform
        self.source_file = source_file  # complete path of solidity file
        self.input_type = input_type  # input file defined in file global_params.py and assigned in cmd
        self.evm = evm  # runtime evm bytes of the contract

    def build_cfg(self):
        if self.input_type == global_params.SOLIDITY:
            # 1. transfer from token string to
            tokens = self.disasm_file.split(" ")
            file_contents = []
            content = []
            pc = 0
            for i, token in enumerate(tokens):
                if token.startswith("0x") and len(content) == 2 and content[1].startswith("PUSH"):
                    content.append(token)
                else:
                    if content:
                        file_contents.append(' '.join(content))
                        if content[1].startswith("PUSH"):
                            pc += int(content[1].split('PUSH')[1])
                        content = []
                        pc += 1
                    content.append(str(pc))
                    if token.startswith("0x"):
                        content.append("INVALID")
                    else:
                        content.append(token)

            self._collect_vertices(file_contents)
            self._construct_bb()
            self._construct_static_edges()
        else:
            self.change_format()
            with open(self.disasm_file, 'r') as disasm_file:
                file_contents = disasm_file.readlines()
                self._collect_vertices(file_contents)
                self._construct_bb()
                self._construct_static_edges()

    def change_format(self):
        with open(self.disasm_file, 'r') as disasm_file:
            file_contents = disasm_file.readlines()
            file_contents = file_contents[1:]
            for i, line in enumerate(file_contents):
                line = line.replace('SELFDESTRUCT', 'SUICIDE')
                line = line.replace('Missing opcode 0xfd', 'REVERT')
                line = line.replace('Missing opcode 0xfe', 'INVALID')

                # unrecognized instruction
                if "Missing opcode" in line:
                    raise Exception("unrecognized instruction: %s", line)

                line = line.replace(':', '')
                lineParts = line.split(' ')

                # transform the pc from hex to decimal
                try:
                    if compare_versions(disassembler.params.EVM_VERSION, disassembler.params.CHANGED_EVM_VERSION) > 0:
                        lineParts[0] = str(int(lineParts[0], 16))
                    else:
                        lineParts[0] = str(int(lineParts[0]))
                except Exception:
                    raise Exception("unknown pc format for disasm file")

                file_contents[i] = ' '.join(lineParts)
            file_contents[-1] = file_contents[-1].strip("\n")

        with open(self.disasm_file, 'w') as disasm_file:
            disasm_file.write("".join(file_contents))

    def _collect_vertices(self, file_contents):

        if self.source_map and self.source_map.positions:
            idx = 0
            positions = self.source_map.positions
            length = len(positions)

        self.end_ins_dict ={}
        self.instructions ={}
        self.jump_type = {}

        tok_string = None
        current_block = 0
        is_new_block = True
        inst_pc = None

        for index, value in enumerate(file_contents):
            line_parts = value.split(" ")

            last_tok_string = tok_string
            tok_string = line_parts[1]

            last_inst_pc = inst_pc
            inst_pc = int(line_parts[0])

            if self.source_map and self.source_map.positions:
                if idx < length:
                    self.source_map.instr_positions[inst_pc] = self.source_map.positions[idx]
                else:
                    # for bytecodes has no position in runtime sourcemap, it's useless
                    break
                idx += 1

            self.instructions[inst_pc] = value

            if is_new_block:
                current_block = inst_pc
                is_new_block = False

            if tok_string in EvmRuntime.terminal_opcode:
                self.jump_type[current_block] = "terminal"
                self.end_ins_dict[current_block] = inst_pc
                is_new_block = True
            elif tok_string == "JUMP":
                self.jump_type[current_block] = "unconditional"
                self.end_ins_dict[current_block] = inst_pc
                is_new_block = True
            elif tok_string == "JUMPI":
                self.jump_type[current_block] = "conditional"
                self.end_ins_dict[current_block] = inst_pc
                is_new_block = True
            elif tok_string == "JUMPDEST":
                if last_tok_string and (last_tok_string not in EvmRuntime.terminal_opcode) and (last_tok_string not in EvmRuntime.jump_opcode): #last instruction don't indicate a new block
                    self.end_ins_dict[current_block] = last_inst_pc
                    self.jump_type[current_block] = "falls_to"
                    current_block = inst_pc

        # last instruction don't indicate a block termination
        if current_block not in self.end_ins_dict and inst_pc:
            self.end_ins_dict[current_block] = inst_pc
            self.jump_type[current_block] = "terminal"

        for key in self.end_ins_dict:
            if key not in self.jump_type:
                self.jump_type[key] = "falls_to"

    def _construct_bb(self):
        self.vertices = {}
        self.edges = {}

        for start_address in self.end_ins_dict:
            end_address = self.end_ins_dict[start_address]

            block = BasicBlock(start_address, end_address)

            changed = False
            lines = set()
            walker = AstWalker(global_params.AST, global_params.DIFFS)
            start = sys.maxsize
            end = 0
            for i in range(start_address, end_address + 1):
                if i in self.instructions:
                    block.add_instruction(self.instructions[i])
                    if self.source_map.instr_positions:
                        if self.source_map.instr_positions[i]["f"] != -1:
                            t_start = self.source_map.instr_positions[i]["s"]
                            t_end = self.source_map.instr_positions[i]["s"] + self.source_map.instr_positions[i]["l"]
                            i_lines = self.source_map.source.get_lines_from_position(t_start, t_end)
                            changed = changed or walker.is_changed(i_lines)
                            for x in i_lines:
                                lines.add(x)
                            if t_start < start:
                                start = t_start
                            if t_end > end:
                                end = t_end

            block.set_position(str(start)+":"+str(end))
            block.set_lines(list(lines))
            block.set_changed(changed)
            block.set_block_type(self.jump_type[start_address])

            self.vertices[start_address] = block
            self.edges[start_address] = []

    def _construct_static_edges(self):
        key_list = sorted(self.jump_type.keys())
        length = len(key_list)
        for i, key in enumerate(key_list):
            if self.jump_type[key] != "terminal" and self.jump_type[key] != "unconditional" and i + 1 < length:
                target = key_list[i+1]
                self.edges[key].append(target)
                self.vertices[target].set_jump_from(key)
                self.vertices[key].set_falls_to(target)
            # match [push 0x... jump/jumpi] pattern for jump target
            if self.jump_type[key] == "conditional" or self.jump_type[key] == "unconditional":
                instrs = self.vertices[key].get_instructions()
                if len(instrs) > 1 and "PUSH" in instrs[-2]:
                    target = int(instrs[-2].split(" ")[2], 16)
                    if target not in self.vertices:
                        raise Exception("unrecognized target address %d", target)
                    self.edges[key].append(target)

                    self.vertices[target].set_jump_from(key)
                    self.vertices[key].set_jump_targets(target)

    def print_cfg(self):
        file_name = "cfg" + self.source_file.split("/")[-1].split(".")[0]
        g1 = Digraph('G', filename=file_name)
        g1.attr(rankdir='TB')
        g1.attr(overlap='scale')
        g1.attr(splines='polyline')
        g1.attr(ratio='fill')

        with g1.subgraph(name=file_name) as g:
            g.attr(label=file_name)
            g.attr(overlap='false')
            g.attr(splines='polyline')
            g.attr(ratio='fill')
            for block in self.vertices.values():
                start = block.get_start_address()
                end = block.get_end_address()
                label = str(start) + "-" + str(end) + "\n"
                if start != end:
                    label = label + self.instructions[start] + "\n...\n" + self.instructions[end]
                else:
                    label = label + self.instructions[start]

                block_type = block.get_block_type()

                start = str(start)
                if block_type == "falls_to":
                    g.node(name=start, label=label)
                    g.edge(start, str(block.get_falls_to()), color="black")  # black for falls to
                elif block_type == "unconditional":
                    g.node(name=start, label=label, color="blue")
                    for target in block.get_jump_targets():
                        g.edge(start, str(target), color="blue")  # blue for unconditional jump
                elif block_type == "conditional":
                    g.node(name=start, label=label, color="green")
                    g.edge(start, str(block.get_falls_to()), color="red")
                    for target in block.get_jump_targets():
                        g.edge(start, str(target), color="green")  # blue for unconditional jump
                elif block_type == "terminal":
                    g.node(name=start, label=label, color="red")
        g1.render(file_name, format='png', directory=global_params.TMP_DIR,
                 view=True)

    def print_cfg_dot(self, visited_edges):
        g = Digraph(name="ControlFlowGraph",
                    comment=self.disasm_file,
                    format='pdf'
                    )

        for block in self.vertices.values():
            start = block.get_start_address()
            end = block.get_end_address()
            label = str(start) + "-" + str(end)+"\n"
            if start != end:
                label = label + self.instructions[start] + "\n...\n" + self.instructions[end]
            else:
                label = label + self.instructions[start]

            block_type = block.get_block_type()

            start = str(start)
            if block_type == "falls_to":
                g.node(name=start, label=label)
                if (int(start), block.get_falls_to()) in visited_edges:
                    e_label = str(visited_edges[(int(start), block.get_falls_to())])
                else:
                    e_label = "0"
                g.edge(start, str(block.get_falls_to()), color="black",
                       label=e_label)  # black for falls to
            elif block_type == "unconditional":
                g.node(name=start, label=label, color="blue")
                for target in block.get_jump_targets():
                    if (int(start), target) in visited_edges:
                        e_label = str(visited_edges[(int(start), target)])
                    else:
                        e_label = "0"
                    g.edge(start, str(target), color="blue",
                           label=e_label)  # blue for unconditional jump
            elif block_type == "conditional":
                g.node(name=start, label=label, color="green")
                if (int(start), block.get_falls_to()) in visited_edges:
                    e_label = str(visited_edges[(int(start), block.get_falls_to())])
                else:
                    e_label = "0"
                g.edge(start, str(block.get_falls_to()), color="red",
                       label=e_label)
                for target in block.get_jump_targets():
                    if (int(start), target) in visited_edges:
                        e_label = str(visited_edges[(int(start), target)])
                    else:
                        e_label = "0"
                    g.edge(start, str(target), color="green",
                           label=e_label)  # blue for unconditional jump
            elif block_type == "terminal":
                g.node(name=start, label=label, color="red")
        g.render(os.path.join(global_params.TMP_DIR, "cfg"+self.source_file.split("/")[-1].split(".")[0]+".gv"), view=True)


