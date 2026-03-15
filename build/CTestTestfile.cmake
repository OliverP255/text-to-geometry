# CMake generated Testfile for 
# Source directory: /Users/oliverpryce/Documents/AI/text-to-geometry
# Build directory: /Users/oliverpryce/Documents/AI/text-to-geometry/build
# 
# This file includes the relevant testing commands required for 
# testing this directory and lists subdirectories to be tested as well.
add_test(dag_builder_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/dag_builder_tests")
set_tests_properties(dag_builder_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;46;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(optimise_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/optimise_tests")
set_tests_properties(optimise_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;51;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(ir_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/ir_tests")
set_tests_properties(ir_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;55;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(flat_ir_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/flat_ir_tests")
set_tests_properties(flat_ir_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;59;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(lower_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/lower_tests")
set_tests_properties(lower_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;64;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(param_extract_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/param_extract_tests")
set_tests_properties(param_extract_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;69;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(pack_for_webgpu_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/pack_for_webgpu_tests")
set_tests_properties(pack_for_webgpu_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;74;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
add_test(unparse_dsl_tests "/Users/oliverpryce/Documents/AI/text-to-geometry/build/unparse_dsl_tests")
set_tests_properties(unparse_dsl_tests PROPERTIES  _BACKTRACE_TRIPLES "/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;79;add_test;/Users/oliverpryce/Documents/AI/text-to-geometry/CMakeLists.txt;0;")
subdirs("_deps/googletest-build")
subdirs("_deps/pybind11-build")
