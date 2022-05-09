enable_language(CXX)

include(FetchContent)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
include(GoogleTest)
include(GenerateExportHeader)
include(GetPrerequisites)

cmake_policy(SET CMP0054 NEW)
cmake_policy(SET CMP0011 NEW)

# Conan search paths.
set(CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR} ${CMAKE_MODULE_PATH})
set(CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR} ${CMAKE_PREFIX_PATH})

# Organize unrelated targets to clean IDE hierarchy.
set(DEPENDENCY_FOLDER "Dependencies")
set_property(GLOBAL PROPERTY USE_FOLDERS ON)
set_property(GLOBAL PROPERTY PREDEFINED_TARGETS_FOLDER ${DEPENDENCY_FOLDER})

# clang-format
if (EXISTS ${CMAKE_SOURCE_DIR}/.clang-format)
	configure_file(${CMAKE_SOURCE_DIR}/.clang-format ${CMAKE_BINARY_DIR}/.clang-format COPYONLY)
endif()

# Be strict
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Compile Options
function(set_compile_options TARGET EXPOSURE)
	if (CMAKE_CXX_COMPILER_ID MATCHES Clang)
		message("${TARGET} : Detected Clang compiler.")
		target_compile_options(${TARGET} ${EXPOSURE} -Wall -Wextra -Wpedantic -Werror)

	elseif (CMAKE_CXX_COMPILER_ID MATCHES GNU)
		message("${TARGET} : Detected GNU compiler.")
		target_compile_options(${TARGET} ${EXPOSURE} -Wall -Wextra -Wpedantic -Werror)

	elseif (CMAKE_CXX_COMPILER_ID MATCHES MSVC)
		message("${TARGET} : Detected MSVC compiler.")
		target_compile_definitions(${TARGET} ${EXPOSURE} NOMINMAX UNICODE _UNICODE
			_SILENCE_CXX17_UNCAUGHT_EXCEPTION_DEPRECATION_WARNING)

		target_compile_options(${TARGET} ${EXPOSURE} /Zc:__cplusplus /Zc:alignedNew
			/permissive- /W4 /WX /utf-8 /MP
			# /FAs
		)

	else()
		message(FATAL_ERROR "${TARGET} : Compiler unsupported, aborting.\n")
	endif()
endfunction()

# Make output directory predictabe
function(set_output_dir OUT_DIR)
	# Output binary to predictable location (fixes cyclic dependency issues).
	set(BINARY_OUT_DIR ${OUT_DIR})
	set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${BINARY_OUT_DIR} PARENT_SCOPE)
	set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${BINARY_OUT_DIR} PARENT_SCOPE)
	set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${BINARY_OUT_DIR} PARENT_SCOPE)

	foreach(OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES})
		string(TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG)
		set(CMAKE_RUNTIME_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${BINARY_OUT_DIR} PARENT_SCOPE)
		set(CMAKE_LIBRARY_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${BINARY_OUT_DIR} PARENT_SCOPE)
		set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY_${OUTPUTCONFIG} ${BINARY_OUT_DIR} PARENT_SCOPE)
	endforeach(OUTPUTCONFIG CMAKE_CONFIGURATION_TYPES)
	set(BINARY_OUT_DIR ${OUT_DIR} PARENT_SCOPE)
endfunction()

# Pulls conan dependencies according to platform settings.
function(pull_conan)
	message("Pulling conan dependencies.\n")

	# message("sizeof_void : ${CMAKE_SIZEOF_VOID_P }\n")
	# message("host platform : ${CMAKE_HOST_SYSTEM_PROCESSOR}")
	# message("target platform : ${CMAKE_GENERATOR_PLATFORM}\n")

	# Cross-compiling to 32bits on Windows.
	if (CMAKE_HOST_SYSTEM_PROCESSOR MATCHES AMD64 AND CMAKE_GENERATOR_PLATFORM MATCHES Win32)
		message("Cross-compiling to 32bits.\n")
		set(CONAN_ARCH "-s arch=x86")
		separate_arguments(CONAN_ARCH UNIX_COMMAND "${CONAN_ARCH}")
	else()
		set(CONAN_ARCH)
	endif()

	if (WIN32)
		set(CONAN_TOOLSET "-s compiler.toolset=${CMAKE_VS_PLATFORM_TOOLSET}")
		separate_arguments(CONAN_TOOLSET UNIX_COMMAND "${CONAN_TOOLSET}")
	else()
		set(CONAN_TOOLSET)
	endif()

	execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} --build missing -s
		build_type=Debug ${CONAN_ARCH} ${CONAN_TOOLSET}
		COMMAND_ECHO STDOUT
	)
	execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} --build missing -s
		build_type=Release ${CONAN_ARCH} ${CONAN_TOOLSET}
		COMMAND_ECHO STDOUT
	)
endfunction()


# Keeps track of input files and copies them to your output
# directory when they've changed.
function(copy_folder_on_build TARGET DATA_IN_DIR DATA_OUT_DIR)
	set(STAMP_DIR ${CMAKE_BINARY_DIR}/stamps)
	file(GLOB_RECURSE DATA_FILES "${DATA_IN_DIR}/*")

	set(STAMP_FILES "")
	foreach(FILE ${DATA_FILES})
		get_filename_component(FILENAME ${FILE} NAME)
		get_filename_component(FILE_PATH ${FILE} REALPATH DIRECTORY)
		file(RELATIVE_PATH FILE_OUTPUT_RPATH ${DATA_IN_DIR} ${FILE_PATH})
		# message("path test : ${FILE_OUTPUT_RPATH}")

		set(STAMP_FILE ${STAMP_DIR}/${FILENAME}.stamp)
		add_custom_command(
			OUTPUT ${STAMP_FILE}
			COMMAND ${CMAKE_COMMAND} -E make_directory ${STAMP_DIR}
			COMMAND ${CMAKE_COMMAND} -E make_directory ${DATA_OUT_DIR}
			COMMAND ${CMAKE_COMMAND} -E touch ${STAMP_FILE}
			COMMAND ${CMAKE_COMMAND} -E copy_if_different ${FILE}
			${DATA_OUT_DIR}/${FILE_OUTPUT_RPATH}
			DEPENDS ${FILE}
			COMMENT "Copying data file : '${FILENAME}'"
		)

		list(APPEND STAMP_FILES ${STAMP_FILE})
	endforeach()

	add_custom_target(${TARGET}_data
		SOURCES ${DATA_FILES}
		DEPENDS ${STAMP_FILES}
	)

	# set_target_properties(Shaders PROPERTIES FOLDER ${PROJECT_NAME}) # Pretty hacky :) Doesn't work on VS
	add_dependencies(${TARGET} ${TARGET}_data)
endfunction()