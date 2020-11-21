import logging
import argparse
import json
import sys
import re
from os import path
from das_shared.object_base import LoggingObject
from das_shared.op_sys import full_path, run_exec, write_to_file
from das_shared.diag import log_on_exception
from das_keywords import DAS_KEYWORDS


APP_NAME = 'dasBinder'


class BinderError(Exception):
    pass


class Settings(object):

    def __init__(self, argv):
        self.__args = self.__parse_argv(argv=argv)

    @classmethod
    def __parse_argv(cls, argv):
        parser = argparse.ArgumentParser(
            description='Generates das::Module binding stuff from .h file.')
        parser.add_argument('--c_header_from', type=str, required=True,
            help='.h file to generate bindings from.')
        parser.add_argument('--module_to', type=str, required=True,
            help='.cpp file to write generated das::Module to.')
        parser.add_argument('--clang_c_exe', type=str, default='clang',
            help='Clang C compiler to use. Default: %(default)s')
        parser.add_argument('--include_dirs', type=str,
            help='Additional "include" directories to use.')
        parser.add_argument('--include_dirs_sep', type=str, default=';',
            help='Separator used in "--include_dirs".')
        parser.add_argument('--config', type=str, required=True,
            help='Path to binding config.')
        parser.add_argument('--log_level', type=str,
            choices=['debug', 'info', 'warning', 'error'],
            default='info', help='Logging level. Default: %(default)s')
        return parser.parse_args(argv)

    @property
    def log_level(self):
        return getattr(logging, self.__args.log_level.upper())

    @property
    def module_to(self):
        return full_path(self.__args.module_to)

    @property
    def c_header_from(self):
        return full_path(self.__args.c_header_from)

    @property
    def clang_c_exe(self):
        return self.__args.clang_c_exe

    @property
    def include_dirs(self):
        return self.__args.include_dirs.split(self.__args.include_dirs_sep)

    @property
    def config_fpath(self):
        return full_path(self.__args.config)


class Binder(LoggingObject):

    def __init__(self, argv):
        self.__settings = Settings(argv=argv[1:])
        self.__config = self.__read_config(self.__settings.config_fpath)
        self.__main_c_header = C_TranslationUnit(
            c_src_fpath=self.__settings.c_header_from,
            clang_c_exe=self.__settings.clang_c_exe,
            include_dirs=self.__settings.include_dirs,
            config=self.__config)
        self.__raw_c_headers = [C_HeaderRaw(fpath=fpath, config=self.__config)
            for fpath in self.__raw_c_headers_fpaths]

    @property
    def __raw_c_headers_fpaths(self):
        for headers in [
            self.__config.c_headers_to_extract_macro_consts_from,
        ]:
            for header in headers:
                if path.isabs(header):
                    yield full_path(header)
                else:
                    for include_dir in self.__settings.include_dirs:
                        full_header_fpath = full_path(path.join(
                            include_dir, header))
                        if path.exists(full_header_fpath):
                            yield full_header_fpath
                            break
                    else:
                        raise BinderError(f'Cannot find header {header} in '
                            f'any of the include directories.')

    @property
    def __macro_consts(self):
        for header in self.__raw_c_headers:
            for macro_const in header.macro_consts:
                yield macro_const

    @property
    def __enums(self):
        return self.__main_c_header.enums

    @property
    def __structs(self):
        return self.__main_c_header.structs

    @property
    def __opaque_structs(self):
        return self.__main_c_header.opaque_structs

    @property
    def __functions(self):
        return self.__main_c_header.functions

    @property
    def __ast(self):
        return self.__main_c_header.root

    def run(self):
        logging.basicConfig(level=self.__settings.log_level,
            format='%(asctime)s [%(levelname)s:%(name)s] %(message)s')
        self._log_info(f'Generating bindings for '
            f'{self.__settings.c_header_from}')
        self.__maybe_save_ast()
        write_to_file(fpath=self.__settings.module_to,
            content='\n'.join(self.__generate_module() + ['']))
        self._log_info(f'Wrote generated das::Module to '
            f'{self.__settings.module_to}')
        self._log_info('Finished successfully.')

    def __maybe_save_ast(self):
        if not self.__config.save_ast:
            return
        ast_fpath = self.__settings.module_to + '.ast.json'
        write_to_file(fpath=ast_fpath, content=json.dumps(self.__ast,
            indent=4, sort_keys=True))
        self._log_info(f'Wrote AST for C header to {ast_fpath}')

    def __read_config(self, config_fpath):
        cfg_globals = {}
        try:
            with open(config_fpath, 'r') as f:
                cfg_py = f.read()
        except IOError:
            raise BinderError(f'Could not read config file: {config_fpath}')
        exec(cfg_py, cfg_globals)
        config_class = cfg_globals.get('Config')
        if config_class is None:
            raise BinderError(f'Config file must define "Config" class.')
        return config_class()

    def __generate_module(self):
        lines = []
        module = self.__config.das_module_name
        lines += [
           f'// generated by {APP_NAME}',
            '',
        ]
        lines += [
            '',
            '//',
            '// enums',
            '//',
            ''] + [
            line for enum in self.__enums
                for line in enum.generate_decl()
        ]
        lines += [
            '',
            '//',
            '// opaque structs',
            '//',
            ''] + [
            line for struct in self.__opaque_structs
                for line in struct.generate_decl()
        ]
        lines += [
            '',
            '//',
            '// structs',
            '//',
            ''] + [
            line for struct in self.__structs
                for line in struct.generate_decl()
        ]
        lines += [
            '',
           f'class Module_{module} : public Module {{',
            'public:',
           f'    Module_{module}() : Module("{module}") {{',
            '        ModuleLibrary lib;',
            '        lib.addModule(this);',
            '        lib.addBuiltInModule();'
        ]
        lines += [
            '',
            '        //',
            '        // enums',
            '        //',
            ''] + [
           f'        {line}' for enum in self.__enums
                        for line in enum.generate_add()
        ]
        lines += [
            '',
            '        //',
            '        // opaque structs',
            '        //',
            ''] + [
           f'        {line}' for struct in self.__opaque_structs
                        for line in struct.generate_add()
        ]
        lines += [
            '',
            '        //',
            '        // structs',
            '        //',
            ''] + [
           f'        {line}' for struct in self.__structs
                        for line in struct.generate_add()
        ]
        lines += [
            '',
            '        //',
            '        // functions',
            '        //',
            ''] + [
           f'        {line}' for function in self.__functions
                        for line in function.generate_add()
        ]
        lines += [
            '',
            '        //',
            '        // macro constants',
            '        //',
            ''] + [
           f'        {line}' for const in self.__macro_consts
                        for line in const.generate_add()
        ]
        lines += [
            '    }',
            '};',
            '',
            f'REGISTER_MODULE(Module_{module});',
        ]
        return lines


