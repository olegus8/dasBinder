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
        parser.add_argument('--num_parts', type=int, required=True,
            help='Number of compilation units to split generated bindings '
                'into.')
        parser.add_argument('--module_cpp_prefix', type=str, required=True,
            help='Prefix for .cpp files to write generated das::Module '
                'parts to.')
        parser.add_argument('--module_h_inc_to', type=str, required=True,
            help='.h file to write generated das header to.')
        parser.add_argument('--module_h', type=str, required=True,
            help='.h file to include in generated .cpp')
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
    def module_cpp_prefix(self):
        return full_path(self.__args.module_cpp_prefix)

    @property
    def num_parts(self):
        return self.__args.num_parts

    @property
    def module_h_inc_to(self):
        return full_path(self.__args.module_h_inc_to)

    @property
    def module_h(self):
        return full_path(self.__args.module_h)

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

    @property
    def __generated_cpp_inc_path(self):
        return f'{self.__settings.module_cpp_prefix}.cpp.inc'

    def run(self):
        logging.basicConfig(level=self.__settings.log_level,
            format='%(asctime)s [%(levelname)s:%(name)s] %(message)s')
        self._log_info(f'Generating bindings for '
            f'{self.__settings.c_header_from}')
        self.__maybe_save_ast()
        self._log_info('Running custom pass.')
        self.__config.custom_pass(CustomPassContext(
            main_c_header = self.__main_c_header,
            macro_consts = self.__macro_consts,
        ))
        write_to_file(fpath=self.__generated_cpp_inc_path,
            content='\n'.join(self.__generate_module_cpp_inc() + ['']))
        self._log_info(f'Wrote generated das::Module to '
            f'{self.__generated_cpp_inc_path}')
        for part in range(self.__settings.num_parts):
            fpath = f'{self.__settings.module_cpp_prefix}_{part}.cpp'
            write_to_file(fpath=fpath,
                content='\n'.join(self.__generate_module_cpp(part)+['']))
            self._log_info(f'Wrote generated part to {fpath}')
        write_to_file(fpath=self.__settings.module_h_inc_to,
            content='\n'.join(self.__generate_module_h_inc() + ['']))
        self._log_info(f'Wrote generated header to '
            f'{self.__settings.module_h_inc_to}')
        self._log_info('Finished successfully.')

    def __maybe_save_ast(self):
        if not self.__config.save_ast:
            return
        ast_fpath = self.__settings.module_cpp_prefix + '.ast.json'
        write_to_file(fpath=ast_fpath, content=json.dumps(self.__ast,
            indent=4, sort_keys=True))
        self._log_info(f'Wrote AST for C header to {ast_fpath}')

    def __read_config(self, config_fpath):
        try:
            with open(config_fpath, 'r') as f:
                cfg_py = f.read()
        except IOError:
            raise BinderError(f'Could not read config file: {config_fpath}')
        old_path = list(sys.path)
        sys.path.insert(0, path.dirname(config_fpath))
        cfg_globals = {}
        exec(cfg_py, cfg_globals)
        sys.path = old_path
        config_class = cfg_globals.get('Config')
        if config_class is None:
            raise BinderError(f'Config file must define "Config" class.')
        return config_class()

    def __generate_module_h_inc(self):
        lines = []
        module = self.__config.das_module_name
        header_from = path.relpath(
            self.__settings.c_header_from,
            path.dirname(self.__settings.module_h_inc_to))
        lines += [self.__config.title or f'// generated by {APP_NAME}']
        lines += [
            '',
            '//',
            '// enums',
            '//',
            ''] + [
            line for enum in self.__enums
                for line in enum.generate_decl_h()
        ]
        lines += [
            '',
            '//',
            '// opaque structs',
            '//',
            ''] + [
            line for struct in self.__opaque_structs
                for line in struct.generate_decl_h()
        ]
        lines += [
            '',
            '//',
            '// structs',
            '//',
            ''] + [
            line for struct in self.__structs
                for line in struct.generate_decl_h()
        ]
        return lines

    def __generate_module_cpp_inc(self):
        lines = []
        module = self.__config.das_module_name
        lines += [self.__config.title or f'// generated by {APP_NAME}']
        lines += [
            '',
        ]
        kinds = ['Enums', 'OpaqueStructs', 'Structs', 'Functions', 'Consts']
        for part in range(self.__settings.num_parts):
            for kind in kinds:
                lines += [f'void addVulkanGenerated{kind}_{part}'
                    '(Module &, ModuleLibrary &);'
                ]
        lines += [
            '',
           f'class GeneratedModule_{module} : public Module {{',
            'public:',
           f'    GeneratedModule_{module}() : Module("{module}") {{',
            '    }',
            '',
            'protected:',
            '    void addGenerated(ModuleLibrary & lib) {'] + [
           f'        addVulkanGenerated{kind}_{part}(*this, lib);'
                     for kind in kinds
                     for part in range(self.__settings.num_parts)] + [
            '    }',
            '};',
        ]
        return lines

    def __generate_module_cpp(self, part_i):
        lines = []
        module = self.__config.das_module_name
        header = path.relpath(
            self.__settings.module_h,
            path.dirname(self.__settings.module_cpp_prefix))
        part_of = lambda xs: split_to_parts(
            list(xs), self.__settings.num_parts)[part_i]
        lines += [self.__config.title or f'// generated by {APP_NAME}']
        lines += [
           f'#include "{header}"',
            '',
            'using namespace das;',
            '',
            '#if defined(_MSC_VER)',
            '#pragma warning(push)',
            '#pragma warning(disable:4100)   // unreferenced formal parameter',
            '#endif',
            '#if defined(__GNUC__) && !defined(__clang__)',
            '#pragma GCC diagnostic push',
            '#pragma GCC diagnostic ignored "-Wunused-parameter"',
            '#endif',
            '#if defined(__clang__)',
            '#pragma clang diagnostic push',
            '#pragma clang diagnostic ignored "-Wunused-parameter"',
            '#endif',
        ]
        lines += [
            '',
            '//',
            '// opaque structs',
            '//',
            ''] + [
            line for struct in part_of(self.__opaque_structs)
                for line in struct.generate_decl_cpp()
        ]
        lines += [
            '',
            '//',
            '// structs',
            '//',
            ''] + [
            line for struct in part_of(self.__structs)
                for line in struct.generate_decl_cpp()
        ]
        lines += [
            '',
           f'void addVulkanGeneratedEnums_{part_i}('
                'Module & module, ModuleLibrary & lib) {'] + [
           f'    {line}' for enum in part_of(self.__enums)
                 for line in enum.generate_add()] + [
            '}',
        ]
        lines += [
            '',
           f'void addVulkanGeneratedOpaqueStructs_{part_i}('
                'Module & module, ModuleLibrary & lib) {'] + [
           f'    {line}' for struct in part_of(self.__opaque_structs)
                 for line in struct.generate_add()] + [
            '}',
        ]
        lines += [
            '',
           f'void addVulkanGeneratedStructs_{part_i}('
                'Module & module, ModuleLibrary & lib) {'] + [
           f'    {line}' for struct in part_of(self.__structs)
                 for line in struct.generate_add()] + [
            '}',
        ]
        lines += [
            '',
           f'void addVulkanGeneratedFunctions_{part_i}('
                'Module & module, ModuleLibrary & lib) {'] + [
           f'    {line}' for function in part_of(self.__functions)
                 for line in function.generate_add()] + [
            '}',
        ]
        lines += [
            '',
           f'void addVulkanGeneratedConsts_{part_i}('
                'Module & module, ModuleLibrary & lib) {'] + [
           f'    {line}' for const in part_of(self.__macro_consts)
                 for line in const.generate_add()] + [
            '}',
        ]
        return lines


