import os

# https://docs.conan.io/1/howtos/sanitizers.html#id5
class FeaDebugSanitizerHook(object):
    def __init__(self):
        self._old_cxx_flags = None

    def set_sanitize_address_flag(self, conanfile):
        if conanfile.settings.build_type != "Debug":
            return

        opt_str = " -fsanitize=address"
        if conanfile.settings.compiler == "msvc":
            opt_str = " /fsanitize=address"

        self._old_cxx_flags = os.environ.get("CXXFLAGS")
        flags_str = self._old_cxx_flags or ""
        os.environ["CXXFLAGS"] = flags_str + opt_str

    def reset_sanitize_address_flag(self, conanfile):
        if conanfile.settings.build_type != "Debug":
            return
            
        if self._old_cxx_flags is None:
            del os.environ["CXXFLAGS"]
        else:
            os.environ["CXXFLAGS"] = self._old_cxx_flags


sanitizer = FeaDebugSanitizerHook()


def pre_build(output, conanfile, **kwargs):
    sanitizer.set_sanitize_address_flag(conanfile)


def post_build(output, conanfile, **kwargs):
    sanitizer.reset_sanitize_address_flag(conanfile)