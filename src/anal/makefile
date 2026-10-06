# C build for the Morpheus analyzer (cruncher + supporting tools).
#
# The C# port of this module lives in makefile-cs (built separately with `make -f
# makefile-cs`, or `make cs` from the repo root) so the default `make` works
# without a C# toolchain.

LEXLIB = -lfl

INCLUDE=../includes
CFLAGS+= -O2 -I${INCLUDE}
RM=rm
CC=cc
CC=gcc
LEX=flex

ENDLIB=../gkends/gkends.a
GREEKLIB=../greeklib/greeklib.a
MORPHLIB=../morphlib/morphlib.a
GENERLIB=../gener/gener.a
DICTLIB=../gkdict/gkdict.a
ANALLIB=anal.a
LIBS=${GENERLIB} ${ENDLIB} ${DICTLIB} ${MORPHLIB} ${GREEKLIB}

LSJDIR=/local/text/lsj
ANALOBJ= checkcrasis.o \
checkdict.o \
checkgenwds.o \
checkhalf1.o \
checkindecl.o \
checkirreg.o \
checknom.o \
checkpreverb.o \
checkstem.o \
checkstring.o \
checkverb.o \
checkword.o \
dictstems.o \
prntanal.o \
prvb.o

${ANALLIB}: ${ANALOBJ}
	ar rv ${ANALLIB} ${ANALOBJ}
	ranlib ${ANALLIB}

ALL=cruncher pname findbase deverbal ${ANALLIB}

all: ${ALL}

install: all
	cp ${ALL} ../../bin

lcnt: lcnt.o ${ANALLIB} ${LIBS}
	${CC} -o lcnt lcnt.o ../gener/genwd.o ${ANALLIB} ${LIBS}

cruncher: stdiomorph.o ${ANALLIB} ${LIBS}
	${CC} -o cruncher stdiomorph.o ../gener/genwd.o ${ANALLIB} ${LIBS}

pname: propname.o ${ANALOBJ} ${LIBS}
	${CC} -o pname propname.o ${ANALOBJ} ${LIBS}

findbase: findbase.o ${ANALOBJ} ${LIBS}
	${CC} -o findbase findbase.o ${ANALOBJ} ${LIBS}

deverbal: deverb.o ${ANALOBJ} ${LIBS}
	${CC} -o deverbal deverb.o ${ANALOBJ} ${LIBS}

clean:
	rm -f cruncher pname findbase deverbal lcnt *.o ${ANALLIB}

proclems: proclems.o
	${CC} -o proclems proclems.o
