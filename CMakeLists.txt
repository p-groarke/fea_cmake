cmake_minimum_required (VERSION 3.20)
enable_language(CXX)

include(FetchContent)
include(GNUInstallDirs)
include(CMakePackageConfigHelpers)
include(GoogleTest)
include(GenerateExportHeader)
include(GetPrerequisites)

# Applies standard and expected settings to your cmake. Opt-in.
macro(fea_standard_settings)
	cmake_policy(SET CMP0054 NEW)
	cmake_policy(SET CMP0011 NEW)

	# Conan search paths.
	set(CMAKE_MODULE_PATH
		${CMAKE_BINARY_DIR}
		${CMAKE_BINARY_DIR}/generators
		${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/generators
		# ${CMAKE_CURRENT_BINARY_DIR}
		# ${CMAKE_CURRENT_BINARY_DIR}/generators
		# ${CMAKE_CURRENT_BINARY_DIR}/${CMAKE_BUILD_TYPE}/generators
		${CMAKE_MODULE_PATH}
	)
	set(CMAKE_PREFIX_PATH
		${CMAKE_BINARY_DIR}
		${CMAKE_BINARY_DIR}/generators
		${CMAKE_BINARY_DIR}/${CMAKE_BUILD_TYPE}/generators
		# ${CMAKE_CURRENT_BINARY_DIR}
		# ${CMAKE_CURRENT_BINARY_DIR}/generators
		# ${CMAKE_CURRENT_BINARY_DIR}/${CMAKE_BUILD_TYPE}/generators
		${CMAKE_PREFIX_PATH}
	)

	# Organize unrelated targets to clean IDE hierarchy.
	set(DEPENDENCY_FOLDER "Dependencies")
	set_property(GLOBAL PROPERTY USE_FOLDERS ON)
	set_property(GLOBAL PROPERTY PREDEFINED_TARGETS_FOLDER ${DEPENDENCY_FOLDER})

	# Be strict
	set(CMAKE_C_STANDARD 11)
	set(CMAKE_CXX_STANDARD_REQUIRED ON)
	set(CMAKE_CXX_EXTENSIONS OFF)

	# When called from functions, current_list_dir and current_source_dir
	# are incorrect. Cache the real path to this cmakelists.txt.
	set(FEA_CMAKE_DIR ${CMAKE_CURRENT_LIST_DIR})
endmacro()

# Copies the CMakeLists.fea_cmake.txt file to your base directory.
function(fea_import_fea_cmake_download)
	configure_file(${FEA_CMAKE_DIR}/CMakeLists.fea_cmake.txt ${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.fea_cmake.txt COPYONLY)
endfunction()

# Copies .clang-format from fea_cmake to your base directory.
function(fea_import_clangformat)
	configure_file(${FEA_CMAKE_DIR}/.clang-format ${CMAKE_CURRENT_SOURCE_DIR}/.clang-format COPYONLY)
endfunction()

# Copies .gitignore from fea_cmake to your base directory.
function(fea_import_gitignore)
	configure_file(${FEA_CMAKE_DIR}/.gitignore ${CMAKE_CURRENT_SOURCE_DIR}/.gitignore COPYONLY)
endfunction()

# Copies .gitattributes from fea_cmake to your base directory.
function(fea_import_gitattributes)
	configure_file(${FEA_CMAKE_DIR}/.gitattributes ${CMAKE_CURRENT_SOURCE_DIR}/.gitattributes COPYONLY)
endfunction()

# Make output directory predictabe
function(fea_set_output_dir OUT_DIR)
	# Output binary to predictable location (fixes cyclic dependency issues).
	set(BINARY_OUT_DIR ${OUT_DIR})
	file(MAKE_DIRECTORY ${BINARY_OUT_DIR})

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

# Fetch a dependency through FetchContent.
# Respects and uses the variable 'LIB_NAME_LOCAL' to pull
# from a local directory (searches for 'PROJECT_DIR/../LIB_NAME').
function(fea_fetch_content LIB_NAME REPOSITORY TAG)
	set(LIB_NAME_CAPS "")
	string(TOUPPER ${LIB_NAME} LIB_NAME_CAPS)

	if (${${LIB_NAME_CAPS}_LOCAL})
		set (FETCHCONTENT_SOURCE_DIR_${LIB_NAME_CAPS} ${CMAKE_SOURCE_DIR}/../${LIB_NAME} CACHE INTERNAL "")
		message(STATUS "Using local '${LIB_NAME}' from : ${FETCHCONTENT_SOURCE_DIR_${LIB_NAME_CAPS}}")
	endif()

	FetchContent_Declare(${LIB_NAME}
		GIT_REPOSITORY ${REPOSITORY}
		GIT_TAG ${TAG}
	)
	FetchContent_MakeAvailable(${LIB_NAME})
endfunction()

# Compile Options
function(fea_set_compile_options TARGET EXPOSURE)
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

# Enable required Release profiling options (Windows)
function(fea_release_profiling TARGET)
	target_compile_options(${TARGET} PUBLIC /Zi)
	target_link_options(${TARGET} PUBLIC /DEBUG)
endfunction()

# Fails build if process doesn't succeed.
# Pass arguments of execute_process plus :
# ERROR_MSG "My error message."
function(fea_execute_process)
	set(SINGLE_VAL_ARGS ERROR_MSG)
	cmake_parse_arguments(MARGS "" "${SINGLE_VAL_ARGS}" "" ${ARGN})
	execute_process(
		${MARGS_UNPARSED_ARGUMENTS}
		RESULT_VARIABLE RET
	)

	if (RET AND NOT RET EQUAL 0)
		message(FATAL_ERROR "${MARGS_ERROR_MSG}\n")
	endif()
endfunction()


# Pulls conan and everything.
function(fea_pull_conan_imp)
	set(SINGLE_ARGS CONAN_VER CONAN_BUILD_TYPE CONAN_MSVC_TOOLSET)
	set(MULTI_ARGS CONAN_ARGS CONAN_ARGS_MSVC CONAN_ARGS_CLANG CONAN_ARGS_GCC)
	cmake_parse_arguments(IN "" "${SINGLE_ARGS}" "${MULTI_ARGS}" ${ARGN})

	# Sanitize inputs.
	string(REPLACE ";" " " IN_CONAN_VER "${IN_CONAN_VER}")
	string(REPLACE ";" " " IN_CONAN_BUILD_TYPE "${IN_CONAN_BUILD_TYPE}")
	string(REPLACE ";" " " IN_CONAN_MSVC_TOOLSET "${IN_CONAN_MSVC_TOOLSET}")
	string(REPLACE ";" " " IN_CONAN_ARGS "${IN_CONAN_ARGS}")
	string(REPLACE ";" " " IN_CONAN_ARGS_MSVC "${IN_CONAN_ARGS_MSVC}")
	string(REPLACE ";" " " IN_CONAN_ARGS_CLANG "${IN_CONAN_ARGS_CLANG}")
	string(REPLACE ";" " " IN_CONAN_ARGS_GNU "${IN_CONAN_ARGS_GNU}")

	if (NOT IN_CONAN_VER EQUAL 1 AND NOT IN_CONAN_VER EQUAL 2)
		message(WARNING "No conan version provided, defaulting to '1'.")
		set(IN_CONAN_VER 1)
	endif()

	# Set compile options per platform.
	if (CMAKE_CXX_COMPILER_ID MATCHES Clang)
		set(IN_CONAN_ARGS "${IN_CONAN_ARGS} ${IN_CONAN_ARGS_CLANG}")
	elseif (CMAKE_CXX_COMPILER_ID MATCHES GNU)
		set(IN_CONAN_ARGS "${IN_CONAN_ARGS} ${IN_CONAN_ARGS_GNU}")
	elseif (CMAKE_CXX_COMPILER_ID MATCHES MSVC)
		set(IN_CONAN_ARGS "${IN_CONAN_ARGS} ${IN_CONAN_ARGS_MSVC}")

		if (NOT IN_CONAN_MSVC_TOOLSET STREQUAL "")
			# Assuming this OK with added conan 2 toolsets in settings.
			set(IN_CONAN_ARGS "-s compiler.toolset=${IN_CONAN_MSVC_TOOLSET} ${IN_CONAN_ARGS}")

		# TODO : Investigate some more. Maybe conan 2 has a different way to change toolset?
		# 	if (IN_CONAN_VER EQUAL 1)
		# 	else()
		# 		message(STATUS "CONAN_MSVC_TOOLSET skipped in conan 2. Investigation under way.")
		# 	endif()
		endif()

		# Cross-compiling to 32bits on Windows.
		if (CMAKE_HOST_SYSTEM_PROCESSOR MATCHES AMD64 AND CMAKE_GENERATOR_PLATFORM MATCHES Win32)
			message(STATUS "Cross-compiling to 32bits.")
			set(IN_CONAN_ARGS "-s arch=x86 ${IN_CONAN_ARGS}")
		endif()
	endif()

	# Conan 1.
	# if (IN_CONAN_VER EQUAL 1)
	# endif()

	# Conan 2.
	if (IN_CONAN_VER EQUAL 2)
		# Install user settings to fix msvc toolsets in conan 2.
		fea_execute_process(COMMAND conan config install ${FEA_CMAKE_DIR}/.conan2/settings_user.yml
			COMMAND_ECHO STDOUT
			ERROR_MSG "Couldn't install conan settings_user.xml"
		)

		# # output-folder shenanigans
		# set(IN_CONAN_ARGS "--output-folder ${CMAKE_SOURCE_DIR} ${IN_CONAN_ARGS}")
	endif()

	# output-folder shenanigans for FetchContent.
	set(IN_CONAN_ARGS "--output-folder ${CMAKE_SOURCE_DIR} ${IN_CONAN_ARGS}")

	# Build-type
	set(IN_CONAN_ARGS "-s build_type=${IN_CONAN_BUILD_TYPE} ${IN_CONAN_ARGS}")

	# cppstd
	set(IN_CONAN_ARGS "-s compiler.cppstd=${CMAKE_CXX_STANDARD} ${IN_CONAN_ARGS}")

	# Finally, sanitize and call conan.
	separate_arguments(IN_CONAN_ARGS UNIX_COMMAND "${IN_CONAN_ARGS}")
	message(STATUS "Conan arguments : '${IN_CONAN_ARGS}'")

	fea_execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR}
		${IN_CONAN_ARGS} --update
		COMMAND_ECHO STDOUT
		ERROR_MSG "Failed to pull conan dependencies."
	)

