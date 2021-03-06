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

    MACRO(DAS_BINDER_GET_GENERATED_CPP
        num_parts
        module_cpp_parts_var
        module_cpp_prefix
    )
        FOREACH(part_i_plus_one RANGE 1 ${num_parts})
            MATH(EXPR part_i "${part_i_plus_one}-1")
            LIST(APPEND ${module_cpp_parts_var} "${module_cpp_prefix}_${part_i}.cpp")
        ENDFOREACH()
    ENDMACRO()

    MACRO(DAS_BINDER
        target
        num_parts
        c_header_from
        module_cpp_prefix
        module_h_inc_to
        module_h
        config
        include_dirs
        extra_deps
        extra_outputs
    )
        IF(NOT Python3_FOUND)
            MESSAGE(STATUS "Python3 prerequisite for dasBinder not found. Will use pregenerated bindings in ${module_h_inc_to} and ${module_cpp_prefix} for ${c_header_from}.")
        ELSEIF(NOT DAS_BINDER_CLANG_EXE)
            MESSAGE(STATUS "Clang prerequisite for dasBinder not found. Will use pregenerated bindings in ${module_h_inc_to} and ${module_cpp_prefix} for ${c_header_from}.")
        ELSE()
            ADD_CUSTOM_TARGET(${target})
            SET(parts_cpp)
            DAS_BINDER_GET_GENERATED_CPP(
                ${num_parts} parts_cpp ${module_cpp_prefix}
            )
            ADD_CUSTOM_COMMAND(
                TARGET ${target}
                DEPENDS ${c_header_from} ${module_h} ${config} ${extra_deps} ${DAS_BINDER_SRC} ${DAS_BINDER_SHARED_SRC}
                WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                VERBATIM
                COMMAND ${Python3_EXECUTABLE} -B ${DAS_BINDER_PY_DIR}/main.py
                    --c_header_from ${c_header_from}
                    --num_parts ${num_parts}
                    --module_cpp_prefix ${module_cpp_prefix}
                    --module_h_inc_to ${module_h_inc_to}
                    --module_h ${module_h}
                    --config ${config}
                    --clang_c_exe ${DAS_BINDER_CLANG_EXE}
                    --include_dirs "${CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES};${include_dirs}"
                    --include_dirs_sep ";"
                COMMENT "Writing generated das bindings for ${c_header_from} to ${module_h_inc_to} and ${module_cpp_prefix}"
            )
        ENDIF()
    ENDMACRO()

#    SET(DAS_BINDER_TEST_SRC
#        ${DAS_BINDER_DIR}/examples/test/bindings.cpp
#        ${DAS_BINDER_DIR}/examples/test/bindings_generated.h.inc
#        ${DAS_BINDER_DIR}/examples/test/bindings_generated.cpp.inc
#        ${DAS_BINDER_DIR}/examples/test/main.cpp
#    )
#
#    add_executable(dasBinderTest ${DAS_BINDER_TEST_SRC})
#    TARGET_LINK_LIBRARIES(dasBinderTest libDaScript)
#    SETUP_CPP11(dasBinderTest)
#
#    get_target_property(DAS_BINDER_TEST_INCLUDE_DIRS dasBinderTest INCLUDE_DIRECTORIES)
#
#    DAS_BINDER(
#        ${DAS_BINDER_DIR}/examples/test/header_to_bind.h
#        ${DAS_BINDER_DIR}/examples/test/bindings_generated.h.inc
#        ${DAS_BINDER_DIR}/examples/test/bindings_generated.cpp.inc
#        ${DAS_BINDER_DIR}/examples/test/binding_config.py
#        ${DAS_BINDER_TEST_INCLUDE_DIRS}
#        ""
#        ""
#    )
ENDIF()
