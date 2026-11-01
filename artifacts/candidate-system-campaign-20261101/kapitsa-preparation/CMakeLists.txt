cmake_minimum_required(VERSION 3.24)
# before project(): CMake reads the deployment target when it sets up the compilers
set(CMAKE_OSX_DEPLOYMENT_TARGET "14.0" CACHE STRING "")
project(nace_infer LANGUAGES C CXX OBJCXX)

set(KAPITSA_VERSION "0.2.25")
if(NOT DEFINED KAPITSA_GIT)  # packaging/release/build.sh passes the commit it exported
  execute_process(COMMAND git -C ${CMAKE_SOURCE_DIR} rev-parse --short HEAD OUTPUT_VARIABLE KAPITSA_GIT
                  OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
endif()

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OBJCXX_STANDARD 20)
set(CMAKE_OSX_ARCHITECTURES "arm64" CACHE STRING "")
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_FLAGS_RELEASE "-O3")
set(CMAKE_OBJCXX_FLAGS_RELEASE "-O3")
set(CMAKE_OBJCXX_FLAGS "${CMAKE_OBJCXX_FLAGS} -fobjc-arc")

# Metal kernel sources are embedded as strings and compiled at runtime (no offline
# `metal` compiler needed; works with Command Line Tools only).
file(GLOB NI_KERNELS CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/src/kernels/*.metal ${CMAKE_SOURCE_DIR}/src/kernels/*.h)
# (src/kernels/kflash.h is in NI_KERNELS: both embedded libraries read it)
set(NI_EMBED ${CMAKE_BINARY_DIR}/generated/kernels_embed.cpp)
add_custom_command(
  OUTPUT ${NI_EMBED}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_EMBED} -DSRC_DIR=${CMAKE_SOURCE_DIR}/src/kernels
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_kernels.cmake
  DEPENDS ${NI_KERNELS} ${CMAKE_SOURCE_DIR}/cmake/embed_kernels.cmake
  COMMENT "Embedding Metal kernels")

# Nemotron-H kernels: a second embedded source, compiled only when such a model loads.
file(GLOB NI_NH_KERNELS CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/src/kernels/nemotron/*.metal ${CMAKE_SOURCE_DIR}/src/kernels/nemotron/*.h)
set(NI_NH_EMBED ${CMAKE_BINARY_DIR}/generated/nh_kernels_embed.cpp)
add_custom_command(
  OUTPUT ${NI_NH_EMBED}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_NH_EMBED} -DSRC_DIR=${CMAKE_SOURCE_DIR}/src/kernels
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_nh.cmake
  DEPENDS ${NI_NH_KERNELS} ${CMAKE_SOURCE_DIR}/src/kernels/common.h ${CMAKE_SOURCE_DIR}/src/kernels/iq.h ${CMAKE_SOURCE_DIR}/src/kernels/kflash.h
          ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_nh.cmake
  COMMENT "Embedding the Nemotron-H Metal kernels")

# Dory kernels: a third embedded source, compiled only when a Dory model loads.
file(GLOB NI_DORY_KERNELS CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/src/kernels/dory/*.metal)
set(NI_DORY_EMBED ${CMAKE_BINARY_DIR}/generated/dory_kernels_embed.cpp)
add_custom_command(
  OUTPUT ${NI_DORY_EMBED}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_DORY_EMBED} -DSRC_DIR=${CMAKE_SOURCE_DIR}/src/kernels
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_dory.cmake
  DEPENDS ${NI_DORY_KERNELS} ${CMAKE_SOURCE_DIR}/src/kernels/common.h ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_dory.cmake
  COMMENT "Embedding the Dory Metal kernels")

# Flint kernels: compiled only when a Flint model loads.
file(GLOB NI_FLINT_KERNELS CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/src/kernels/flint/*.metal)
set(NI_FLINT_EMBED ${CMAKE_BINARY_DIR}/generated/flint_kernels_embed.cpp)
add_custom_command(
  OUTPUT ${NI_FLINT_EMBED}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_FLINT_EMBED} -DSRC_DIR=${CMAKE_SOURCE_DIR}/src/kernels
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_flint.cmake
  DEPENDS ${NI_FLINT_KERNELS} ${CMAKE_SOURCE_DIR}/src/kernels/common.h ${CMAKE_SOURCE_DIR}/src/kernels/quant.h
          ${CMAKE_SOURCE_DIR}/src/kernels/kflash.h
          ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_flint.cmake
  COMMENT "Embedding the Flint Metal kernels")

# Metal 4 tensor_ops kernels (src/kernels/tensor/): a library of their own, compiled as Metal 4 on a GPU with matrix units
file(GLOB NI_TENSOR_KERNELS CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/src/kernels/tensor/*.metal)
set(NI_TENSOR_EMBED ${CMAKE_BINARY_DIR}/generated/tensor_kernels_embed.cpp)
add_custom_command(
  OUTPUT ${NI_TENSOR_EMBED}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_TENSOR_EMBED} -DSRC_DIR=${CMAKE_SOURCE_DIR}/src/kernels
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_tensor.cmake
  DEPENDS ${NI_TENSOR_KERNELS} ${CMAKE_SOURCE_DIR}/src/kernels/common.h ${CMAKE_SOURCE_DIR}/src/kernels/nemotron/nh_route.h
          ${CMAKE_SOURCE_DIR}/src/kernels/iq.h
          ${CMAKE_SOURCE_DIR}/cmake/embed_kernels_tensor.cmake
  COMMENT "Embedding the Metal 4 tensor kernels")

# kapitsa bench (src/bench/): the harness's frozen prompt corpus and Apple's names for the Mac models, embedded
set(NI_BENCH_CORPUS ${CMAKE_BINARY_DIR}/generated/bench_corpus.cpp)
add_custom_command(
  OUTPUT ${NI_BENCH_CORPUS}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_BENCH_CORPUS} -DSRC=${CMAKE_SOURCE_DIR}/bench/harness/corpus/bench_corpus.txt
          -DNAME=kBenchCorpus -P ${CMAKE_SOURCE_DIR}/cmake/embed_file.cmake
  DEPENDS ${CMAKE_SOURCE_DIR}/bench/harness/corpus/bench_corpus.txt ${CMAKE_SOURCE_DIR}/cmake/embed_file.cmake
  COMMENT "Embedding the benchmark's prompt corpus")
set(NI_MAC_MODELS ${CMAKE_BINARY_DIR}/generated/mac_models.cpp)
add_custom_command(
  OUTPUT ${NI_MAC_MODELS}
  COMMAND ${CMAKE_COMMAND} -DOUT=${NI_MAC_MODELS} -DSRC=${CMAKE_SOURCE_DIR}/bench/community/mac-models.json
          -DNAME=kMacModels -P ${CMAKE_SOURCE_DIR}/cmake/embed_file.cmake
  DEPENDS ${CMAKE_SOURCE_DIR}/bench/community/mac-models.json ${CMAKE_SOURCE_DIR}/cmake/embed_file.cmake
  COMMENT "Embedding the Mac models")

file(GLOB_RECURSE NI_SOURCES CONFIGURE_DEPENDS
  ${CMAKE_SOURCE_DIR}/src/*.cpp ${CMAKE_SOURCE_DIR}/src/*.mm)
list(FILTER NI_SOURCES EXCLUDE REGEX ".*/src/server/.*")

add_library(naceinfer STATIC ${NI_SOURCES} ${NI_EMBED} ${NI_NH_EMBED} ${NI_DORY_EMBED} ${NI_FLINT_EMBED} ${NI_TENSOR_EMBED} ${NI_BENCH_CORPUS} ${NI_MAC_MODELS})
target_include_directories(naceinfer PUBLIC ${CMAKE_SOURCE_DIR}/include ${CMAKE_SOURCE_DIR}/third_party PRIVATE ${CMAKE_SOURCE_DIR}/src)
target_link_libraries(naceinfer PUBLIC "-framework Metal" "-framework Foundation" "-framework CoreFoundation" "-framework IOSurface"
  "-framework IOKit" "-framework ImageIO" "-framework CoreGraphics" "-framework Security"
  "-framework SystemConfiguration")  # src/cluster: this Mac's computer name, the kind of each network link
target_compile_definitions(naceinfer PRIVATE KAPITSA_VERSION="${KAPITSA_VERSION}")

file(GLOB NI_TOOLS CONFIGURE_DEPENDS ${CMAKE_SOURCE_DIR}/tools/*.cpp ${CMAKE_SOURCE_DIR}/tools/*.mm)
# a library the Python converters build and load themselves (ctypes), not a command
list(FILTER NI_TOOLS EXCLUDE REGEX ".*/tools/(mlx_quant|execution_session_test|http_stream_test|splash_protocol_test|splash_runtime_test|splash_discover_test|splash_plan_test)\\.cpp$")
foreach(t ${NI_TOOLS})
  get_filename_component(name ${t} NAME_WE)
  add_executable(${name} ${t})
  target_include_directories(${name} PRIVATE ${CMAKE_SOURCE_DIR}/src)
  target_link_libraries(${name} PRIVATE naceinfer)
  # (KAPITSA_GIT: the commit a dump or measurement says it was built from, as `kapitsa --version` does)
  target_compile_definitions(${name} PRIVATE KAPITSA_VERSION="${KAPITSA_VERSION}" KAPITSA_GIT="${KAPITSA_GIT}")
endforeach()


find_package(Threads REQUIRED)
add_executable(execution_session_test tools/execution_session_test.cpp src/engine/execution_session.cpp)
target_include_directories(execution_session_test PRIVATE ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/third_party)
target_link_libraries(execution_session_test PRIVATE Threads::Threads)
enable_testing()
add_test(NAME load_error_test COMMAND load_error_test)
set_tests_properties(load_error_test PROPERTIES TIMEOUT 30)
add_test(NAME execution_session_test COMMAND execution_session_test)
set_tests_properties(execution_session_test PROPERTIES TIMEOUT 30)

# Exercise the real HTTP observer and chunked provider without native/UI linkage or sockets.
add_executable(http_stream_test tools/http_stream_test.cpp src/server/http_stream.cpp src/engine/execution_session.cpp)
target_include_directories(http_stream_test PRIVATE ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/third_party)
target_link_libraries(http_stream_test PRIVATE Threads::Threads)
add_test(NAME http_stream_test COMMAND http_stream_test)
set_tests_properties(http_stream_test PROPERTIES TIMEOUT 45)
# Normal static-archive linking uses this object's cache symbols, not naceinfer's hook-free member.
target_sources(fn_store_test PRIVATE src/model/expert_store.cpp)
target_compile_definitions(fn_store_test PRIVATE NI_EXPERT_CACHE_TEST)

# Splash's native protocol (src/splash/protocol.*) against bytes Splash 1.4.0's protocol.py produced and accepted: no model, no GPU.
add_executable(splash_protocol_test tools/splash_protocol_test.cpp src/splash/protocol.cpp)
target_include_directories(splash_protocol_test PRIVATE ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/tools)
add_test(NAME splash_protocol_test COMMAND splash_protocol_test)
set_tests_properties(splash_protocol_test PROPERTIES TIMEOUT 30)

# The child-process runtime (src/splash/runtime.*) against a fake engine this test binary re-executes itself as.
add_executable(splash_runtime_test tools/splash_runtime_test.cpp src/splash/runtime.cpp src/splash/protocol.cpp)
target_include_directories(splash_runtime_test PRIVATE ${CMAKE_SOURCE_DIR}/src)
target_link_libraries(splash_runtime_test PRIVATE Threads::Threads)
add_test(NAME splash_runtime_test COMMAND splash_runtime_test)
set_tests_properties(splash_runtime_test PROPERTIES TIMEOUT 90)

# Finding Splash's binary and model folders (src/splash/discover.*) on a throwaway tree.
add_executable(splash_discover_test tools/splash_discover_test.cpp src/splash/discover.cpp)
target_include_directories(splash_discover_test PRIVATE ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/third_party)
add_test(NAME splash_discover_test COMMAND splash_discover_test)
set_tests_properties(splash_discover_test PROPERTIES TIMEOUT 30)

# What Kapitsa adds to `splash serve-native` (src/splash/plan.*): idle release, expert memory from free memory.
add_executable(splash_plan_test tools/splash_plan_test.cpp src/splash/plan.cpp)
target_include_directories(splash_plan_test PRIVATE ${CMAKE_SOURCE_DIR}/src ${CMAKE_SOURCE_DIR}/third_party)
add_test(NAME splash_plan_test COMMAND splash_plan_test)
set_tests_properties(splash_plan_test PROPERTIES TIMEOUT 30)

# Kapitsa's server and CLI: `kapitsa serve --model <name|dir> ...`, with the chat page (src/server/chat.html)
# embedded, the coding-agent launchers (src/server/launch.cpp) and `kapitsa update` (src/server/update_cmd.cpp). The API
# translations (src/api/) and the updater (src/update/) are in the library.
# build/nace-infer-server stays as a symlink to it for scripts written before the rename.
set(KAPITSA_CHAT ${CMAKE_BINARY_DIR}/generated/chat_page.cpp)
add_custom_command(
  OUTPUT ${KAPITSA_CHAT}
  COMMAND ${CMAKE_COMMAND} -DOUT=${KAPITSA_CHAT} -DSRC=${CMAKE_SOURCE_DIR}/src/server/chat.html -DNAME=kChatPage
          -P ${CMAKE_SOURCE_DIR}/cmake/embed_file.cmake
  DEPENDS ${CMAKE_SOURCE_DIR}/src/server/chat.html ${CMAKE_SOURCE_DIR}/cmake/embed_file.cmake
  COMMENT "Embedding the chat page")
add_executable(kapitsa ${CMAKE_SOURCE_DIR}/src/server/main.cpp ${CMAKE_SOURCE_DIR}/src/server/native_execution.cpp
  ${CMAKE_SOURCE_DIR}/src/server/http_stream.cpp
  ${CMAKE_SOURCE_DIR}/src/server/launch.cpp
  ${CMAKE_SOURCE_DIR}/src/server/ui.cpp ${CMAKE_SOURCE_DIR}/src/server/beam.cpp ${CMAKE_SOURCE_DIR}/src/server/picker.cpp
  ${CMAKE_SOURCE_DIR}/src/server/bench_cmd.cpp ${CMAKE_SOURCE_DIR}/src/server/update_cmd.cpp
  ${CMAKE_SOURCE_DIR}/src/server/stage_cmd.cpp ${CMAKE_SOURCE_DIR}/src/server/route.cpp
  ${CMAKE_SOURCE_DIR}/src/server/cluster_cmd.cpp ${CMAKE_SOURCE_DIR}/src/server/pair.cpp ${KAPITSA_CHAT})
target_include_directories(kapitsa PRIVATE ${CMAKE_SOURCE_DIR}/src)
target_link_libraries(kapitsa PRIVATE naceinfer "-framework CoreFoundation")
target_compile_definitions(kapitsa PRIVATE KAPITSA_VERSION="${KAPITSA_VERSION}" KAPITSA_GIT="${KAPITSA_GIT}")
add_custom_command(TARGET kapitsa POST_BUILD
  COMMAND ${CMAKE_COMMAND} -E rm -f ${CMAKE_BINARY_DIR}/nace-infer-server
  COMMAND ${CMAKE_COMMAND} -E create_symlink kapitsa ${CMAKE_BINARY_DIR}/nace-infer-server)

add_executable(systemone_codes_driver EXCLUDE_FROM_ALL
  tests/systemone_codes_driver.cpp src/systemone/systemone.cpp src/tokenizer/tokenizer.cpp)
target_include_directories(systemone_codes_driver PRIVATE src third_party)
target_link_libraries(systemone_codes_driver PRIVATE "-framework CoreFoundation")
add_executable(systemone_codes_probe_test EXCLUDE_FROM_ALL
  tests/systemone_codes_probe_test.cpp src/systemone/systemone.cpp)
target_include_directories(systemone_codes_probe_test PRIVATE src third_party)

# In-process SDK. Opt-in so the existing CLI build stays unchanged.
option(KAPITSA_BUILD_SDK "Build the in-process C ABI shared library" OFF)
if(KAPITSA_BUILD_SDK)
  set_target_properties(naceinfer PROPERTIES POSITION_INDEPENDENT_CODE ON)
  add_library(kapitsa_sdk SHARED sdk/c/kapitsa.cpp)
  target_include_directories(kapitsa_sdk PUBLIC sdk/c PRIVATE src)
  target_link_libraries(kapitsa_sdk PRIVATE naceinfer)
  target_link_options(kapitsa_sdk PRIVATE "LINKER:-exported_symbols_list,${CMAKE_CURRENT_SOURCE_DIR}/sdk/c/exports.txt")
  set_property(TARGET kapitsa_sdk APPEND PROPERTY LINK_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/sdk/c/exports.txt")
  set_target_properties(kapitsa_sdk PROPERTIES CXX_VISIBILITY_PRESET hidden
    VISIBILITY_INLINES_HIDDEN YES VERSION 1.0.0 SOVERSION 1)
  add_executable(sdk_contract_test sdk/c/contract_test.cpp)
  target_include_directories(sdk_contract_test PRIVATE sdk/c src third_party)
  target_link_libraries(sdk_contract_test PRIVATE kapitsa_sdk)
  add_test(NAME sdk_contract_test COMMAND sdk_contract_test)
  add_executable(sdk_model_test sdk/c/model_test.cpp)
  target_include_directories(sdk_model_test PRIVATE third_party)
  target_link_libraries(sdk_model_test PRIVATE kapitsa_sdk)
  # Fault hooks only in this test's objects, never in the CLI or shared library.
  add_executable(sdk_deferred_test sdk/c/deferred_test.cpp sdk/c/kapitsa.cpp src/metal/gpu.mm src/engine/engine.cpp)
  target_include_directories(sdk_deferred_test PRIVATE sdk/c src third_party)
  target_compile_definitions(sdk_deferred_test PRIVATE NI_PIPELINE_TEST)
  target_link_libraries(sdk_deferred_test PRIVATE naceinfer)
  # Real-model test: built in CI but run only with explicit GPU authorization.
  install(TARGETS kapitsa_sdk LIBRARY DESTINATION lib)
  install(FILES sdk/c/kapitsa.h DESTINATION include)
endif()
