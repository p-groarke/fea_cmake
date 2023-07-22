cmake_minimum_required (VERSION 3.20)
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
set(CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR}/generators ${CMAKE_MODULE_PATH})
set(CMAKE_PREFIX_PATH ${CMAKE_BINARY_DIR}/generators ${CMAKE_PREFIX_PATH})

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

# Copies the CMakeLists.fea_cmake.txt file to your base directory.
function(fea_import_fea_cmake_download)
	configure_file(${FEA_CMAKE_DIR}/CMakeLists.fea_cmake.txt ${CMAKE_CURRENT_SOURCE_DIR}/CMakeLists.fea_cmake.txt COPYONLY)
endfunction()

# Copies .clang-format from fea_cmake to your base directory.
function(fea_import_clangformat)
	configure_file(${FEA_CMAKE_DIR}/.clang-format ${CMAKE_CURRENT_SOURCE_DIR}/.clang-format COPYONLY)
endfunction()

# Copies .clang-format from fea_cmake to your base directory.
function(fea_import_gitignore)
	configure_file(${FEA_CMAKE_DIR}/.gitignore ${CMAKE_CURRENT_SOURCE_DIR}/.gitignore COPYONLY)
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
		message("\nUsing local '${LIB_NAME}' from : ${FETCHCONTENT_SOURCE_DIR_${LIB_NAME_CAPS}}")
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


# Parses input args and sets CONAN_USER_OPTIONS.
# Finds current arch and toolset if applicable,
# outputs to CONAN_ARCH and CONAN_TOOLSET.
function(fea_impl_pull_conan_get_info)
	# Cannot use ARGN directly with list() command,
	# so copy it to a variable first.
	set(EXTRA_ARGS ${ARGN})

	# Did we get any optional args?
	list(LENGTH EXTRA_ARGS ARG_COUNT)
	if (${ARG_COUNT} GREATER 0)
		string(REPLACE ";" " " MCONAN_USER_OPTIONS "${EXTRA_ARGS}")
		separate_arguments(MCONAN_USER_OPTIONS UNIX_COMMAND "${MCONAN_USER_OPTIONS}")

		message("\tExtra conan arguments : '${MCONAN_USER_OPTIONS}'")
	else()
		set(MCONAN_USER_OPTIONS)
	endif ()

	# Cross-compiling to 32bits on Windows.
	if (CMAKE_HOST_SYSTEM_PROCESSOR MATCHES AMD64 AND CMAKE_GENERATOR_PLATFORM MATCHES Win32)
		message("\tCross-compiling to 32bits.")
		set(MCONAN_ARCH "-s arch=x86")
		separate_arguments(MCONAN_ARCH UNIX_COMMAND "${MCONAN_ARCH}")
	else()
		set(MCONAN_ARCH)
	endif()

	if (WIN32)
		set(MCONAN_TOOLSET "-s compiler.toolset=${CMAKE_VS_PLATFORM_TOOLSET}")
		separate_arguments(MCONAN_TOOLSET UNIX_COMMAND "${MCONAN_TOOLSET}")
	else()
		set(MCONAN_TOOLSET)
	endif()

	# Return vars.
	set(CONAN_USER_OPTIONS ${MCONAN_USER_OPTIONS} PARENT_SCOPE)
	set(CONAN_ARCH ${MCONAN_ARCH} PARENT_SCOPE)
	set(CONAN_TOOLSET ${MCONAN_TOOLSET} PARENT_SCOPE)
endfunction()


# Pulls conan Debug dependencies according to platform settings.
# You can pass extra conan options to this command (strings),
# and they will be appended to the conan call.
function(fea_pull_conan_debug)
	message("Pulling conan debug dependencies.")

	# Computes user extra arguments, arch and toolset.
	fea_impl_pull_conan_get_info(${ARGN})

	execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} --build missing
		-s build_type=Debug ${CONAN_ARCH} ${CONAN_TOOLSET} ${CONAN_USER_OPTIONS} --update
		COMMAND_ECHO STDOUT
	)
endfunction()

# Pulls conan Release dependencies according to platform settings.
# You can pass extra conan options to this command (strings),
# and they will be appended to the conan call.
function(fea_pull_conan_release)
	message("Pulling conan release dependencies.")

	# Computes user extra arguments, arch and toolset.
	fea_impl_pull_conan_get_info(${ARGN})

	execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} --build missing
		-s build_type=Release ${CONAN_ARCH} ${CONAN_TOOLSET} ${CONAN_USER_OPTIONS} --update
		COMMAND_ECHO STDOUT
	)
endfunction()

# Pulls conan dependencies according to platform settings.
# You can pass extra conan options to this command (strings),
# and they will be appended to the conan call.
function(fea_pull_conan)
	fea_pull_conan_debug(${ARGN})
	fea_pull_conan_release(${ARGN})
endfunction()

# Pulls conan dependencies according to platform settings and
# using provided lockfile.
# You must provide your conanfile path (conanfile.txt or conanfile.py),
# plus the lockfile to use. This way, it works with --base lockfiles.
#
# Note, to create a partial lockfile :
# conan lock create ..\conanfile.txt --base
#
# You can pass extra conan options to this command (strings),
# and they will be appended to the conan call.
function(fea_pull_conan_locked CONANFILEPATH LOCKFILEPATH)
	message("Pulling conan dependencies.")

	# Computes user extra arguments, arch and toolset.
	fea_impl_pull_conan_get_info(${ARGN})

	# We expect partial lockfiles (aka, revision lockfile), so we must
	# generate a new "full" lockfile using that input, for the current
	# platform, options, settings, etc.
	execute_process(COMMAND conan lock create ${CONANFILEPATH} --lockfile=${LOCKFILEPATH}
		--build=missing -s build_type=Debug ${CONAN_ARCH} ${CONAN_TOOLSET} ${CONAN_USER_OPTIONS}
		--lockfile-out=${CMAKE_CURRENT_BINARY_DIR}/conan_debug.lock --update
		COMMAND_ECHO STDOUT
	)

	execute_process(COMMAND conan lock create ${CONANFILEPATH} --lockfile=${LOCKFILEPATH}
		--build=missing -s build_type=Release ${CONAN_ARCH} ${CONAN_TOOLSET} ${CONAN_USER_OPTIONS}
		--lockfile-out=${CMAKE_CURRENT_BINARY_DIR}/conan_release.lock --update
		COMMAND_ECHO STDOUT
	)

	execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} --build=missing
		--lockfile=${CMAKE_CURRENT_BINARY_DIR}/conan_debug.lock
		COMMAND_ECHO STDOUT
	)
	execute_process(COMMAND conan install ${CMAKE_CURRENT_SOURCE_DIR} --build=missing
		--lockfile=${CMAKE_CURRENT_BINARY_DIR}/conan_release.lock
		COMMAND_ECHO STDOUT
	)
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