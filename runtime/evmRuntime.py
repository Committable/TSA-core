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
            disasm_file.readline()  # Remove first line
            tokens = tokenize.generate_tokens(disasm_file.readline)
            self._collect_vertices(tokens)
            self._construct_bb()
            self._construct_static_edges()

    def change_format(self):
        with open(self.disasm_file) as disasm_file:
            file_contents = disasm_file.readlines()
            i = 0
            firstLine = file_contents[0].strip('\n')
            for line in file_contents:
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
                    lineParts[0] = lineParts[0]
                lineParts[-1] = lineParts[-1].strip('\n')
                try:  # adding arrow if last is a number
                    lastInt = lineParts[-1]
                    if (int(lastInt, 16) or int(lastInt, 16) == 0) and len(lineParts) > 2:
                        lineParts[-1] = "=>"
                        lineParts.append(lastInt)
                except Exception:
                    pass
                file_contents[i] = ' '.join(lineParts)
                i = i + 1
            file_contents[0] = firstLine
            file_contents[-1] += '\n'

        with open(self.disasm_file, 'w') as disasm_file:
            disasm_file.write("\n".join(file_contents))

    # 1. Parse the disassembled file
    # 2. Then identify each basic block (i.e. one-in, one-out)
    # 3. Store them in vertices
    def _collect_vertices(self,tokens):
        if self.source_map:
            idx = 0
            positions = self.source_map.positions
            length = len(positions)
        self.end_ins_dict ={}
        self.instructions ={}
        self.jump_type = {}

        current_ins_address = 0
        last_ins_address = 0
        is_new_line = True
        current_block = 0
        current_line_content = ""
        wait_for_push = False
        is_new_block = False
        for tok_type, tok_string, (srow, scol), mi, line_number in tokens:
            if wait_for_push is True:
                push_val = ""
                for ptok_type, ptok_string, _, _, _ in tokens:
                    if ptok_type == NEWLINE:
                        is_new_line = True
                        current_line_content += push_val + ' '
                        self.instructions[current_ins_address] = current_line_content
                        idx = self._mapping_push_instruction(current_line_content, current_ins_address, idx, positions,length) if self.source_map else None
                        log.debug(current_line_content)
                        current_line_content = ""
                        wait_for_push = False
                        break
                    try:
                        int(ptok_string, 16)
                        push_val += ptok_string
                    except ValueError:
                        pass

                continue
            elif is_new_line is True and tok_type == NUMBER:  # looking for a line number
                last_ins_address = current_ins_address
                try:
                    current_ins_address = int(tok_string)
                except ValueError:
                    log.critical("ERROR when parsing row %d col %d", srow, scol)
                    quit()
                is_new_line = False
                if is_new_block:
                    current_block = current_ins_address
                    is_new_block = False
                continue
            elif tok_type == NEWLINE:
                is_new_line = True
                log.debug(current_line_content)
                self.instructions[current_ins_address] = current_line_content
                idx = self._mapping_non_push_instruction(current_line_content, current_ins_address, idx, positions,length) if self.source_map else None
                current_line_content = ""
                continue
            elif tok_type == NAME:
                if tok_string == "JUMPDEST":
                    if last_ins_address not in self.end_ins_dict:
                        self.end_ins_dict[current_block] = last_ins_address
                    current_block = current_ins_address
                    is_new_block = False
                elif tok_string == "STOP" or tok_string == "RETURN" or tok_string == "SUICIDE" or tok_string == "REVERT" or tok_string == "ASSERTFAIL":
                    self.jump_type[current_block] = "terminal"
                    self.end_ins_dict[current_block] = current_ins_address
                elif tok_string == "JUMP":
                    self.jump_type[current_block] = "unconditional"
                    self.end_ins_dict[current_block] = current_ins_address
                    is_new_block = True
                elif tok_string == "JUMPI":
                    self.jump_type[current_block] = "conditional"
                    self.end_ins_dict[current_block] = current_ins_address
                    is_new_block = True
                elif tok_string.startswith('PUSH', 0):
                    wait_for_push = True
                is_new_line = False
            if tok_string != "=" and tok_string != ">":
                current_line_content += tok_string + " "
        # log.info("<<<<<<<<<<<<<<<<")
        # log.info("**************")
        # for i in instructions.keys():
        #     log.info(str(i) + ":" + instructions[i])
        # log.info("*************")
        if current_block not in self.end_ins_dict:
            log.debug("current block: %d", current_block)
            log.debug("last line: %d", current_ins_address)
            self.end_ins_dict[current_block] = current_ins_address

        if current_block not in self.jump_type:
            self.jump_type[current_block] = "terminal"

        for key in self.end_ins_dict:
            if key not in self.jump_type:
                self.jump_type[key] = "falls_to"

    def _mapping_push_instruction(self,current_line_content, current_ins_address, idx, positions, length):
        while (idx < length):
            if not positions[idx]:
                return idx + 1
            name = positions[idx]['name']
            if name.startswith("tag"):
                idx += 1
            else:
                if name.startswith("PUSH"):
                    if name == "PUSH":
                        value = positions[idx]['value']
                        instr_value = current_line_content.split(" ")[1]
                        if int(value, 16) == int(instr_value, 16):
                            self.source_map.instr_positions[current_ins_address] = self.source_map.positions[idx]
                            idx += 1
                            break
                        else:
                            raise Exception("Source map error")
                    else:
                        self.source_map.instr_positions[current_ins_address] = self.source_map.positions[idx]
                        idx += 1
                        break
                else:
                    raise Exception("Source map error")
        return idx

    def _mapping_non_push_instruction(self,current_line_content, current_ins_address, idx, positions, length):
        while (idx < length):
            if not positions[idx]:
                return idx + 1
            name = positions[idx]['name']
            if name.startswith("tag"):
                idx += 1
            else:
                instr_name = current_line_content.split(" ")[0]
                if name == instr_name or name == "INVALID" and instr_name == "ASSERTFAIL" or name == "KECCAK256" and instr_name == "SHA3" or name == "SELFDESTRUCT" and instr_name == "SUICIDE":
                    self.source_map.instr_positions[current_ins_address] = self.source_map.positions[idx]
                    idx += 1
                    break
                else:
                    raise Exception("Source map error")
        return idx

    def _construct_bb(self):
        self.vertices = {}
        self.edges = {}
        sorted_addresses = sorted(self.instructions.keys())
        size = len(sorted_addresses)
        for key in self.end_ins_dict:
            end_address = self.end_ins_dict[key]
            block = BasicBlock(key, end_address)
            if key not in self.instructions:
                continue
            block.add_instruction(self.instructions[key])
            i = sorted_addresses.index(key) + 1
            while i < size and sorted_addresses[i] <= end_address:
                block.add_instruction(self.instructions[sorted_addresses[i]])
                i += 1
            block.set_block_type(self.jump_type[key])
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