class CustomPassContext(object):

    def __init__(self, main_c_header, macro_consts):
        self.main_c_header = main_c_header
        self.macro_consts = macro_consts


class C_TranslationUnit(LoggingObject):

    def __init__(self, c_src_fpath, clang_c_exe, include_dirs, config):
        cmd = []
        cmd += [clang_c_exe, '-c',
            '-fno-delayed-template-parsing',
            '-fno-color-diagnostics',
        ]
        for dpath in include_dirs:
            dpath = dpath.strip()
            if dpath:
                cmd += [f'-I{dpath}']
        cmd += [
            '-Xclang',
            '-ast-dump=json',
        ]

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

    def generate_decl_cpp(self):
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

    def generate_decl_h(self):
        name = self.name
        fields = list(self.fields)
        lines = []
        lines += [
           f'namespace das',
           f'{{',
           f'    template <> struct cast < {name} > '
                        f': cast_enum < {name} > {{}};',
           f'}};',
            '',
           f'class Enumeration{name} : public das::Enumeration {{',
           f'public:',
           f'    Enumeration{name}() : das::Enumeration("{name}") {{',
           f'        external = true;',
           f'        cppName = "{name}";',
           f'        baseType = (das::Type) das::ToBasicType< '
                        f'das::underlying_type< {name} >::type >::type;',
           f'        {name} enumArray[] = {{'] + [
           f'            {name}::{f},' for f in fields
        ]
        remove_last_char(lines, ',')
        lines += [
           f'        }};',
           f'        static const char *enumArrayName[] = {{'] + [
           f'            "{f}",' for f in fields
        ]
        remove_last_char(lines, ',')
        lines += [
           f'        }};',
           f'        for (uint32_t i = 0; i < {len(fields)}; ++i)',
           f'            addI(enumArrayName[i], int64_t(enumArray[i]), '
                                f'das::LineInfo());',
           f'    }}',
           f'}};',
            '',
           f'namespace das',
           f'{{',
           f'    template <>',
           f'    struct typeFactory< {name} > {{',
           f'        static TypeDeclPtr make(const ModuleLibrary & library){{',
           f'            return library.makeEnumType("{name}");',
           f'        }}',
           f'    }};',
           f'}}',
        ]
        return lines

    def generate_add(self):
        return [
            f'module.addEnumeration(make_smart<Enumeration{self.name}>());']