class C_TranslationUnit(LoggingObject):

    def __init__(self, c_src_fpath, clang_c_exe, include_dirs, config):
        cmd = []
        cmd += [clang_c_exe, '-cc1', '-ast-dump=json']
        for dpath in include_dirs:
            cmd += [f'-I{dpath}']
        cmd += [c_src_fpath]
        out, err, exit_code = run_exec(cmd)
        self.__root = json.loads(out)
        self.__config = config
        self.__cached_enums = None
        self.__cached_structs = None
        self.__cached_opaque_structs = None
        self.__cached_functions = None

    def __get_nodes(self, node_class, configure_fn):
        for inner in self.__root['inner']:
            with log_on_exception(inner=inner):
                node = node_class.maybe_create(
                    root=inner, config=self.__config)
                if node is None or node.is_builtin:
                    continue
                configure_fn(node)
                if not node.is_ignored:
                    yield node

    @property
    def root(self):
        return self.__root

    @property
    def enums(self):
        if self.__cached_enums is None:
            self.__cached_enums = list(self.__get_nodes(node_class=C_Enum,
                configure_fn=self.__config.configure_enum))
        return self.__cached_enums

    @property
    def structs(self):
        if self.__cached_structs is None:
            self.__cached_structs = list(self.__get_nodes(node_class=C_Struct,
                configure_fn=self.__config.configure_struct))
        return self.__cached_structs

    @property
    def opaque_structs(self):
        if self.__cached_opaque_structs is None:
            regular_struct_names = set(s.name for s in self.structs)
            self.__cached_opaque_structs = [s for s in self.__get_nodes(
                node_class=C_OpaqueStruct,
                configure_fn=self.__config.configure_opaque_struct
            ) if s.name not in regular_struct_names]
        return self.__cached_opaque_structs

    @property
    def functions(self):
        if self.__cached_functions is None:
            self.__cached_functions = list(self.__get_nodes(
                node_class=C_Function,
                configure_fn=self.__config.configure_function))
        return self.__cached_functions


class C_Item(object):

    def __init__(self, config):
        self.__ignored = False
        self.__config = config

    def ignore(self):
        self.__ignored = True

    @property
    def config(self):
        return self.__config

    @property
    def is_ignored(self):
        return self.__ignored

    @property
    def is_builtin(self):
        return self.name.startswith('_')

    @property
    def name(self):
        raise NotImplementedError()

    def generate_decl(self):
        return []

    def generate_add(self):
        return []


class C_InnerNode(C_Item):

    def __init__(self, root, **kwargs):
        super(C_InnerNode, self).__init__(**kwargs)
        self.__root = root

    @property
    def root(self):
        return self.__root

    @property
    def type(self):
        t = self.root['type']
        return t.get('desugaredQualType', t['qualType'])
    
    @property
    def name(self):
        return self.root['name']

    @property
    def das_name(self):
        name = self.name
        if name in DAS_KEYWORDS:
            name += '_'
        return name


class C_Enum(C_InnerNode):

    @staticmethod
    def maybe_create(root, **kwargs):
        if root['kind'] == 'EnumDecl':
            return C_Enum(root=root, **kwargs)

    @property
    def fields(self):
        for inner in self.root['inner']:
            if inner['kind'] == 'EnumConstantDecl':
                yield inner['name']

    def generate_decl(self):
        lines = []
        lines += [f'DAS_BIND_ENUM_CAST({self.name});']
        lines += [f'DAS_BASE_BIND_ENUM({self.name}, {self.name}']
        lines += [f',   {f}' for f in self.fields]
        lines += [')']
        return lines

    def generate_add(self):
        return [f'addEnumeration(make_smart<Enumeration{self.name}>());']


class C_Struct(C_InnerNode):

    def __init__(self, **kwargs):
        super(C_Struct, self).__init__(**kwargs)
        self.__is_local = True
        self.__can_copy = True
        self.__can_move = True

    def set_is_local(self, is_local):
        self.__is_local = is_local

    def set_can_copy(self, can_copy):
        self.__can_copy = can_copy

    def set_can_move(self, can_move):
        self.__can_move = can_move

    @staticmethod
    def maybe_create(root, **kwargs):
        if (root['kind'] == 'RecordDecl'
            and root['tagUsed'] in ['struct', 'union']
            and 'inner' in root
            and 'name' in root
        ):
            return C_Struct(root=root, **kwargs)

    @property
    def fields(self):
        for inner in self.root['inner']:
            if inner['kind'] == 'FieldDecl':
                field = C_StructField(root=inner, config=self.config,
                    struct=self)
                self.config.configure_struct_field(field=field)
                if not field.is_ignored:
                    yield field

    def generate_decl(self):
        is_local = to_cpp_bool(self.__is_local)
        can_copy = to_cpp_bool(self.__can_copy)
        can_move = to_cpp_bool(self.__can_move)
        lines = []
        lines += [
            '',
           f'MAKE_TYPE_FACTORY({self.name}, {self.name});',
        ]
        for field in self.fields:
            if not field.is_bit_field:
                continue
            lines += [
                '',
               f'__forceinline {field.type} {field.getter_name}(const {self.name} &s) {{ return s.{field.name}; }}',
               f'__forceinline void {field.setter_name}({self.name} &s, {field.type} f) {{ s.{field.name} = f; }}',
            ]
        lines += [
            '',
           f'struct {self.name}Annotation',
           f': public ManagedStructureAnnotation<{self.name},true,true> {{',
           f'    {self.name}Annotation(ModuleLibrary & ml)',
           f'    : ManagedStructureAnnotation ("{self.name}", ml) {{',
        ]
        lines += [
           f'        addField<DAS_BIND_MANAGED_FIELD({f.name})>("{f.name}");'
                        for f in self.fields
                        if not f.is_bit_field and not f.is_self_ref
        ]
        lines += [
            '    }',
            '    void init() {',
        ]
        lines += [
           f'        addField<DAS_BIND_MANAGED_FIELD({f.name})>("{f.name}");'
                        for f in self.fields if f.is_self_ref
        ]
        lines += [
            '    }',
           f'    virtual bool isLocal() const override {{ return {is_local}; }}',
           f'    virtual bool canCopy() const override {{ return {can_copy}; }}',
           f'    virtual bool canMove() const override {{ return {can_move}; }}',
            '};'
        ]
        return lines

    def generate_add(self):
        lines = []
        lines += [
            f'addAnnotation(make_smart<{self.name}Annotation>(lib));',
        ]
        for field in self.fields:
            if not field.is_bit_field:
                continue
            lines += [
                '',
               f'addExtern<DAS_BIND_FUN({field.getter_name})>(*this, lib, "{field.getter_name}",',
                '    SideEffects::none, "{field.getter_name}");',
               f'addExtern<DAS_BIND_FUN({field.setter_name})>(*this, lib, "{field.setter_name}",',
                '    SideEffects::modifyArgument, "{field.setter_name}");',
            ]
        return lines


