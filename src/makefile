# Morpheus top-level build.
#
# `make` / `make install` build the analyzer (cruncher) and its libraries.
# Rebuilding the stemlibs additionally needs flex + libfl: `make stemtools`.
# The C# port of the analyzer is built with `make cs` (requires a C# compiler).

all:
	cd greeklib; $(MAKE) greeklib.a
	cd morphlib; $(MAKE) morphlib.a
	cd gkends; $(MAKE) all
	cd gkdict; $(MAKE) gkdict.a
	cd gener; $(MAKE) all
	cd anal; $(MAKE) all

install:
	[ -d ../bin ] || mkdir ../bin
	cd gkends; $(MAKE) install
	cd gener; $(MAKE) install
	cd anal; $(MAKE) install

# Flex-based stemlib-building tools (require flex + libfl).
stemtools:
	cd gkdict; $(MAKE) stemtools

# C# port of the analyzer.
cs:
	cd anal; $(MAKE) -f makefile-cs all

clean:
	cd anal; $(MAKE) clean
	cd gener; $(MAKE) clean
	cd gkdict; $(MAKE) clean
	cd gkends; $(MAKE) clean
	cd greeklib; $(MAKE) clean
	cd morphlib; $(MAKE) clean

libs:
	cd gener; $(MAKE) gener.a
	cd gkdict; $(MAKE) gkdict.a
	cd gkends; $(MAKE) gkends.a
	cd greeklib; $(MAKE) greeklib.a
	cd morphlib; $(MAKE) morphlib.a
