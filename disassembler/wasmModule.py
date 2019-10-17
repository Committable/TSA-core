import typing
from disassembler import wasmConvention
import num
import log
import io

from disassembler.wasmConvention import opcodes


def read_count(reader, maxbits=32, signed=False) -> int:
    return num.leb(reader, maxbits, signed)[1]


def read_bytes(reader, maxbits=32, signed=False) -> bytearray:
    n = read_count(reader, maxbits, signed)
    return bytearray(reader.read(n))

class Module:
    def __init__(self):
        self.functions_name = {}
        self.module_name: str = ""
        self.locals_name = {}
        self.types: typing.List[FunctionType] = []
        self.funcs: typing.List[Function] = []
        self.tables: typing.List[Table] = []
        self.mems: typing.List[Memory] = []
        self.globals: typing.List[Global] = []
        self.elem: typing.List[ElementSegment] = []
        self.data: typing.List[DataSegment] = []
        self.start: int = None
        self.imports: typing.List[Import] = []
        self.exports: typing.List[Export] = []

    @classmethod
    def load(cls, name: str) -> 'Module':
        with open(name, 'rb') as f:
            return cls.from_reader(f)

    @classmethod
    def from_reader(cls, r: typing.BinaryIO) -> 'Module':
        if list(r.read(4)) != [0x00, 0x61, 0x73, 0x6d]:
            raise Exception('pywasm: invalid magic number')
        if list(r.read(4)) != [0x01, 0x00, 0x00, 0x00]:
            raise Exception('pywasm: invalid version')
        mod = Module()
        log.debugln('Sections:')
        log.debugln()
        while True:
            section_id_byte = r.read(1)
            if not section_id_byte:
                break
            section_id = ord(section_id_byte)
            n = read_count(r, 32)
            data = r.read(n)
            if len(data) != n:
                raise Exception('pywasm: invalid section size')
            if section_id == wasmConvention.custom_section:
                custom_section = CustomSection.from_reader(io.BytesIO(data))
                log.debugln(f'{wasmConvention.section[section_id][0]:>9} {custom_section.name}')
                mod.module_name = custom_section.module_name
                mod.functions_name = custom_section.function_names.func_names
                for i in custom_section.local_names:
                    mod.locals_name[i.func_index] = i.local_name
            elif section_id == wasmConvention.type_section:
                type_section = TypeSection.from_reader(io.BytesIO(data))
                for i, e in enumerate(type_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.types = type_section.vec
            elif section_id == wasmConvention.import_section:
                import_section = ImportSection.from_reader(io.BytesIO(data))
                for i, e in enumerate(import_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.imports = import_section.vec
            elif section_id == wasmConvention.function_section:
                function_section = FunctionSection.from_reader(io.BytesIO(data))
                num_imported_funcs = sum(1 for _ in filter(lambda i: i.kind == wasmConvention.extern_func, mod.imports))
                for i, e in enumerate(function_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] func={num_imported_funcs+i} sig={e}')
            elif section_id == wasmConvention.table_section:
                table_section = TableSection.from_reader(io.BytesIO(data))
                for i, e in enumerate(table_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.tables = table_section.vec
            elif section_id == wasmConvention.memory_section:
                memory_section = MemorySection.from_reader(io.BytesIO(data))
                for i, e in enumerate(memory_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.mems = memory_section.vec
            elif section_id == wasmConvention.global_section:
                global_section = GlobalSection.from_reader(io.BytesIO(data))
                for i, e in enumerate(global_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.globals = global_section.vec
            elif section_id == wasmConvention.export_section:
                export_section = ExportSection.from_reader(io.BytesIO(data))
                for i, e in enumerate(export_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.exports = export_section.vec
            elif section_id == wasmConvention.start_section:
                start_section = StartSection.from_reader(io.BytesIO(data))
                log.debugln(f'{wasmConvention.section[section_id][0]:>12} {start_section.start_function}')
                mod.start = start_section.start_function.funcidx
            elif section_id == wasmConvention.element_section:
                element_section = ElementSection.from_reader(io.BytesIO(data))
                for i, e in enumerate(element_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.elem = element_section.vec
            elif section_id == wasmConvention.code_section:
                code_section = CodeSection.from_reader(io.BytesIO(data))

                def printex(instrs: typing.List[Instruction], prefix=0):
                    for e in instrs:
                        a = f'           | {" " * prefix}{wasmConvention.opcodes[e.code][0]}'
                        if e.code in [wasmConvention.block, wasmConvention.loop, wasmConvention.if_]:
                            log.debugln(f'{a} {wasmConvention.blocktype[e.immediate_arguments][0]}')
                            prefix += 2
                        elif e.code == wasmConvention.end:
                            prefix -= 2
                            a = f'           | {" " * prefix}{wasmConvention.opcodes[e.code][0]}'
                            log.debugln(f'{a}')
                        elif e.immediate_arguments is None:
                            log.debugln(f'{a}')
                        elif isinstance(e.immediate_arguments, list):
                            log.debugln(f'{a} {" ".join([str(e) for e in e.immediate_arguments])}')
                        else:
                            log.debugln(f'{a} {e.immediate_arguments}')

                num_imported_funcs = sum(1 for _ in filter(lambda i: i.kind == wasmConvention.extern_func, mod.imports))
                for i, e in enumerate(code_section.vec):
                    log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] func={num_imported_funcs+i} {e}')
                    printex(e.expr.data)
                    func = Function()
                    func.typeidx = function_section.vec[i]
                    func.locals = e.locals
                    func.expr = e.expr
                    mod.funcs.append(func)
            elif section_id == wasmConvention.data_section:
                data_section = DataSection.from_reader(io.BytesIO(data))
                # for i, e in enumerate(data_section.vec):
                #     log.debugln(f'{wasmConvention.section[section_id][0]:>9}[{i}] {e}')
                mod.data = data_section.vec
            else:
                raise Exception('pywasm: invalid section id')
        log.debugln('')
        return mod

class FunctionType:
    # Function types are encoded by the byte 0x60 followed by the respective vectors of parameter and result types.
    #
    # functype ::= 0x60 t1∗:vec(valtype) t2∗:vec(valtype) ⇒ [t1∗] → [t2∗]
    def __init__(self):
        self.args: typing.List[int]
        self.rets: typing.List[int]

    def __repr__(self):
        args = [wasmConvention.valtype[i][0] for i in self.args]
        rets = [wasmConvention.valtype[i][0] for i in self.rets]
        a = ', '.join(args)
        if rets:
            b = rets[0]
            return f'({a}) -> {b}'
        return f'({a})'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = FunctionType()
        assert ord(r.read(1)) == 0x60
        o.args = read_bytes(r)
        o.rets = read_bytes(r)
        return o

class Function:
    # The funcs component of a module defines a vector of functions with the following structure:
    #
    # func ::= {type typeidx, locals vec(valtype), body expr}
    #
    # The type of a function declares its signature by reference to a type defined in the module. The parameters of the
    # function are referenced through 0-based local indices in the function’s body; they are mutable.
    #
    # The locals declare a vector of mutable local variables and their types. These variables are referenced through
    # local indices in the function’s body. The index of the first local is the smallest index not referencing a
    # parameter.
    #
    # The body is an instruction sequence that upon termination must produce a stack matching the function type’s
    # result type.
    #
    # Functions are referenced through function indices, starting with the smallest index not referencing
    # a function import.
    def __init__(self):
        self.typeidx: int
        self.locals: typing.List[int] = []
        self.expr: Expression

class Instruction:
    # Instructions are encoded by opcodes. Each opcode is represented by a single byte, and is followed by the
    # instruction’s immediate arguments, where present. The only exception are structured control instructions,
    # which consist of several opcodes bracketing their nested instruction sequences.
    def __init__(self, code: int, immediate_arguments=None):
        self.code = code
        self.immediate_arguments = immediate_arguments
        self.offset = 0
        self.xref = []

    def __repr__(self):
        if self.immediate_arguments is None:
            return f'{wasmConvention.opcodes[self.code][0]}'
        return f'{wasmConvention.opcodes[self.code][0]} {self.immediate_arguments}'

    def set_offset(self,offset):
        self.offset = offset

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        code_byte = r.read(1)
        if not code_byte:
            return None
        code = ord(code_byte)
        code_size = wasmConvention.opcodes[code][1]
        if code_size == '':
            immediate_arguments = None
        elif code_size == 'u8':
            immediate_arguments = read_count(r, 8)
        elif code_size == 'u32':
            immediate_arguments = read_count(r, 32)
        elif code_size == 'i32':
            immediate_arguments = num.int2i32(read_count(r, 32, signed=True))
        elif code_size == 'i64':
            immediate_arguments = num.int2i64(read_count(r, 64, signed=True))
        elif code_size == 'f32':
            immediate_arguments = num.LittleEndian.f32(r.read(4))
        elif code_size == 'f64':
            immediate_arguments = num.LittleEndian.f64(r.read(8))
        elif code_size == 'u32,u8':
            immediate_arguments = [read_count(r, 32), read_count(r, 8)]
        elif code_size == 'u32,u32':
            immediate_arguments = [read_count(r, 32) for _ in range(2)]
        elif code == wasmConvention.br_table:
            n = read_count(r, 32)
            a = [read_count(r, 32) for _ in range(n)]
            b = read_count(r, 32)
            immediate_arguments = [a, b]
        else:
            raise Exception('pywasm: invalid code size')
        return Instruction(code, immediate_arguments)

    # @property
    # def is_control(self):
    #     return self.code >= wasmConvention.unreachable and self.code <= wasmConvention.call_indirect
    #
    # @property
    # def is_parametric(self):
    #     return self.group == 'Parametric'
    #
    # @property
    # def is_variable(self):
    #     return self.group == 'Variable'
    #
    # @property
    # def is_memory(self):
    #     return self.group == 'Memory'
    #
    # @property
    # def is_constant(self):
    #     return self.group == 'Constant'
    #
    # @property
    # def is_logical_i32(self):
    #     return self.group == 'Logical_i32'
    #
    # @property
    # def is_logical_i64(self):
    #     return self.group == 'Logical_i64'
    #
    # @property
    # def is_logical_f32(self):
    #     return self.group == 'Logical_f32'
    #
    # @property
    # def is_logical_f64(self):
    #     return self.group == 'Logical_f64'
    #
    # @property
    # def is_arithmetic_i32(self):
    #     return self.group == 'Arithmetic_i32'
    #
    # @property
    # def is_bitwise_i32(self):
    #     return self.group == 'Bitwise_i32'
    #
    # @property
    # def is_arithmetic_i64(self):
    #     return self.group == 'Arithmetic_i64'
    #
    # @property
    # def is_bitwise_i64(self):
    #     return self.group == 'Bitwise_i64'
    #
    # @property
    # def is_arithmetic_f32(self):
    #     return self.group == 'Arithmetic_f32'
    #
    # @property
    # def is_arithmetic_f64(self):
    #     return self.group == 'Arithmetic_f64'
    #
    # @property
    # def is_conversion(self):
    #     return self.group == 'Conversion'

    @property
    def is_branch_conditional(self):
        """ Return True if the instruction is a conditional jump """
        return opcodes[self.code][0] in ['br_if', 'br_table', 'if']

    @property
    def is_branch_unconditional(self):
        """ Return True if the instruction is a unconditional jump """
        return opcodes[self.code][0] in ['br']

    @property
    def is_call(self):
        """ True if the instruction is a call instruction """
        return opcodes[self.code][0] in ['call', 'call_indirect']

    @property
    def is_branch(self):
        return self.is_branch_conditional or self.is_branch_unconditional

    @property
    def is_halt(self):
        """ Return True if the instruction is a branch terminator """
        return opcodes[self.code][0] in ['unreachable', 'return']

    @property
    def is_terminator(self):
        """ True if the instruction is a basic block terminator """
        return self.is_branch or self.is_halt

    @property
    def is_block_starter(self):
        """ Return True if the instruction is a basic block starter """
        return opcodes[self.code][0] in ['block', 'loop', 'if', 'else']

    @property
    def is_block_terminator(self):
        """ Return True if the instruction is a basic block terminator """
        return opcodes[self.code][0] in ['else', 'end']

class Expression:
    # Function bodies, initialization values for globals, and offsets of element or data segments are given as
    # expressions, which are sequences of instructions terminated by an end marker.
    #
    # expr ::= instr∗ end
    #
    # In some places, validation restricts expressions to be constant, which limits the set of allowable instructions.
    def __init__(self):
        self.data: typing.List[Instruction] = []
        self.composition = {}

    def __str__(self):
        return str(self.data)

    @classmethod
    def compose(cls, data: typing.List[Instruction]):
        composition = {}
        stack = []
        for i, instr in enumerate(data):
            code = instr.code
            if code in [wasmConvention.block, wasmConvention.loop, wasmConvention.if_]:
                stack.append([i])
                continue
            if code == wasmConvention.else_:
                stack[-1].append(i)
                continue
            if code == wasmConvention.end:
                if i == len(data) - 1:
                    break
                block = stack.pop()
                block.append(i)
                composition[block[0]] = block
                continue
        if data[-1].code != wasmConvention.end:
            raise Exception('pywasm: function block did not end with 0xb')
        if stack:
            raise Exception('pywasm: function ended in middle of block')
        return composition

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Expression()
        d = 1
        offset = 0
        while True:
            i = Instruction.from_reader(r)
            i.set_offset(offset)
            offset += 1
            if not i:
                break
            o.data.append(i)
            if i.code in [wasmConvention.block, wasmConvention.loop, wasmConvention.if_]:
                d += 1
            if i.code == wasmConvention.end:
                d -= 1
            if d == 0:
                break
        o.composition = cls.compose(o.data)
        return o



class Table:
    # The tables component of a module defines a vector of tables described by their table type:
    #
    # table ::= {type tabletype}
    def __init__(self):
        self.tabletype: TableType

    def __repr__(self):
        return f'{wasmConvention.elemtype[self.tabletype.elemtype][0]} {self.tabletype.limits}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Table()
        o.tabletype = TableType.from_reader(r)
        return o

class TableType:
    # Table types classify tables over elements of element types within a size range.
    #
    # tabletype ::= limits elemtype
    # elemtype ::= funcref
    #
    # Like memories, tables are constrained by limits for their minimum and optionally maximum size. The limits are
    # given in numbers of entries. The element type funcref is the infinite union of all function types. A table of that
    # type thus contains references to functions of heterogeneous type.

    def __init__(self):
        self.limits: Limits
        self.elemtype: int

    def __repr__(self):
        a = wasmConvention.elemtype[self.elemtype][0]
        return f'{a} {self.limits}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = TableType()
        o.elemtype = ord(r.read(1))
        o.limits = Limits.from_reader(r)
        return o

class Limits:
    # Limits are encoded with a preceding flag indicating whether a maximum is present.
    #
    # limits ::= 0x00  n:u32        ⇒ {min n,max ϵ}
    #          | 0x01  n:u32  m:u32 ⇒ {min n,max m}
    def __init__(self, minimum: int, maximum: int = None):
        self.minimum = minimum
        self.maximum = maximum

    def __repr__(self):
        if self.maximum:
            return f'minimum={self.minimum} maximum={self.maximum}'
        return f'minimum={self.minimum}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        flag = ord(r.read(1))
        minimum = read_count(r)
        maximum = read_count(r) if flag else None
        return Limits(minimum, maximum)

class Memory:
    # The mems component of a module defines a vector of linear memories (or memories for short) as described by their
    # memory type:
    #
    # mem ::= {type memtype}
    def __init__(self):
        self.memtype: MemoryType

    def __repr__(self):
        return f'{self.memtype}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Memory()
        o.memtype = MemoryType.from_reader(r)
        return o

class MemoryType:
    # Memory types classify linear memories and their size range.
    #
    # memtype ::= limits
    #
    # The limits constrain the minimum and optionally the maximum size of a memory. The limits are given in units of
    # page size.
    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        return Limits.from_reader(r)

class Global:
    # The globals component of a module defines a vector of global variables (or globals for short):
    #
    # global ::= {type globaltype, init expr}
    def __init__(self):
        self.globaltype: GlobalType
        self.expr: Expression

    def __repr__(self):
        return f'{self.globaltype} expr={self.expr}>'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Global()
        o.globaltype = GlobalType.from_reader(r)
        o.expr = Expression.from_reader(r)
        return o

class GlobalType:
    # Global types are encoded by their value type and a flag for their
    # mutability.
    #
    # globaltype ::= t:valtype m:mut ⇒ m t
    # mut ::= 0x00 ⇒ const
    #       | 0x01 ⇒ var
    def __init__(self):
        self.valtype: int
        self.mut: bool

    def __repr__(self):
        a = wasmConvention.valtype[self.valtype][0]
        if self.mut:
            return f'var {a}'
        return f'const {a}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = GlobalType()
        o.valtype = ord(r.read(1))
        o.mut = ord(r.read(1)) == 1
        return o

class ElementSegment:
    # The initial contents of a table is uninitialized. The elem component of a module defines a vector of element
    # segments that initialize a subrange of a table, at a given offset, from a static vector of elements.
    #
    # elem ::= {table tableidx, offset expr, init vec(funcidx)}
    #
    # The offset is given by a constant expression.
    def __init__(self):
        self.tableidx: int
        self.expr: Expression
        self.init: typing.List[int]

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = ElementSegment()
        o.tableidx = read_count(r, 32)
        o.expr = Expression.from_reader(r)
        n = read_count(r, 32)
        o.init = [read_count(r, 32) for _ in range(n)]
        return o

class DataSegment:
    # The initial contents of a memory are zero-valued bytes. The data component of a module defines a vector of data
    # segments that initialize a range of memory, at a given offset, with a static vector of bytes.
    #
    # data::={data memidx,offset expr,init vec(byte)}
    #
    # The offset is given by a constant expression.
    def __init__(self):
        self.memidx: int
        self.expr: Expression
        self.init: bytearray

    def __repr__(self):
        return self.init[:32].decode()

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = DataSegment()
        o.memidx = read_count(r, 32)
        o.expr = Expression.from_reader(r)
        o.init = bytearray(read_bytes(r, 32))
        return o

class Import:
    # The imports component of a module defines a set of imports that are required for instantiation.
    #
    # import ::= {module name, name name, desc importdesc}
    # importdesc ::= func typeidx | table tabletype | mem memtype | global globaltype
    #
    # Each import is labeled by a two-level name space, consisting of a module name and a name for an entity within
    # that module. Importable definitions are functions, tables, memories, and globals. Each import is specified by a
    # descriptor with a respective type that a definition provided during instantiation is required to match. Every
    # import defines an index in the respective index space. In each index space, the indices of imports go before the
    # first index of any definition contained in the module itself.
    def __init__(self):
        self.module: str
        self.name: str
        self.kind: int
        self.desc = None

    def __repr__(self):
        if self.kind == wasmConvention.extern_func:
            return f'{self.module}.{self.name} -> Function[{self.desc}]'
        if self.kind == wasmConvention.extern_table:
            return f'{self.module}.{self.name} -> Table[{self.desc}]'
        if self.kind == wasmConvention.extern_mem:
            return f'{self.module}.{self.name} -> Memory[{self.desc}]'
        if self.kind == wasmConvention.extern_global:
            return f'{self.module}.{self.name} -> Global[{self.desc}]'
        return f'{self.module}.{self.name}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Import()
        o.module = read_bytes(r, 32).decode()
        o.name = read_bytes(r, 32).decode()
        o.kind = ord(r.read(1))
        if o.kind == wasmConvention.extern_func:
            o.desc = read_count(r, 32)
        elif o.kind == wasmConvention.extern_table:
            o.desc = TableType.from_reader(r)
        elif o.kind == wasmConvention.extern_mem:
            o.desc = MemoryType.from_reader(r)
        elif o.kind == wasmConvention.extern_global:
            o.desc = GlobalType.from_reader(r)
        else:
            raise Exception('pywasm: malformed')
        return o

class Export:
    # The exports component of a module defines a set of exports that become accessible to the host environment once
    # the module has been instantiated.
    #
    # export ::= {name name, desc exportdesc}
    # exportdesc ::= func funcidx | table tableidx | mem memidx | global globalidx
    #
    # Each export is labeled by a unique name. Exportable definitions are functions, tables, memories, and globals,
    # which are referenced through a respective descriptor.
    def __init__(self):
        self.name: str
        self.kind: int
        self.desc = None

    def __repr__(self):
        if self.kind == wasmConvention.extern_func:
            return f'{self.name} -> Function[{self.desc}]'
        if self.kind == wasmConvention.extern_table:
            return f'{self.name} -> Table[{self.desc}]'
        if self.kind == wasmConvention.extern_mem:
            return f'{self.name} -> Memory[{self.desc}]'
        if self.kind == wasmConvention.extern_global:
            return f'{self.name} -> Global[{self.desc}]'
        return f'{self.name}'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Export()
        o.name = read_bytes(r, 32).decode()
        o.kind = ord(r.read(1))
        o.desc = read_count(r, 32)
        return o

class CustomSection:
    # Custom sections have the id 0. They are intended to be used for debugging
    # information or third-party extensions, and are ignored by the WebAssembly
    # semantics. Their contents consist of a name further identifying the custom
    # section, followed by an uninterpreted sequence of bytes for custom use.
    #
    # customsec ::= section0(custom)
    # custom ::= name byte∗
    def __init__(self):
        self.name: str = ""
        self.module_name = ""
        self.function_names: FunctionName = {}
        self.local_names: typing.List[LocalsName] = []
        self.data: bytearray = None

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = CustomSection()
        n = read_count(r, 32)
        o.name = r.read(n).decode()
        try:
            while True:
                t = read_count(r,7)
                n = read_count(r, 32)
                if t == 0:
                    l = read_count(r, 32)
                    o.module_name = r.read(l).decode()
                elif t == 1:
                    o.function_names = FunctionName.from_reader(r)
                elif t == 2:
                    n = read_count(r, 32)
                    o.local_names = [LocalsName.from_reader(r) for _ in range(n)]
        except:
            return o

        return o

class FunctionName:
    def __init__(self):
        self.func_names = {}

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = FunctionName()
        n = read_count(r, 32)
        for i in range(n):
            index = read_count(r, 32)
            l = read_count(r, 32)
            o.func_names[index] = r.read(l).decode()
        return o

class LocalsName:
    def __init__(self):
        self.func_index = None
        self.local_name = {}


    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = LocalsName()
        o.func_index = read_count(r, 32)
        n = read_count(r, 32)
        for i in range(n):
            index = read_count(r, 32)
            l = read_count(r, 32)
            o.local_name[index] = r.read(l).decode()

        return o



class TypeSection:
    # The type section has the id 1. It decodes into a vector of function
    # types that represent the types component of a module.
    #
    # typesec ::= ft∗:section1(vec(functype)) ⇒ ft∗

    def __init__(self):
        self.vec: typing.List[FunctionType] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = TypeSection()
        n = read_count(r, 32)
        o.vec = [FunctionType.from_reader(r) for _ in range(n)]
        return o

class ImportSection:
    # The import section has the id 2. It decodes into a vector of imports
    # that represent the imports component of a module.
    #
    # importsec ::= im∗:section2(vec(import)) ⇒ im∗
    # import ::= mod:name nm:name d:importdesc ⇒ {module mod, name nm, desc d}
    # importdesc ::= 0x00 x:typeidx ⇒ func x
    #              | 0x01 tt:tabletype ⇒ table tt
    #              | 0x02 mt:memtype ⇒ mem mt
    #              | 0x03 gt:globaltype ⇒ global gt

    def __init__(self):
        self.vec: typing.List[Import] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = ImportSection()
        n = read_count(r, 32)
        o.vec = [Import.from_reader(r) for _ in range(n)]
        return o

class FunctionSection:
    # The function section has the id 3. It decodes into a vector of type
    # indices that represent the type fields of the functions in the funcs
    # component of a module. The locals and body fields of the respective
    # functions are encoded separately in the code section.
    #
    # funcsec ::= x∗:section3(vec(typeidx)) ⇒ x∗

    def __init__(self):
        self.vec: typing.List[int] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = FunctionSection()
        n = read_count(r, 32)
        o.vec = [read_count(r, 32) for _ in range(n)]
        return o

class TableSection:
    # The table section has the id 4. It decodes into a vector of tables that
    # represent the tables component of a module.
    #
    # tablesec ::= tab∗:section4(vec(table)) ⇒ tab∗
    # table ::= tt:tabletype ⇒ {type tt}

    def __init__(self):
        self.vec: typing.List[Table] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = TableSection()
        n = read_count(r, 32)
        o.vec = [Table.from_reader(r) for _ in range(n)]
        return o

class MemorySection:
    # The memory section has the id 5. It decodes into a vector of memories
    # that represent the mems component of a module.
    #
    # memsec ::= mem∗:section5(vec(mem)) ⇒ mem∗
    # mem ::= mt:memtype ⇒ {type mt}

    def __init__(self):
        self.vec: typing.List[Memory] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = MemorySection()
        n = read_count(r, 32)
        o.vec = [Memory.from_reader(r) for _ in range(n)]
        return o

class GlobalSection:
    # The global section has the id 6. It decodes into a vector of globals
    # that represent the globals component of a module.
    #
    # globalsec ::= glob*:section6(vec(global)) ⇒ glob∗
    # global ::= gt:globaltype e:expr ⇒ {type gt, init e}

    def __init__(self):
        self.vec: typing.List[Global] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = GlobalSection()
        n = read_count(r, 32)
        o.vec = [Global.from_reader(r) for _ in range(n)]
        return o

class ExportSection:
    # The export section has the id 7. It decodes into a vector of exports
    # that represent the exports component of a module.
    #
    # exportsec ::= ex∗:section7(vec(export)) ⇒ ex∗
    # export :: =nm:name d:exportdesc ⇒ {name nm, desc d}
    # exportdesc ::= 0x00 x:funcidx ⇒ func x
    #              | 0x01 x:tableidx ⇒ table x
    #              | 0x02 x:memidx ⇒ mem x
    #              | 0x03 x:globalidx⇒global x

    def __init__(self):
        self.vec: typing.List[Export] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = ExportSection()
        n = read_count(r, 32)
        o.vec = [Export.from_reader(r) for _ in range(n)]
        return o

class StartSection:
    # The start section has the id 8. It decodes into an optional start
    # function that represents the start component of a module.
    #
    # startsec ::= st?:section8(start) ⇒ st?
    # start ::= x:funcidx ⇒ {func x}

    def __init__(self):
        self.start_function: StartFunction

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = StartSection()
        o.start_function = StartFunction.from_reader(r)
        return o

class StartFunction:
    # The start component of a module declares the function index of a start function that is automatically invoked
    # when the module is instantiated, after tables and memories have been initialized.
    #
    # start ::= {func funcidx}
    def __init__(self):
        self.funcidx: int

    def __repr__(self):
        return f'Function[{self.funcidx}]'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = StartFunction()
        o.funcidx = read_count(r, 32)
        return o

class ElementSection:
    # The element section has the id 9. It decodes into a vector of element
    # segments that represent the elem component of a module.
    #
    # elemsec ::= seg∗:section9(vec(elem)) ⇒ seg
    # elem ::= x:tableidx e:expr y∗:vec(funcidx) ⇒ {table x, offset e, init y∗}
    def __init__(self):
        self.vec: typing.List[ElementSegment]

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = ElementSection()
        n = read_count(r, 32)
        o.vec = [ElementSegment.from_reader(r) for _ in range(n)]
        return o

class CodeSection:
    # The code section has the id 10. It decodes into a vector of code
    # entries that are pairs of value type vectors and expressions. They
    # represent the locals and body field of the functions in the funcs
    # component of a module. The type fields of the respective functions are
    # encoded separately in the function section.
    def __init__(self):
        self.vec: typing.List[Code] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = CodeSection()
        n = read_count(r, 32)
        o.vec = [Code.from_reader(r) for _ in range(n)]
        return o

class Code:
    # The encoding of each code entry consists of
    #   - the u32 size of the function code in bytes
    #   - the actual function code, which in turn consists of
    #       - the declaration of locals
    #      -  the function body as an expression.
    #
    # Local declarations are compressed into a vector whose entries consist of
    #   - a u32 count
    #   - a value type.
    #
    # code ::= size:u32 code:func ⇒ code(ifsize=||func||)
    # func ::= (t∗)∗:vec(locals) e:expr ⇒ concat((t∗)∗), e∗(if|concat((t∗)∗)|<232)
    # locals ::= n:u32 t:valtype ⇒ tn
    def __init__(self):
        self.locals: typing.List[int] = []
        self.expr: Expression

    def __repr__(self):
        return f'locals=[{", ".join([wasmConvention.valtype[i][0] for i in self.locals])}]'

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Code()
        n = read_count(r, 32)
        n = read_count(r, 32)
        for _ in range(n):
            l = Locals.from_reader(r)
            o.locals.extend([l.valtype for _ in range(l.n)])
        o.expr = Expression.from_reader(r)
        return o

class Locals:
    # The locals declare a vector of mutable local variables and their types. These variables are referenced through
    # local indices in the function’s body. The index of the first local is the smallest index not referencing a
    # parameter.
    #
    # locals ::= n:u32 t:valtype ⇒ tn
    def __init__(self):
        self.n: int
        self.valtype: int

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = Locals()
        o.n = read_count(r, 32)
        o.valtype = ord(r.read(1))
        return o

class DataSection:
    # The data section has the id 11. It decodes into a vector of data
    # segments that represent the data component of a module.
    #
    # datasec ::= seg∗:section11(vec(data)) ⇒ seg
    # data ::= x:memidx e:expr b∗:vec(byte) ⇒ {data x,offset e,init b∗}
    def __init__(self):
        self.vec: typing.List[DataSegment] = []

    @classmethod
    def from_reader(cls, r: typing.BinaryIO):
        o = DataSection()
        n = read_count(r, 32)
        o.vec = [DataSegment.from_reader(r) for _ in range(n)]
        return o