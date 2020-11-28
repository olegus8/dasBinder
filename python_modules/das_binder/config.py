class ConfigBase(object):

    @property
    def das_module_name(self):
        '''Module name as to be seen by das "require".'''
        raise NotImplementedError()

    @property
    def c_headers_to_extract_defines_from(self):
        return []

    def generate_custom_files(self, context):
        '''Return tuples of file path and contents.
        File paths must be relative. They will be resolved relative
        to the directory containing config file.
        '''
        return []

    @property
    def save_ast(self):
        return False

    def configure_enum(self, enum):
        '''This function is called for each encountered enum.'''
        pass

    def configure_struct(self, struct):
        '''This function is called for each encountered struct.'''
        pass

    def configure_opaque_struct(self, struct):
        '''This function is called for each encountered opaque struct.'''
        pass

    def configure_struct_field(self, field):
        '''This function is called for each field in each struct.'''
        pass

    def configure_function(self, function):
        '''This function is called for each function.'''
        pass
