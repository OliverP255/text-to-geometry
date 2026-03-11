# CMake generated Testfile for 
# Source directory: /Users/oliverpryce/Documents/AI/text-to-geometry
# Build directory: /Users/oliverpryce/Documents/AI/text-to-geometry/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(dag_builder_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/dag_builder_tests")
set_tests_properties(dag_builder_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;45;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(optimise_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/optimise_tests")
set_tests_properties(optimise_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;50;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(ir_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/ir_tests")
set_tests_properties(ir_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;54;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(lower_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/lower_tests")
set_tests_properties(lower_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;59;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(codegen_cuda_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/codegen_cuda_tests")
set_tests_properties(codegen_cuda_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;64;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(unparse_dsl_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/unparse_dsl_tests")
set_tests_properties(unparse_dsl_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;69;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
subdirs("_deps/googletest-build")
subdirs("_deps/pybind11-build")
