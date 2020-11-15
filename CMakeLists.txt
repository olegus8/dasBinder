IF(NOT DAS_BINDER_INCLUDED)
    SET(DAS_BINDER_INCLUDED TRUE)
    MESSAGE(STATUS "dasBinder module included.")

    find_package(Python3)

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

    MACRO(DAS_BINDER c_header_from module_to config include_dirs)
        IF(NOT Python3_FOUND OR NOT CMAKE_C_COMPILER_ID MATCHES "Clang")
            MESSAGE(STATUS "Prerequisites for dasBinder not found. Will use pregenerated bindings in ${module_to} for ${c_header_from}.")
        ELSE()
            ADD_CUSTOM_COMMAND(
                DEPENDS ${c_header_from} ${config} ${DAS_BINDER_SRC} ${DAS_BINDER_SHARED_SRC}
                OUTPUT ${module_to}
                WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
                VERBATIM
                COMMAND ${Python3_EXECUTABLE} -B ${DAS_BINDER_PY_DIR}/main.py
                    --c_header_from ${c_header_from}
                    --module_to ${module_to}
                    --config ${config}
                    --clang_c_exe ${CMAKE_C_COMPILER}
                    --include_dirs "${CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES};${include_dirs}"
                    --include_dirs_sep ";"
                COMMENT "Writing generated das bindings for ${c_header_from} to ${module_to}"
            )
        ENDIF()
    ENDMACRO()

    SET(DAS_BINDER_TEST_SRC
        ${DAS_BINDER_DIR}/examples/test/bindings.cpp
        ${DAS_BINDER_DIR}/examples/test/bindings_generated.inc
        ${DAS_BINDER_DIR}/examples/test/main.cpp
    )

    add_executable(dasBinderTest ${DAS_BINDER_TEST_SRC})
    TARGET_LINK_LIBRARIES(dasBinderTest libDaScript)
    SETUP_CPP11(dasBinderTest)

    DAS_BINDER(
        ${DAS_BINDER_DIR}/examples/test/header_to_bind.h
        ${DAS_BINDER_DIR}/examples/test/bindings_generated.inc
        ${DAS_BINDER_DIR}/examples/test/binding_config.py
    )
ENDIF()
