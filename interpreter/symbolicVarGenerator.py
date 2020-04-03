class Generator:
    def __init__(self):
        self.countstack = 0
        self.countdata = 0
        self.count = 0
        self.branch = 0

    def gen_stack_var(self):
        self.countstack += 1
        return "s" + str(self.countstack)

    # def gen_data_var(self):
    #     self.countdata += 1
    #     return "Id_" + str(self.countdata)

    def gen_data_var(self, position):
        self.countdata += 1
        return "Id_" + str(self.countdata) + "_" + str(position)

    def gen_data_size(self):
        return "Id_size_" + str(self.branch)

    def gen_mem_var(self, address):
        return "mem_" + str(address)

    def gen_arbitrary_var(self):
        self.count += 1
        return "some_var_" + str(self.count)

    def gen_arbitrary_address_var(self):
        self.count += 1
        return "some_address_" + str(self.count)

    def gen_owner_store_var(self, position, var_name=""):
        return "Ia_store-%s-%s" % (str(position), var_name)

    def gen_gas_var(self):
        self.count += 1
        return "gas_" + str(self.count)

    def gen_gas_price_var(self):
        return "Ip"

    def gen_address_var(self):
        return "Ia"

    def gen_caller_var(self):
        return "Is"

    def gen_origin_var(self):
        return "Io"

    def gen_coin_base(self):
        return "IH_c"

    def gen_difficult(self):
        return "IH_d"

    def gen_gas_limit(self):
        return "IH_l"

    def gen_number(self):
        return "IH_i"

    def gen_timestamp(self):
        return "IH_s"

    def gen_balance_var(self):
        self.count += 1
        return "balance_" + str(self.count)

    def gen_code_var(self, address, position, bytecount):
        return "code_" + str(address) + "_" + str(position) + "_" + str(bytecount)

    def gen_code_size_var(self, address):
        return "code_size_" + str(address)

    def gen_import_global_var(self, module, name):
        return "global_"+str(module)+str(name)

    def gen_input_var(self, index):
        return "param_" + str(index)

    def gen_local_var(self, index):
        return "local_" + str(index)

    def gen_select_var(self, index):
        self.count += 1
        return "select_"+str(index)+"_"+str(self.count)

    def gen_func_call(self, addr):
        self.count += 1
        return "call_"+str(addr)+"_"+str(self.count)

    def gen_branch_id(self):
        self.branch += 1
        return "branch_"+str(self.branch)

    def get_branch_id(self):
        return "branch_"+str(self.branch)
