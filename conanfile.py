#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, Meson
import os
import shutil


class GLibConan(ConanFile):
    name = "glib"
    version = "2.58.3"
    description = "GLib provides the core application building blocks for libraries and applications written in C"
    url = "https://github.com/bincrafters/conan-glib"
    homepage = "https://github.com/GNOME/glib"
    author = "BinCrafters <bincrafters@gmail.com>"
    license = "LGPL-2.1"
    exports = ["LICENSE.md"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "with_pcre": [True, False]}
    default_options = "shared=False", "fPIC=True", "with_pcre=False"
    _source_subfolder = "source_subfolder"
    _build_subfolder = 'build_subfolder'
    autotools = None
    short_paths = True
    generators = "pkg_config"
    requires = "zlib/1.2.11@conan/stable", "libffi/3.2.1@bincrafters/stable"

    def configure(self):
        del self.settings.compiler.libcxx

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        if self.options.with_pcre:
            self.requires.add("pcre/8.41@bincraftres/stable")
        #if self.settings.os == "Linux":
        #    self.requires.add("libmount/2.33.1@bincrafters/stable")

    def source(self):
        tools.get("{0}/archive/{1}.tar.gz".format(self.homepage, self.version))
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def build_requirements(self):
        if not tools.which("meson"):
            self.build_requires("meson_installer/0.49.0@bincrafters/stable")

    def _configure_meson(self):
        meson = Meson(self)
        defs = dict()
        if tools.is_apple_os(self.settings.os):
            defs["iconv"] = "native"  # https://gitlab.gnome.org/GNOME/glib/issues/1557
        elif self.settings.os == "Linux":
            defs["selinux"] = "false"
            defs["libmount"] = "false"
            defs["libdir"] = "lib"
        meson.configure(source_folder=self._source_subfolder,
                        build_folder=self._build_subfolder, defs=defs)
        return meson

    def build(self):
        #if self.settings.os == "Linux":
        #    shutil.move("libmount.pc", "mount.pc")
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
        self.cpp_info.includedirs.append(os.path.join('include', 'glib-2.0'))
        self.cpp_info.includedirs.append(os.path.join('lib', 'glib-2.0', 'include'))
