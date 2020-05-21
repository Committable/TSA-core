import six
from graphBuilder.XGraph import *
# from disassembler.wasmConvention import opcodes


class BasicBlock:
    def __init__(self, start_address, end_address=None, start_inst= None, end_inst = None):
        self.start = start_address
        self.start_inst = start_inst

        self.end = end_address
        self.end_inst = end_inst

        self.instructions = []  # each instruction is a string

        self.jump_from = []  # all blocks from which can jump to or fall to this block

        self.falls_to = None
        self.jump_targets = []  # all true targets for conditional jump or targets for uncondition jump

        self.type = None

        self.branch_expression = None
        self.branch_expression_node = None
        self.negated_branch_expression_node = None
        self.branch_id = []

    def set_jump_to(self, to):
        self.jump_to.append(to)

    def set_type(self, type):
        self.type = type

    def get_type(self):
        return self.type

    def get_start_address(self):
        return self.start

    def get_end_address(self):
        return self.end

    def add_instruction(self, instruction):
        self.instructions.append(instruction)

    def get_instructions(self):
        return self.instructions

    def set_block_type(self, type):
        self.type = type

    def get_block_type(self):
        return self.type

    def set_falls_to(self, address):
        self.falls_to = address #target for fall through and false branch for conditional jump

    def get_falls_to(self):
        return self.falls_to

    def set_jump_targets(self, address):
        self.jump_targets.append(address)

    def get_jump_targets(self):
        return self.jump_targets

    def set_branch_expression(self, branch):
        self.branch_expression = branch

    def set_branch_node_experssion(self, branch_node):
        self.branch_expression_node = branch_node

    def set_negated_branch_node_experssion(self, negated_branch_node):
        self.negated_branch_expression_node = negated_branch_node

    def set_jump_from(self, block):
        self.jump_from.append(block)

    def get_jump_from(self):
        return self.jump_from

    def get_branch_expression(self):
        return self.branch_expression

    def get_branch_expression_node(self):
        return self.branch_expression_node

    def get_negated_branch_expression_node(self):
        return self.negated_branch_expression_node

    def instructions_details(self, format='hex'):
        out = ''
        line = ''
        for i in self.instructions:
            line = '%x: ' % i.offset
            if i.immediate_arguments is not None and not i.xref:
                line += '%s' % str(i)
            elif isinstance(i.xref, list) and i.xref:
                line += '%s %s' % (opcodes[i.code][0], i.xref)
            elif isinstance(i.xref, int) and i.xref:
                line += '%s %x' % (opcodes[i.code][0], i.xref)
            # elif i.operand_interpretation:
            #     line += i.operand_interpretation
            else:
                line += opcodes[i.code][0] + ' '

            out = out + line + "\n"
        return out

    def display(self):
        six.print_("================")
        six.print_("start address: %d" % self.start)
        six.print_("end address: %d" % self.end)
        six.print_("end statement type: " + self.type)
        for instr in self.instructions:
            six.print_(instr)
