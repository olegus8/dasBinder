MACRO(GET_DAS_SHARED_PY_SRC output_var shared_dir)
    SET(DAS_SHARED_PY_DIR ${shared_dir}/python_modules/das_shared)
    SET(${output_var}
        ${DAS_SHARED_PY_DIR}/__init__.py
        ${DAS_SHARED_PY_DIR}/assertions.py
        ${DAS_SHARED_PY_DIR}/diag.py
        ${DAS_SHARED_PY_DIR}/object_base.py
        ${DAS_SHARED_PY_DIR}/op_sys.py
    )
ENDMACRO()
