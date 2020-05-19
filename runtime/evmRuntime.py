import time
import logging
import tokenize
from utils import compare_versions
from runtime.basicBlock import BasicBlock
import disassembler.params
from tokenize import NUMBER, NAME, NEWLINE
# from graphviz import Digraph


log=logging.getLogger()

class EvmRuntime:
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
                line = line.replace('Missing opcode 0xfe', 'ASSERTFAIL')
                line = line.replace('Missing opcode', 'INVALID')
                line = line.replace(':', '')
                lineParts = line.split(' ')
                try:  # removing initial zeroes
                    if compare_versions(disassembler.params.EVM_VERSION, disassembler.params.CHANGED_EVM_VERSION) > 0:
                        lineParts[0] = str(int(lineParts[0], 16))
                    else:
                        lineParts[0] = str(int(lineParts[0]))

                except:
                    raise Exception("unkonwn pc format for disasm file")


                file_contents[i] = ' '.join(lineParts)
            file_contents[-1] = file_contents[-1].strip("\n")


        with open(self.disasm_file, 'w') as disasm_file:
            disasm_file.write("".join(file_contents))

    # 1. Parse the disassembled file
    # 2. Then identify each basic block (i.e. one-in, one-out)
    # 3. Store them in vertices
    def _collect_vertices(self,file_contents):
        if self.source_map:
            positions = self.source_map.positions
            assert(len(positions) == len(file_contents))
        self.end_ins_dict ={}
        self.instructions ={}
        self.jump_type = {}

        last_block = 0
        current_block = 0
        is_new_block = True

        for index, value in enumerate(file_contents):

            line_parts = value.strip("\n").split(" ")
            self.instructions[index] = " ".join(line_parts[1:])

            tok_string = line_parts[1]

            if is_new_block:
                last_block = current_block
                current_block = index
                is_new_block = False

            if tok_string == "STOP" or tok_string == "RETURN" or tok_string == "SUICIDE" or tok_string == "REVERT" or tok_string == "ASSERTFAIL":
                self.jump_type[current_block] = "terminal"
                self.end_ins_dict[current_block] = index
                is_new_block = True
            elif tok_string == "JUMP":
                self.jump_type[current_block] = "unconditional"
                self.end_ins_dict[current_block] = index
                is_new_block = True
            elif tok_string == "JUMPI":
                self.jump_type[current_block] = "conditional"
                self.end_ins_dict[current_block] = index
                is_new_block = True
            elif tok_string == "JUMPDEST":
                if last_block not in self.end_ins_dict:
                    self.end_ins_dict[last_block] = index-1
            # todo: continut deal

    def _construct_bb(self):
        self.vertices = {}
        self.edges = {}
        size = len(self.instructions)
        for start_address in self.end_ins_dict:
            end_address = self.end_ins_dict[start_address]
            block = BasicBlock(start_address, end_address)
            for i in range(start_address, end_address + 1):
                block.add_instruction(self.instructions[i])
            block.set_block_type(self.jump_type[start_address])
            self.vertices[key] = block
            self.edges[key] = []

    def _construct_static_edges(self):
        key_list = sorted(self.jump_type.keys())
        length = len(key_list)
        for i, key in enumerate(key_list):
            if self.jump_type[key] != "terminal" and self.jump_type[key] != "unconditional" and i + 1 < length:
                target = key_list[i + 1]
                self.edges[key].append(target)
                self.vertices[target].set_jump_from(key)
                self.vertices[key].set_falls_to(target)

    def print_cfg(self,path):
        for block in self.vertices.values():
            block.display()
        log.debug(str(self.edges))




    def build_runtime_env(self):
        begin = time.time()
        self.build_cfg()
        # self.print_cfg('reporter/visited-cfg-merge.gv')



        # initialize_platform()
        end = time.time()
