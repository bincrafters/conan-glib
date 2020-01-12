from conans import ConanFile, tools, Meson, VisualStudioBuildEnvironment
import os
import shutil
import glob


class GLibConan(ConanFile):
    name = "glib"
    description = "GLib provides the core application building blocks for libraries and applications written in C"
    topics = ("conan", "glib", "gobject", "gio", "gmodule")
    url = "https://github.com/bincrafters/conan-glib"
    homepage = "https://gitlab.gnome.org/GNOME/glib"
    license = "LGPL-2.1"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False],
               "fPIC": [True, False],
               "with_pcre": [True, False],
               "with_elf": [True, False],
               "with_selinux": [True, False],
               "with_mount": [True, False]}
    default_options = {"shared": False,
                       "fPIC": True,
                       "with_pcre": True,
                       "with_elf": True,
                       "with_mount": True,
                       "with_selinux": True}
    _source_subfolder = "source_subfolder"
    _build_subfolder = 'build_subfolder'
    autotools = None
    short_paths = True
    generators = "pkg_config"
    requires = "zlib/1.2.11", "libffi/3.2.1"

    @property
    def _is_msvc(self):
        return self.settings.compiler == "Visual Studio"

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_mount
            del self.options.with_selinux

    def build_requirements(self):
        if not tools.which("meson"):
            self.build_requires("meson/0.53.0")
        if not tools.which("pkg-config"):
            self.build_requires("pkg-config_installer/0.29.2@bincrafters/stable")

    def requirements(self):
        if self.options.with_pcre:
            self.requires.add("pcre/8.41")
        if self.options.with_elf:
            self.requires.add("libelf/0.8.13")
        if self.settings.os == "Linux":
            if self.options.with_mount:
                self.requires.add("libmount/2.33.1")
            if self.options.with_selinux:
                self.requires.add("libselinux/2.9@bincrafters/stable")
        else:
            # for Linux, gettext is provided by libc
            self.requires.add("gettext/0.20.1@bincrafters/stable")

        if tools.is_apple_os(self.settings.os):
            self.requires.add("libiconv/1.15")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

        tools.replace_in_file(os.path.join(self._source_subfolder, 'meson.build'), \
            'build_tests = not meson.is_cross_build() or (meson.is_cross_build() and meson.has_exe_wrapper())', \
            'build_tests = false')

    def _configure_meson(self):
        meson = Meson(self)
        defs = dict()
        if tools.is_apple_os(self.settings.os):
            defs["iconv"] = "external"  # https://gitlab.gnome.org/GNOME/glib/issues/1557
        if self.settings.os == "Linux":
            defs["selinux"] = "enabled" if self.options.with_selinux else "disabled"
            defs["libmount"] = self.options.with_mount
        defs["internal_pcre"] = not self.options.with_pcre

        meson.configure(source_folder=self._source_subfolder,
                        build_folder=self._build_subfolder, defs=defs)
        return meson

    def build(self):
        for filename in [os.path.join(self._source_subfolder, "meson.build"),
                         os.path.join(self._source_subfolder, "glib", "meson.build"),
                         os.path.join(self._source_subfolder, "gobject", "meson.build"),
                         os.path.join(self._source_subfolder, "gio", "meson.build")]:
            tools.replace_in_file(filename, "subdir('tests')", "#subdir('tests')")
        # allow to find gettext
        tools.replace_in_file(os.path.join(self._source_subfolder, "meson.build"),
                              "libintl = cc.find_library('intl', required : false)",
                              "libintl = cc.find_library('gnuintl', required : false)")
        with tools.environment_append(VisualStudioBuildEnvironment(self).vars) if self._is_msvc else tools.no_op():
            meson = self._configure_meson()
            meson.build()

    def _fix_library_names(self):
        if self.settings.compiler == "Visual Studio":
            with tools.chdir(os.path.join(self.package_folder, "lib")):
                for filename_old in glob.glob("*.a"):
                    filename_new = filename_old[3:-2] + ".lib"
                    self.output.info("rename %s into %s" % (filename_old, filename_new))
                    shutil.move(filename_old, filename_new)

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        with tools.environment_append(VisualStudioBuildEnvironment(self).vars) if self._is_msvc else tools.no_op():
            meson = self._configure_meson()
            meson.install()
            self._fix_library_names()

    def package_info(self):
        self.cpp_info.libs = ["gio-2.0", "gmodule-2.0", "gobject-2.0", "gthread-2.0", "glib-2.0"]
        if self.settings.os == "Linux":
            self.cpp_info.libs.append("pthread")
        if self.settings.os == "Windows":
            self.cpp_info.libs.extend(["ws2_32", "ole32", "shell32", "user32", "advapi32"])
        self.cpp_info.includedirs.append(os.path.join('include', 'glib-2.0'))
        self.cpp_info.includedirs.append(os.path.join('lib', 'glib-2.0', 'include'))
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        if self.settings.os == "Macos":
            self.cpp_info.libs.append("iconv")
            self.cpp_info.frameworks.extend(['Foundation', 'CoreServices', 'CoreFoundation'])
