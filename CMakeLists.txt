cmake_minimum_required(VERSION 3.14)
project(text-to-geometry LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

include(FetchContent)
FetchContent_Declare(
  googletest
  GIT_REPOSITORY https://github.com/google/googletest.git
  GIT_TAG v1.14.0
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_library(kernel
  src/kernel/accum_transform.cpp
  src/kernel/builder.cpp
  src/kernel/codegen_cuda.cpp
  src/kernel/intern.cpp
  src/kernel/lower.cpp
  src/kernel/optimise.cpp
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

add_executable(lower_tests tests/lower_tests.cpp)
target_include_directories(lower_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(lower_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME lower_tests COMMAND lower_tests)

add_executable(codegen_cuda_tests tests/codegen_cuda_tests.cpp)
target_include_directories(codegen_cuda_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/tests)
target_link_libraries(codegen_cuda_tests PRIVATE kernel GTest::gtest GTest::gtest_main)
add_test(NAME codegen_cuda_tests COMMAND codegen_cuda_tests)

add_executable(validate_dsl text-to-dsl/validate_dsl.cpp)
target_link_libraries(validate_dsl PRIVATE frontend)

# CUDA renderer (optional - requires CUDA toolkit)
include(CheckLanguage)
check_language(CUDA)
if(CMAKE_CUDA_COMPILER)
  enable_language(CUDA)
  find_package(CUDAToolkit REQUIRED)
  add_library(cuda_renderer src/kernel/cuda_renderer.cpp)
  target_include_directories(cuda_renderer PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
  target_link_libraries(cuda_renderer PUBLIC kernel CUDA::cuda_driver CUDA::nvrtc)
  set_target_properties(cuda_renderer PROPERTIES CUDA_STANDARD 17)
  add_executable(launch_config_bench benchmarks/launch_config_bench.cpp)
  target_link_libraries(launch_config_bench PRIVATE cuda_renderer kernel)
  message(STATUS "CUDA found: building cuda_renderer + benchmarks")

  # GLFW viewer (optional - requires GLFW3)
  find_package(glfw3 QUIET)
  find_package(OpenGL QUIET)
  if(glfw3_FOUND AND OpenGL_FOUND)
    add_library(glad STATIC third_party/glad/src/gl.c)
    target_include_directories(glad PUBLIC third_party/glad/include)

    add_executable(sdf_viewer src/viewer/main.cpp)
    target_link_libraries(sdf_viewer PRIVATE
      frontend kernel cuda_renderer
      glfw OpenGL::GL glad
    )
    target_include_directories(sdf_viewer PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
    message(STATUS "GLFW found: building sdf_viewer")
  else()
    message(STATUS "GLFW or OpenGL not found: skipping sdf_viewer")
  endif()
else()
  message(STATUS "CUDA not found: skipping cuda_renderer + benchmarks")
endif()
