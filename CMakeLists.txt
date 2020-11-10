SET(DAS_BINDER_DIR ${PROJECT_SOURCE_DIR}/modules/dasBinder)
SET(DAS_BINDER_PY_DIR ${DAS_BINDER_DIR}/python_modules/das_binder)

SET(DAS_BINDER_SRC
    ${DAS_BINDER_PY_DIR}/__init__.py
    ${DAS_BINDER_PY_DIR}/binder.py
    ${DAS_BINDER_PY_DIR}/config.py
    ${DAS_BINDER_PY_DIR}/main.py
)

include(${DAS_BINDER_DIR}/dasShared/CMakeLists.txt)
GET_DAS_SHARED_PY_SRC(DAS_BINDER_SHARED_SRC ${DAS_BINDER_DIR}/dasShared)

find_package(Python3)
IF(Python3_FOUND AND CMAKE_C_COMPILER_ID MATCHES "Clang")
    MESSAGE(STATUS "Found all prerequisites for dasBinder.")
    SET(DAS_BINDER_FOUND ON)
ELSE()
    MESSAGE(STATUS "Prerequisites for dasBinder not found.")
ENDIF()

MACRO(DAS_BINDER c_header_from module_to config)
    IF(NOT Python3_FOUND OR NOT CMAKE_C_COMPILER_ID MATCHES "Clang")
        MESSAGE(STATUS "Prerequisites for dasBinder not found. Pre-generated binding files will be used.")
    ELSE()
        ADD_CUSTOM_COMMAND(
            DEPENDS ${c_header_from} ${config} ${DAS_BINDER_SRC} ${DAS_PYTHON_SHARED_SRC}
            OUTPUT ${CMAKE_SOURCE_DIR}/${module_to}
            WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}
            VERBATIM
            COMMAND ${Python3_EXECUTABLE} -B utils/dasBinder/main.py
                --c_header_from ${c_header_from}
                --module_to ${module_to}
                --config ${config}
                --clang_c_exe ${CMAKE_C_COMPILER}
                --include_dirs "${CMAKE_C_IMPLICIT_INCLUDE_DIRECTORIES}"
                --include_dirs_sep ";"
            COMMENT "Writing generated das bindings for ${c_header_from} to ${module_to}"
        )
    ENDIF()
ENDMACRO()