class C_Struct(C_InnerNode):

    def __init__(self, tag, **kwargs):
        super(C_Struct, self).__init__(**kwargs)
        self.__is_local = True
        self.__can_copy = True
        self.__can_move = True
        self.__can_clone = True
        self.__tag = tag

    def set_is_local(self, is_local):
        self.__is_local = is_local

    def set_can_copy(self, can_copy):
        self.__can_copy = can_copy

    def set_can_move(self, can_move):
        self.__can_move = can_move

    def set_can_clone(self, can_move):
        self.__can_move = can_move

    @staticmethod
    def maybe_create(root, **kwargs):
        if (root['kind'] == 'RecordDecl'
            and root['tagUsed'] in ['struct', 'union']
            and 'inner' in root
            and 'name' in root
        ):
            return C_Struct(root=root, tag=root['tagUsed'], **kwargs)

    @property
    def is_union(self):
        return self.__tag == 'union'

    @property
    def is_struct(self):
        return self.__tag == 'struct'

    @property
    def fields(self):
        for inner in self.root['inner']:
            if inner['kind'] == 'FieldDecl':
                field = C_StructField(root=inner, config=self.config,
                    struct=self)
                self.config.configure_struct_field(field=field)
                if not field.is_ignored:
                    yield field

    def generate_decl_h(self):
        return [f'MAKE_EXTERNAL_TYPE_FACTORY({self.name}, {self.name});']

    def generate_decl_cpp(self):
        is_local = to_cpp_bool(self.__is_local)
        can_copy = to_cpp_bool(self.__can_copy)
        can_move = to_cpp_bool(self.__can_move)
        can_clone = to_cpp_bool(self.__can_clone)
        lines = []
        lines += [
            '',
           f'IMPLEMENT_EXTERNAL_TYPE_FACTORY({self.name}, {self.name});',
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
           f'    : ManagedStructureAnnotation ("{self.das_name}", ml) {{',
        ]
        lines += [
           f'        addField<DAS_BIND_MANAGED_FIELD({f.name})>("{f.das_name}");'
                        for f in self.fields
                        if not f.is_bit_field and not f.is_self_ref
        ]
        lines += [
            '    }',
            '    void init() {',
        ]
        lines += [
           f'        addField<DAS_BIND_MANAGED_FIELD({f.name})>("{f.das_name}");'
                        for f in self.fields if f.is_self_ref
        ]
        lines += [
            '    }',
           f'    virtual bool isLocal() const override {{ return {is_local}; }}',
           f'    virtual bool canCopy() const override {{ return {can_copy}; }}',
           f'    virtual bool canMove() const override {{ return {can_move}; }}',
           f'    virtual bool canClone() const override {{ return {can_clone}; }}',
            '    virtual SimNode * simulateCopy ( Context & context, const LineInfo & at, SimNode * l, SimNode * r ) const override {',
           f'        return context.code->makeNode<SimNode_CopyRefValue>(at, l, r, getSizeOf());',
            '    }',
            '    virtual SimNode * simulateClone ( Context & context, const LineInfo & at, SimNode * l, SimNode * r ) const override {',
            '        return simulateCopy(context, at, l, r);',
            '    }',
            '};'
        ]
        return lines

    def generate_add(self):
        lines = []
        lines += [
            f'module.addAnnotation(make_smart<{self.name}Annotation>(lib));',
        ]
        for field in self.fields:
            if not field.is_bit_field:
                continue
            lines += [
                '',
               f'addExtern<DAS_BIND_FUN({field.getter_name})>(module, lib, "{field.getter_name}",',
                '    SideEffects::none, "{field.getter_name}");',
               f'addExtern<DAS_BIND_FUN({field.setter_name})>(module, lib, "{field.setter_name}",',
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

    def generate_decl_h(self):
        lines = []
        if self.__ptr_type is not None:
            lines += [
                f'typedef {self.name} * {self.__ptr_type};'
            ]
        lines += [
            f'MAKE_EXTERNAL_TYPE_FACTORY({self.das_type}, {self.das_type})',
        ]
        return lines

    def generate_decl_cpp(self):
        return [
            f'IMPLEMENT_EXTERNAL_TYPE_FACTORY({self.das_type}, {self.das_type})',
        ]

    def generate_add(self):
        t = self.das_type
        ann = self.__annotation_type
        return [
            f'module.addAnnotation(make_smart<{ann}<{t}>>("{t}", "{t}"));']


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

    def __init__(self, **kwargs):
        super(C_Function, self).__init__(**kwargs)
        self.__side_effects = 'worstDefault'

    def set_side_effects(self, side_effects):
        self.__side_effects = side_effects

    @staticmethod
    def maybe_create(root, **kwargs):
        if root['kind'] == 'FunctionDecl':
            return C_Function(root=root, **kwargs)

    def generate_add(self):
        return [
            f'addExtern<DAS_BIND_FUN({self.name})>(module, lib, "{self.name}",',
            f'    SideEffects::{self.__side_effects}, "{self.name}");',
        ]

    @property
    def params(self):
        for inner in self.root['inner']:
            if inner['kind'] == 'ParmVarDecl':
                param = C_FunctionParam(root=inner, config=self.config,
                    function=self)
                yield param

    @property
    def return_type(self):
        return re.match(r'^([^(]+) \(.*', self.type).group(1).strip()


class C_FunctionParam(C_InnerNode):

    def __init__(self, function, **kwargs):
        super(C_FunctionParam, self).__init__(**kwargs)
        self.__function = function

    @property
    def function(self):
        return self.__function


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
            self.__cached_macro_consts = list(self.__get_items(
                item_class=C_MacroConst,
                configure_fn=self.__config.configure_macro_const))
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
            f'addConstant(module, "{self.name}", {self.value});'
        ]


def to_cpp_bool(b):
    return {True: 'true', False: 'false'}[b]

def remove_last_char(lines, char):
    if lines[-1].endswith(char):
        lines[-1] = lines[-1][:-1]

def split_to_parts(xs, parts):
    '''
    >>> a = 'some string to split'
    >>> split_to_parts(a, 10)
    ['so', 'me', ' s', 'tr', 'in', 'g ', 'to', ' s', 'pl', 'it']
    >>> for parts in [1, 10, 50]:
    ...     aa = split_to_parts(a, parts)
    ...     assert len(aa), parts
    ...     assert ''.join(aa) == a
    '''
    return [xs[(len(xs)* n   ) // parts :
               (len(xs)*(n+1)) // parts
    ] for n in range(parts) ]
