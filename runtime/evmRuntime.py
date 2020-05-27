import logging
from utils import compare_versions
from runtime.basicBlock import BasicBlock
import disassembler.params
from graphviz import Digraph
import global_params
import os

log = logging.getLogger()

class EvmRuntime:
    terminal_opcode = {"STOP", "RETURN", "SUICIDE", "REVERT", "ASSERTFAIL"}
    jump_opcode = {"JUMP", "JUMPI"}
    block_jump_types = {"terminal", "conditional", "unconditional", "falls_to"}

    def __init__(self, platform=None, disasm_file=None,source_map=None, source_file=None):
        self.disasm_file = disasm_file
        self.source_map = source_map
        self.platFrom = platform
        self.source_file = source_file

    def build_cfg(self):
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

    def _collect_vertices(self,file_contents):
        if self.source_map:
            idx = 0
        self.end_ins_dict ={}
        self.instructions ={}
        self.jump_type = {}

        tok_string = None
        current_block = 0
        is_new_block = True
        inst_pc = None

        for index, value in enumerate(file_contents):
            line_parts = value.strip("\n").split(" ")

            last_tok_string = tok_string
            tok_string = line_parts[1]

            last_inst_pc = inst_pc
            inst_pc = int(line_parts[0])

            self.instructions[inst_pc] = value.strip("\n")

            if is_new_block:
                current_block = inst_pc
                is_new_block = False

            if tok_string == "STOP" or tok_string == "RETURN" or tok_string == "SUICIDE" or tok_string == "REVERT" or tok_string == "ASSERTFAIL":
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
                idx += 1  # TODO:there is always a "tag" before "JUMPDEST", why it's necessary and it's sure?
                if last_tok_string and (last_tok_string not in EvmRuntime.terminal_opcode) and (last_tok_string not in EvmRuntime.jump_opcode): #last instruction don't indicate a new block
                    self.end_ins_dict[current_block] = last_inst_pc
                    self.jump_type[current_block] = "falls_to"
                    current_block = inst_pc

            if self.source_map:
                self.source_map.instr_positions[inst_pc] = self.source_map.positions[idx]

            idx += 1

        # check the sourcemap is well format
        if self.source_map:
            assert(idx == len(self.source_map.positions))

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

            for i in range(start_address, end_address + 1):
                if i in self.instructions:
                    block.add_instruction(self.instructions[i])

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
                    self.edges[key].append(target)
                    self.vertices[target].set_jump_from(key)
                    self.vertices[key].set_jump_targets(target)

    def print_cfg(self):
        keys = sorted(self.vertices.keys())
        for key in keys:
            block = self.vertices[key]
            block.display()
        log.debug(str(self.edges))

    def print_cfg_dot(self):
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

        g.render(os.path.join(global_params.TMP_DIR, "cfg.gv"), view=True)

    def build_runtime_env(self):
        #todo: test for building cfg process
        self.build_cfg()
        # self.print_cfg()
        self.print_cfg_dot()
        return 0

