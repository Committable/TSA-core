import six


class BasicBlock:

    def __init__(self,
                 start_address,
                 end_address=None,
                 start_inst=None,
                 end_inst=None):
        self.start = start_address
        self.start_inst = start_inst

        self.end = end_address
        self.end_inst = end_inst

        self.instructions = []  # each instruction is a string

        self.jump_from = [
        ]  # all blocks from which can jump to or fall to this block

        self.falls_to = None  # the block this block can falls to

        # all true targets for conditional jump or targets for un-condition
        # jump, we don't use set() because the top of jump_targets is the
        # aimed pc currently
        self.jump_targets = []

        self.type = None

        self.branch_expression = None
        self.branch_expression_node = None
        self.negated_branch_expression_node = None
        self.branch_id = []

        self.position = ''
        self.jump_in_type = ''
        self.changed = False
        self.lines = []

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

    def set_block_type(self, block_type):
        self.type = block_type

    def get_block_type(self):
        return self.type

    def set_falls_to(self, address):
        # target for fall through and false branch for conditional jump
        self.falls_to = address

    def get_falls_to(self):
        return self.falls_to

    def set_jump_targets(self, address):
        # top element is the most recently setted jump target
        for x in self.jump_targets:
            if x == address:
                self.jump_targets.remove(x)

        self.jump_targets.append(address)

    def get_jump_targets(self):
        return self.jump_targets

    def get_jump_target(self):  # top element is current jump target
        if len(self.jump_targets) == 0:
            return None
        return self.jump_targets[-1]

    def set_branch_expression(self, branch):
        self.branch_expression = branch

    def set_branch_node_expression(self, branch_node):
        self.branch_expression_node = branch_node

    def set_negated_branch_node_expression(self, negated_branch_node):
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

    def set_position(self, src):
        self.position = src

    def set_jump_in(self, t):
        self.jump_in_type = t

    def set_lines(self, lines):
        self.lines = lines

    def set_changed(self, changed):
        self.changed = changed

    def display(self):
        six.print_('================')
        six.print_('start address: %d', self.start)
        six.print_('end address: %d', self.end)
        six.print_('end statement type: %s', self.type)
        for instr in self.instructions:
            six.print_(instr)
