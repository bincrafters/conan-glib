#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, tools, Meson
import os
import shutil
import glob


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
    requires = "zlib/1.2.11@conan/stable", "libffi/3.2.1@bincrafters/stable"
    exports_sources = ["patches/*.patch"]

    def configure(self):
        del self.settings.compiler.libcxx

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.os != "Linux":
            del self.options.with_mount
            del self.options.with_selinux

    def requirements(self):
        if self.options.with_pcre:
            self.requires.add("pcre/8.41@bincrafters/stable")
        if self.options.with_elf:
            self.requires.add("libelf/0.8.13@bincrafters/stable")
        if self.settings.os == "Linux":
            if self.options.with_mount:
                self.requires.add("libmount/2.33.1@bincrafters/stable")
            if self.options.with_selinux:
                self.requires.add("libselinux/2.8@bincrafters/stable")

    def source(self):
        tools.get("{0}/archive/{1}.tar.gz".format(self.homepage, self.version))
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def build_requirements(self):
        if not tools.which("meson"):
            self.build_requires("meson_installer/0.50.0@bincrafters/stable")
        if not tools.which("pkg-config"):
            self.build_requires("pkg-config_installer/0.29.2@bincrafters/stable")

    def _configure_meson(self):
        meson = Meson(self)
        defs = dict()
        if tools.is_apple_os(self.settings.os):
            defs["iconv"] = "native"  # https://gitlab.gnome.org/GNOME/glib/issues/1557
        meson.configure(source_folder=self._source_subfolder,
                        build_folder=self._build_subfolder, defs=defs)
        return meson

    def _apply_patches(self):
        for filename in sorted(glob.glob("patches/*.patch")):
            self.output.info('applying patch "%s"' % filename)
            tools.patch(base_path=self._source_subfolder, patch_file=filename)

    def build(self):
        self._apply_patches()
        if self.settings.os == "Linux" and self.options.with_mount:
            shutil.move("libmount.pc", "mount.pc")
        if self.options.with_pcre:
            shutil.move("pcre.pc", "libpcre.pc")
        for filename in [os.path.join(self._source_subfolder, "meson.build"),
                         os.path.join(self._source_subfolder, "glib", "meson.build"),
                         os.path.join(self._source_subfolder, "gobject", "meson.build"),
                         os.path.join(self._source_subfolder, "gio", "meson.build")]:
            tools.replace_in_file(filename, "subdir('tests')", "#subdir('tests')")
        with tools.environment_append({"PKG_CONFIG_PATH": [self.source_folder]}):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        with tools.environment_append({"PKG_CONFIG_PATH": [self.source_folder]}):
            meson = self._configure_meson()
            meson.install()

    def package_info(self):
        self.cpp_info.libs = ["gio-2.0", "gmodule-2.0", "gobject-2.0", "gthread-2.0", "glib-2.0"]
        if self.settings.os == "Linux":
            self.cpp_info.libs.append("pthread")
        if self.settings.os != "Linux":
            self.cpp_info.libs.append("intl")
        self.cpp_info.includedirs.append(os.path.join('include', 'glib-2.0'))
        self.cpp_info.includedirs.append(os.path.join('lib', 'glib-2.0', 'include'))
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        if self.settings.os == "Macos":
            self.cpp_info.libs.append("iconv")
            frameworks = ['Foundation', 'CoreServices', 'CoreFoundation']
            for framework in frameworks:
                self.cpp_info.exelinkflags.append("-framework %s" % framework)
            self.cpp_info.sharedlinkflags = self.cpp_info.exelinkflags
