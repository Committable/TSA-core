class Generator:

    def __init__(self):
        self.path = 0

    # todo: str() of symbolic expression is time-consuming

    @staticmethod
    def gen_contract_address(pc):
        return f'contractAddress_{pc}'

    @staticmethod
    def gen_balance_of(address):
        return f'init_{address}'

    @staticmethod
    def gen_return_data_size(call_pc):
        return f'returnSize_{call_pc}'

    @staticmethod
    def gen_evm_data(start, end):
        return f'evm_{start}_{end}'

    @staticmethod
    def gen_ext_code_data(address, start, end):
        return f'bytecode_{address}_{start}_{end}'

    @staticmethod
    def gen_code_size_var(address):
        return f'codeSize_{address}'

    @staticmethod
    def gen_code_hash_var(address):
        return f'codeHash_{address}'

    @staticmethod
    def gen_return_data(pc, start, end, path_id):
        return f'return_{pc}_{start}_{end}_{path_id}'

    @staticmethod
    def gen_data_var(start, end, function):
        return f'inputData_{start}_{end}_{function}'

    @staticmethod
    def gen_data_size():
        return 'inputSize'

    @staticmethod
    def gen_storage_var(position):
        return f'state_{position}'

    @staticmethod
    def gen_exp_var(v0, v1):
        return f'exp_({v0}, {v1})'

    @staticmethod
    def gen_sha3_var(value):
        return f'sha3_({value})'

    @staticmethod
    def gen_gas_price_var():
        return 'gasPrice'

    @staticmethod
    def gen_origin_var():
        return 'origin'

    @staticmethod
    def gen_blockhash(number):
        return f'blockhash_{number}'

    @staticmethod
    def gen_coin_base():
        return 'coinbase'

    @staticmethod
    def gen_difficult():
        return 'difficulty'

    @staticmethod
    def gen_gas_limit():
        return 'gasLimit'

    @staticmethod
    def gen_chain_id():
        return 'chainId'

    @staticmethod
    def gen_base_fee():
        return 'baseFee'

    @staticmethod
    def gen_number():
        return 'blockNumber'

    @staticmethod
    def gen_timestamp():
        return 'timestamp'

    def gen_path_id(self):
        self.path += 1
        return str(self.path)

    def get_path_id(self):
        return str(self.path)

    @staticmethod
    def gen_mem_var(pc):
        return f'mem_{pc}'

    @staticmethod
    def gen_gas_var(pc):
        return f'gas_{pc}'

    @staticmethod
    def gen_return_status(pc):
        return f'returnStatus_{pc}'
