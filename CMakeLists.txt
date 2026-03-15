cmake_minimum_required(VERSION 3.14)
project(text-to-geometry LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

include(FetchContent)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.14.0
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# pybind11 for Python bindings
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG v2.11.1
)
FetchContent_MakeAvailable(pybind11)

add_library(kernel
  src/kernel/accum_transform.cpp
  src/kernel/builder.cpp
  src/kernel/intern.cpp
  src/kernel/lower.cpp
  src/kernel/optimise.cpp
  src/kernel/pack_for_webgpu.cpp
  src/kernel/param_extract.cpp
  src/kernel/unparse_dsl.cpp
)
target_include_directories(kernel PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_library(frontend
  src/frontend/lexer.cpp
  src/frontend/parser.cpp
)
target_include_directories(frontend PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(frontend PRIVATE kernel)

enable_testing()
add_executable(dag_builder_tests tests/dag_builder_tests.cpp)
target_link_libraries(dag_builder_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME dag_builder_tests COMMAND dag_builder_tests)

add_executable(optimise_tests tests/optimise_tests.cpp)
target_include_directories(optimise_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(optimise_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME optimise_tests COMMAND optimise_tests)

add_executable(ir_tests tests/ir_tests.cpp)
target_link_libraries(ir_tests PRIVATE frontend GTest::gtest GTest::gtest_main)
add_test(NAME ir_tests COMMAND ir_tests)

add_executable(flat_ir_tests tests/flat_ir_tests.cpp)
target_link_libraries(flat_ir_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME flat_ir_tests COMMAND flat_ir_tests)

add_executable(lower_tests tests/lower_tests.cpp)
target_include_directories(lower_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(lower_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME lower_tests COMMAND lower_tests)

add_executable(param_extract_tests tests/param_extract_tests.cpp)
target_include_directories(param_extract_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(param_extract_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME param_extract_tests COMMAND param_extract_tests)

add_executable(pack_for_webgpu_tests tests/pack_for_webgpu_tests.cpp)
target_include_directories(pack_for_webgpu_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(pack_for_webgpu_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME pack_for_webgpu_tests COMMAND pack_for_webgpu_tests)

add_executable(unparse_dsl_tests tests/unparse_dsl_tests.cpp)
target_include_directories(unparse_dsl_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(unparse_dsl_tests PRIVATE frontend kernel GTest::gtest GTest::gtest_main)
add_test(NAME unparse_dsl_tests COMMAND unparse_dsl_tests)

add_executable(validate_dsl text-to-dsl/validate_dsl.cpp)
target_link_libraries(validate_dsl PRIVATE frontend)

# Python bindings (pybind11)
pybind11_add_module(text_to_geometry_bindings bindings/pybind_compile.cpp)
target_link_libraries(text_to_geometry_bindings PRIVATE frontend kernel)
