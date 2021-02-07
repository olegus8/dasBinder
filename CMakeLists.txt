IF(NOT DAS_BINDER_INCLUDED)
    SET(DAS_BINDER_INCLUDED TRUE)
    MESSAGE(STATUS "dasBinder module included.")

    find_package(Python3)
    FIND_PROGRAM(DAS_BINDER_CLANG_EXE clang)

    SET(DAS_BINDER_DIR ${CMAKE_SOURCE_DIR}/modules/dasBinder)
    SET(DAS_BINDER_PY_DIR ${DAS_BINDER_DIR}/python_modules/das_binder)

    SET(DAS_BINDER_SRC
        ${DAS_BINDER_PY_DIR}/__init__.py
        ${DAS_BINDER_PY_DIR}/binder.py
        ${DAS_BINDER_PY_DIR}/config.py
        ${DAS_BINDER_PY_DIR}/main.py
    )

    include(${DAS_BINDER_DIR}/dasShared/CMakeLists.txt)
    GET_DAS_SHARED_PY_SRC(DAS_BINDER_SHARED_SRC ${DAS_BINDER_DIR}/dasShared)

    MACRO(DAS_BINDER
        c_header_from
        num_parts
        module_cpp_prefix
        module_cpp_parts_var
        module_h_to config
        include_dirs
        extra_deps
        extra_outputs
    )
        IF(NOT Python3_FOUND)
            MESSAGE(STATUS "Python3 prerequisite for dasBinder not found. Will use pregenerated bindings in ${module_h_to} and ${module_cpp_prefix} for ${c_header_from}.")
        ELSEIF(NOT DAS_BINDER_CLANG_EXE)
            MESSAGE(STATUS "Clang prerequisite for dasBinder not found. Will use pregenerated bindings in ${module_h_to} and ${module_cpp_prefix} for ${c_header_from}.")
        ELSE()
            LIST(APPEND ${module_cpp_parts_var} ${out_src})
            ADD_CUSTOM_COMMAND(
                DEPENDS ${c_header_from} ${config} ${extra_deps} ${DAS_BINDER_SRC} ${DAS_BINDER_SHARED_SRC}
                OUTPUT ${module_cpp_prefix} ${module_h_to} ${extra_outputs}
                WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                VERBATIM
                COMMAND ${Python3_EXECUTABLE} -B ${DAS_BINDER_PY_DIR}/main.py
                    --c_header_from ${c_header_from}
                    --module_cpp_prefix ${module_cpp_prefix}
                    --module_h_to ${module_h_to}
                    --config ${config}
                    --clang_c_exe ${DAS_BINDER_CLANG_EXE}
                    --include_dirs "${CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES};${include_dirs}"
                    --include_dirs_sep ";"
                COMMENT "Writing generated das bindings for ${c_header_from} to ${module_h_to} and ${module_cpp_prefix}"
            )
        ENDIF()
    ENDMACRO()

    SET(DAS_BINDER_TEST_SRC
        ${DAS_BINDER_DIR}/examples/test/bindings.cpp
        ${DAS_BINDER_DIR}/examples/test/bindings_generated.h.inc
        ${DAS_BINDER_DIR}/examples/test/bindings_generated.cpp.inc
        ${DAS_BINDER_DIR}/examples/test/main.cpp
    )

    add_executable(dasBinderTest ${DAS_BINDER_TEST_SRC})
    TARGET_LINK_LIBRARIES(dasBinderTest libDaScript)
    SETUP_CPP11(dasBinderTest)

    get_target_property(DAS_BINDER_TEST_INCLUDE_DIRS dasBinderTest INCLUDE_DIRECTORIES)

    DAS_BINDER(
        ${DAS_BINDER_DIR}/examples/test/header_to_bind.h
        ${DAS_BINDER_DIR}/examples/test/bindings_generated.h.inc
        ${DAS_BINDER_DIR}/examples/test/bindings_generated.cpp.inc
        ${DAS_BINDER_DIR}/examples/test/binding_config.py
        ${DAS_BINDER_TEST_INCLUDE_DIRS}
        ""
        ""
    )
ENDIF()
