class Generator:
    def __init__(self):
        self.countstack = 0
        self.countdata = 0
        self.count = 0
        self.path = 0

        self.overflow_name_count = {}

    def gen_address(self, pc):
        return "address_" + str(pc)

    def gen_overflow_var(self, opcode, pc, path_id):
        if (opcode, pc, path_id) not in self.overflow_name_count:
            self.overflow_name_count[(opcode, pc, path_id)] = 0
        self.overflow_name_count[(opcode, pc, path_id)] += 1
        return "overflow_" + str(opcode) + "_" + str(pc) + "_" + str(path_id) +"_" + str(self.overflow_name_count[(opcode, pc, path_id)])

    def gen_balance_of(self, address):
        return "init_" + str(address)

    def gen_return_status(self, pc, path_id):
        return "return_status_" + str(pc) + "_" + str(path_id)

    def gen_return_data_size(self, pc, path_id):
        return "Rd_size_" + str(pc) + "_" + str(path_id)

    def gen_evm_data(self, start, end):
        return "evm_" + str(start) + "_" + str(end)

    def gen_ext_code_data(self, address, start, end):
        return "bytecode_" + str(address) + "_" + str(start) + "_" + str(end)

    def gen_code_size_var(self, address):
        return "code_size_" + str(address)

    def gen_return_data(self, pc, start, end, path_id):
        return "Rd_" + str(pc) + "_" + str(start) + "_" + str(end) + "_" + str(path_id)

    def gen_data_var(self, start, end):
        return "Id_" + str(start) + "_" + str(end)

    def gen_data_size(self):
        return "Id_size"

    def gen_mem_var(self, address, pc, path_id):
        return "mem_" + str(address) + "_" + str(pc) + "_" + str(path_id)

    def gen_storage_var(self, position):
        return "storage_" + str(position)

    def gen_exp_var(self, v0, v1):
        return "exp(" + str(v0) + ", " + str(v1) + ")"

    def gen_sha3_var(self, value):
        return "sha3("+str(value)+")"

    def gen_gas_var(self, pc):
        self.count += 1
        return "gas_" + str(self.count) + "_" + str(pc)

    def gen_gas_price_var(self):
        return "Ip"

    def gen_origin_var(self):
        return "Io"

    def gen_blockhash(self, number):
        return "IH_blockhash_"+str(number)

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

    def gen_path_id(self):
        self.path += 1
        return "path_"+str(self.path)

    def get_path_id(self):
        return "path_"+str(self.path+1)

    # for wasm
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


