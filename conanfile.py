from conans import ConanFile, tools, Meson
import os
import shutil


class GLibConan(ConanFile):
    name = "glib"
    version = "2.60.3"
    description = "GLib provides the core application building blocks for libraries and applications written in C"
    url = "https://github.com/bincrafters/conan-glib"
    homepage = "https://github.com/GNOME/glib"
    license = "LGPL-2.1"
    exports = ["LICENSE.md"]
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

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_mount
            del self.options.with_selinux

    def requirements(self):
        if self.options.with_pcre:
            self.requires.add("pcre/8.41")
        if self.options.with_elf:
            self.requires.add("libelf/0.8.13")
        if self.settings.os == "Linux":
            if self.options.with_mount:
                self.requires.add("libmount/2.33.1")
            if self.options.with_selinux:
                self.requires.add("libselinux/2.8@bincrafters/stable")

    def source(self):
        tools.get("{0}/archive/{1}.tar.gz".format(self.homepage, self.version))
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def build_requirements(self):
        if not tools.which("meson"):
            self.build_requires("meson/0.52.0")
        if not tools.which("pkg-config"):
            self.build_requires("pkg-config_installer/0.29.2@bincrafters/stable")

    def _configure_meson(self):
        meson = Meson(self)
        defs = dict()
        if tools.is_apple_os(self.settings.os):
            defs["iconv"] = "native"  # https://gitlab.gnome.org/GNOME/glib/issues/1557
        elif self.settings.os == "Linux":
            defs["selinux"] = "enabled" if self.options.with_selinux else "disabled"
            defs["libmount"] = self.options.with_mount
            defs["libdir"] = "lib"
        if str(self.settings.compiler) in ["gcc", "clang"]:
            if self.settings.arch == "x86":
                defs["c_args"] = "-m32"
                defs["cpp_args"] = "-m32"
                defs["c_link_args"] = "-m32"
                defs["cpp_link_args"] = "-m32"
            elif self.settings.arch == "x86_64":
                defs["c_args"] = "-m64"
                defs["cpp_args"] = "-m64"
                defs["c_link_args"] = "-m64"
                defs["cpp_link_args"] = "-m64"
        elif self.settings.compiler == "Visual Studio":
            if self.settings.arch == "x86":
                defs["c_link_args"] = "-MACHINE:X86"
                defs["cpp_link_args"] = "-MACHINE:X86"
            elif self.settings.arch == "x86_64":
                defs["c_link_args"] = "-MACHINE:X64"
                defs["cpp_link_args"] = "-MACHINE:X64"
        meson.configure(source_folder=self._source_subfolder,
                        build_folder=self._build_subfolder, defs=defs)
        return meson

    def build(self):
        if self.options.with_pcre:
            shutil.move("pcre.pc", "libpcre.pc")
        with tools.environment_append({"PKG_CONFIG_PATH": [self.source_folder]}):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        with tools.environment_append({"PKG_CONFIG_PATH": [self.source_folder]}):
            meson = self._configure_meson()
            meson.install()

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Linux":
            self.cpp_info.libs.append("pthread")
        elif self.settings.os == "Windows":
            self.cpp_info.libs.append("ole32", "shell32")
        self.cpp_info.includedirs.append(os.path.join('include', 'glib-2.0'))
        self.cpp_info.includedirs.append(os.path.join('lib', 'glib-2.0', 'include'))
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        if self.settings.os == "Macos":
            self.cpp_info.libs.append("iconv")
            frameworks = ['Foundation', 'CoreServices']
            for framework in frameworks:
                self.cpp_info.exelinkflags.append("-framework %s" % framework)
            self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags
