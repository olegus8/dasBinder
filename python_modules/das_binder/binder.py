import logging
import argparse
import json
import sys
from os import path
from das_shared.object_base import LoggingObject
from das_shared.op_sys import full_path, run_exec, write_to_file
from das_shared.diag import log_on_exception


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
        self.__c_header = C_TranslationUnit(
            c_src_fpath=self.__settings.c_header_from,
            clang_c_exe=self.__settings.clang_c_exe,
            include_dirs=self.__settings.include_dirs,
            config=self.__config)

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
        write_to_file(fpath=ast_fpath, content=json.dumps(self.__c_header.root,
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
        include = self.__config.c_header_include
        lines += [
           f'// generated by {APP_NAME}',
            '',
            '#include "daScript/daScript.h"',
            '',
           f'#include "{include}"',
            '',
            'using namespace das;',
        ]
        lines += [
            '',
            '//',
            '// enums',
            '//',
            ''] + [
            line for enum in self.__c_header.enums
                for line in enum.generate_decl()
        ]
        lines += [
            '',
            '//',
            '// structs',
            '//',
            ''] + [
            line for struct in self.__c_header.structs
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
           f'        {line}' for enum in self.__c_header.enums
                        for line in enum.generate_add()
        ]
        lines += [
            '',
            '        //',
            '        // structs',
            '        //',
            ''] + [
           f'        {line}' for struct in self.__c_header.structs
                        for line in struct.generate_add()
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

    def __get_nodes(self, node_class, configure_fn):
        for inner in self.__root['inner']:
            with log_on_exception(inner=inner):
                node = node_class.maybe_create(
                    root=inner, config=self.__config)
                if node is None or node.is_builtin:
                    continue
                configure_fn(node)
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


class C_InnerNode(object):

    def __init__(self, root, config):
        self.__root = root
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
    def root(self):
        return self.__root

    @property
    def name(self):
        return self.root['name']

    def generate_decl(self):
        return []

    def generate_add(self):
        return []


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
                field = C_StructField(root=inner, config=self.config)
                self.config.configure_struct_field(field=field)
                if not field.is_ignored:
                    yield field

    def generate_decl(self):
        is_local = to_cpp_bool(self.__is_local)
        can_copy = to_cpp_bool(self.__can_copy)
        can_move = to_cpp_bool(self.__can_move)
        lines = []
        lines += [
           f'MAKE_TYPE_FACTORY({self.name}, {self.name});',
           f'struct {self.name}Annotation',
           f': public ManagedStructureAnnotation<{self.name},true,true> {{',
           f'    {self.name}Annotation(ModuleLibrary & ml)',
           f'    : ManagedStructureAnnotation ("{self.name}", ml) {{',
        ]
        lines += [
           f'        addField<DAS_BIND_MANAGED_FIELD({f.name})>("{f.name}");'
                        for f in self.fields
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
        return [f'addAnnotation(make_smart<{self.name}Annotation>(lib));']


class C_OpaqueStruct(C_InnerNode):

    def __init__(self, **kwargs):
        super(C_OpaqueStruct, self).__init__(**kwargs)
        self.__dummy_type = None

    def set_dummy_type(self, dummy_type):
        self.__dummy_type = dummy_type

    @staticmethod
    def maybe_create(root, **kwargs):
        if (root['kind'] == 'RecordDecl'
            and root['tagUsed'] in ['struct', 'union']
            and 'name' in root
            and 'inner' not in root
        ):
            return C_OpaqueStruct(root=root, **kwargs)

    def generate_decl(self):
        dummy_type = self.__dummy_type
        if dummy_type is None:
            raise BinderError(f'Must set dummy type name for {self.name}')
        return [f'MAKE_TYPE_FACTORY({dummy_type}, {dummy_type})']

    def generate_add(self):
        dt = self.__dummy_type
        return [f'addAnnotation(make_smart<DummyTypeAnnotation>('
            f'"{dt}", "{dt}", sizeof({dt}), alignof({dt})));']


class C_StructField(C_InnerNode):

    @property
    def type(self):
        t = self.root['type']
        return t.get('desugaredQualType', t['qualType'])

    @property
    def is_array(self):
        return '[' in self.type

    @property
    def is_bit_field(self):
        return self.root.get('isBitfield', False)


def to_cpp_bool(b):
    return {True: 'true', False: 'false'}[b]
