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