class C_OpaqueStruct(C_InnerNode):

    def __init__(self, **kwargs):
        super(C_OpaqueStruct, self).__init__(**kwargs)
        self.__annotation_type = 'ManagedValueAnnotation'
        self.__das_type = None
        self.__ptr_type = None

    def set_das_type(self, das_type):
        self.__das_type = das_type

    def define_ptr_type(self, ptr_type):
        self.__ptr_type = ptr_type

    def set_annotation_type(self, annotation):
        self.__annotation_type = annotation

    @staticmethod
    def maybe_create(root, **kwargs):
        if (root['kind'] == 'RecordDecl'
            and root['tagUsed'] in ['struct', 'union']
            and 'name' in root
            and 'inner' not in root
        ):
            return C_OpaqueStruct(root=root, **kwargs)

    @property
    def das_type(self):
        return self.__das_type or self.name

    def generate_decl(self):
        lines = []
        if self.__ptr_type is not None:
            lines += [
                f'typedef {self.name} * {self.__ptr_type};'
            ]
        lines += [
            f'MAKE_TYPE_FACTORY({self.das_type}, {self.das_type})',
        ]
        return lines

    def generate_add(self):
        t = self.das_type
        ann = self.__annotation_type
        return [
            f'addAnnotation(make_smart<{ann}<{t}>>("{t}", "{t}"));']


class C_StructField(C_InnerNode):

    def __init__(self, struct, **kwargs):
        super(C_StructField, self).__init__(**kwargs)
        self.__struct = struct

    @property
    def struct(self):
        return self.__struct

    @property
    def is_array(self):
        return '[' in self.type

    @property
    def is_bit_field(self):
        return self.root.get('isBitfield', False)

    @property
    def is_self_ref(self):
        return self.__struct.name in self.type.split()

    @property
    def setter_name(self):
        return f'{self.__struct.name}_set_{self.name}'

    @property
    def getter_name(self):
        return f'{self.__struct.name}_get_{self.name}'


class C_Function(C_InnerNode):

    @staticmethod
    def maybe_create(root, **kwargs):
        if root['kind'] == 'FunctionDecl':
            return C_Function(root=root, **kwargs)

    def generate_add(self):
        return [
            f'addExtern<DAS_BIND_FUN({self.name})>(*this, lib, "{self.name}",',
            f'    SideEffects::worstDefault, "{self.name}");',
        ]


class C_HeaderRaw(object):

    def __init__(self, fpath, config):
        with open(fpath, 'r') as f:
            self.__header_lines = [line for line in f]
        self.__config = config
        self.__cached_macro_consts = None

    def __get_items(self, item_class, configure_fn):
        for line in self.__header_lines:
            with log_on_exception(line=line):
                item = item_class.maybe_create(
                    line=line, config=self.__config)
                if item is None:
                    continue
                configure_fn(item)
                if not item.is_ignored:
                    yield item

    @property
    def macro_consts(self):
        if self.__cached_macro_consts is None:
            self.__cached_macro_consts = self.__get_items(
                item_class=C_MacroConst,
                configure_fn=self.__config.configure_macro_const)
        return self.__cached_macro_consts


class C_MacroConst(C_Item):

    def __init__(self, name, value, **kwargs):
        super(C_MacroConst, self).__init__(**kwargs)
        self.__name = name
        self.value = value

    @property
    def name(self):
        return self.__name

    @staticmethod
    def maybe_create(line, **kwargs):
        m = re.match(r'#define\s+([^\s(]+)\s+(\S+.*)$', line)
        if m is None:
            return
        name, value = m.groups()
        value = re.sub(r'//.*$', '', value)
        return C_MacroConst(name=name, value=value, **kwargs)

    def generate_add(self):
        return [
            f'addConstant(*this,"{self.name}",{self.value});'
        ]


def to_cpp_bool(b):
    return {True: 'true', False: 'false'}[b]