endfunction()

# Conan
# Pulls conan dependencies according to platform settings.
# You can pass extra conan options to this command (strings),
# and they will be appended to the conan call.
#
# Supported single-arguments :
# CONAN_MSVC_TOOLSET, CONAN_VER, CONAN_BUILD_TYPE
#
# Supported multi-arguments :
# CONAN_ARGS, CONAN_ARGS_CLANG, CONAN_ARGS_GNU, CONAN_ARGS_MSVC

# Conan 1
function(fea_pull_conan)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Debug CONAN_VER 1)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Release CONAN_VER 1)
endfunction()

function(fea_pull_conan_debug)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Debug CONAN_VER 1)
endfunction()

function(fea_pull_conan_release)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Release CONAN_VER 1)
endfunction()

# Conan 2
function(fea_pull_conan2)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Debug CONAN_VER 2)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Release CONAN_VER 2)
endfunction()

function(fea_pull_conan2_debug)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Debug CONAN_VER 2)
endfunction()

function(fea_pull_conan2_release)
	fea_pull_conan_imp(${ARGN} CONAN_BUILD_TYPE Release CONAN_VER 2)
endfunction()


# Copies a data folder on build. Ignores stamps and file changes.
function(fea_copy_on_build TARGET DATA_IN_DIR DATA_OUT_DIR)
	add_custom_command(TARGET ${TARGET} POST_BUILD
		COMMAND ${CMAKE_COMMAND} -E make_directory ${DATA_OUT_DIR}
		COMMAND ${CMAKE_COMMAND} -E copy_directory ${DATA_IN_DIR} ${DATA_OUT_DIR}
	)
