{pkgs}: {
  deps = [
    pkgs.rustc
    pkgs.openssl
    pkgs.libiconv
    pkgs.cargo
    pkgs.libxcrypt
    pkgs.tk
    pkgs.tcl
    pkgs.qhull
    pkgs.pkg-config
    pkgs.gtk3
    pkgs.gobject-introspection
    pkgs.ghostscript
    pkgs.freetype
    pkgs.ffmpeg-full
    pkgs.cairo
    pkgs.glibcLocales
  ];
}