endfunction()

# Keeps track of input files and copies them to your output
# directory when they've changed.
# Will be supplemanted by copy_directory_if_different in cmake 3.26.
function(fea_copy_on_build_if_different TARGET DATA_IN_DIR DATA_OUT_DIR)
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

# Converts any cmake bool to 0 or 1.
function(fea_bool_to_int IN_VAR OUT_VAR)
	if (${IN_VAR})
		set(${OUT_VAR} 1 PARENT_SCOPE)
	else()
		set(${OUT_VAR} 0 PARENT_SCOPE)
	endif()
endfunction()

# Converts any cmake bool to False or True
function(fea_bool_to_pybool IN_VAR OUT_VAR)
	if (${IN_VAR})
		set(${OUT_VAR} True PARENT_SCOPE)
	else()
		set(${OUT_VAR} False PARENT_SCOPE)
	endif()
endfunction()

# Used internally.
function(fea_target_replace_definitions_imp TARGET VISIBILITY PROPERTY_NAME)
	get_target_property(MDEFINITIONS ${TARGET} ${PROPERTY_NAME})
	if (MDEFINITIONS STREQUAL "MDEFINITIONS-NOTFOUND")
		message(FATAL_ERROR "fea_target_replace_definitions : Couldn't parse target definitions '${PROPERTY_NAME}'."
			"Did you provide visibility PUBLIC, INTERFACE, PRIVATE?")
	endif()

	# Replace definitions.
	foreach(MDEF ${ARGN})
		string(REGEX REPLACE "=.*" "" MDEF_FILT ${MDEF})
		list(FILTER MDEFINITIONS EXCLUDE REGEX "^${MDEF_FILT}")
		list(APPEND MDEFINITIONS ${MDEF})
	endforeach()
	set_target_properties(${TARGET} PROPERTIES ${PROPERTY_NAME} "${MDEFINITIONS}")
endfunction()

# Replace a target definition.
# Ex : fea_target_replace_definitions(mytarget PRIVATE Bla=0 Blee=1)
#
# TODO : fea_target_erase_definitions
function(fea_target_replace_definitions TARGET VISIBILITY)
	# Use the right property, PUBLIC and INTERFACE are stored elsewhere.
	if (NOT ${VISIBILITY} STREQUAL "PRIVATE")
		set(MPROPERTY_NAME INTERFACE_COMPILE_DEFINITIONS)
	else()
		set(MPROPERTY_NAME COMPILE_DEFINITIONS)
	endif()

	fea_target_replace_definitions_imp(${TARGET} ${VISIBILITY} ${MPROPERTY_NAME} ${ARGN})

	# INTERFACE_COMPILE_DEFINITIONS doesn't mention configuration...
	# if (${VISIBILITY} STREQUAL "PRIVATE")
	# endif()

	foreach(OUTPUTCONFIG ${CMAKE_CONFIGURATION_TYPES})
		string(TOUPPER ${OUTPUTCONFIG} OUTPUTCONFIG)
		set(MPROPERTY_NAME ${MPROPERTY_NAME}_${OUTPUTCONFIG})

		# Check if the property exists first. This one isn't a failure if it doesn't.
		get_target_property(MTEMP ${TARGET} ${MPROPERTY_NAME})
		if (NOT MTEMP STREQUAL "MTEMP-NOTFOUND")
			fea_target_replace_definitions_imp(${TARGET} ${VISIBILITY} ${MPROPERTY_NAME} ${ARGN})
		endif()
	endforeach(OUTPUTCONFIG CMAKE_CONFIGURATION_TYPES)
endfunction()

# Enables static linking MSVC runtime library.
# Q : Equivalent on other OSes?
function(fea_static_runtime TARGET)
	if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
		set_target_properties(${TARGET} PROPERTIES MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
	endif()
endfunction()

# Enables MSVC whole program optimization on release builds.
function(fea_whole_program_optimization TARGET VISIBILITY)
	if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
		target_compile_options(${TARGET} ${VISIBILITY} $<$<CONFIG:Release>:/GL>)
		target_link_options(${TARGET} ${VISIBILITY} $<$<CONFIG:Release>:/LTCG>)
	endif()
endfunction()

# Enables -fsanitize-address on target.
function(fea_sanitize_address TARGET VISIBILITY MCONFIG)
	if (CMAKE_SYSTEM_NAME STREQUAL "Windows")
		target_compile_options(${TARGET} ${VISIBILITY} $<$<CONFIG:${MCONFIG}>:/fsanitize=address>)
		# target_link_options(${TARGET} ${VISIBILITY} $<$<CONFIG:${MCONFIG}>:/fsanitize=address>)
	else()
		target_compile_options(${TARGET} ${VISIBILITY} $<$<CONFIG:${MCONFIG}>:-fsanitize=address>)
		target_link_options(${TARGET} ${VISIBILITY} $<$<CONFIG:${MCONFIG}>:-fsanitize=address>)
	endif()
endfunction()