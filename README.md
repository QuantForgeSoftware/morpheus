# Morpheus

Morpheus is a morphological parsing tool originally written as part of the Perseus Project.
It takes Ancient Greek or Latin text as input and then lemmatizes the text and performs a morphological analysis.
For other versions of this codebase, see [PerseusDL/morpheus](https://github.com/PerseusDL/morpheus)
and [alpheios-project/morpheus](https://github.com/alpheios-project/morpheus).

## Building

### Docker

#### From Docker Hub

```bash
docker pull perseidsproject/morpheus

docker run -it perseidsproject/morpheus /bin/bash
```

(See project on [Docker Hub](https://hub.docker.com/r/perseidsproject/morpheus/).)

#### Building container

```
docker build -t morpheus .

docker run -it morpheus /bin/bash
```

### macOS

Requirements:

- Xcode command line tools

```bash
cd src/
make clean
CFLAGS='-std=gnu89 -Wno-return-type -Wno-implicit-function-declaration' make LOADLIBES='-ll'
make install
```

(Tested on Apple M1, macOS Ventura 13.1, Apple clang version 14.0.0.)

### Linux

Requirements:

- `make`
- `gcc`
- `flex`

```bash
cd src/
make clean
CFLAGS='-std=gnu89 -fcommon' make
make install
```

(Tested on Ubuntu 22.04)

### Stemlibs

The stemlibs are checked in and included in the repository.
To rebuild the stemlibs, run the following commands (with the same
`CFLAGS` used when compiling the binaries):

```
cd stemlib/Greek/
make clean
PATH="$PATH:../../bin" MORPHLIB='..' make
PATH="$PATH:../../bin" MORPHLIB='..' make

cd ../Latin/
make clean
PATH="$PATH:../../bin" MORPHLIB='..' make
PATH="$PATH:../../bin" MORPHLIB='..' make
```

## Usage

Example usage:

```
$ echo 'a)/nqrwpos' | MORPHLIB=stemlib bin/cruncher -S
> a)/nqrwpos
> <NL>N a)/nqrwpos  masc nom sg			os_ou</NL>
```

```
$ echo 'a)nqrwpos' | MORPHLIB=stemlib bin/cruncher -S -n
> a)nqrwpos
> <NL>N a)/nqrwpos,a)/nqrwpos  masc nom sg			os_ou</NL>
```

```
$ echo 'cactus' | MORPHLIB=stemlib bin/cruncher -S -L
> cactus
> <NL>N cactus  masc nom sg			us_i</NL>
```

### Command line options

| Option | Description |
| - | - |
| -L | Set language to Latin |
| -S | Turn off Strict case. For Greek, this allows words with an initial capital to be recognized. For languages in the Roman alphabet, allows words with initial capital or in all capitals. |
| -n | Ignore accents.|
| -d | Database format. This switch changes the output from "Perseus format" to "database format." Output appears in a series of tagged fields. |
| -e | Ending index. Instead of showing the analysis in readable form, this switch gives the indices of the tense, mood, case, number, and so on (as appropriate) in the internal tables. |
| -k | Keep beta-code. When "Perseus format" is enabled (the default), this switch does nothing. When "Perseus format" is off, output (Greek as well as Latin) is converted to the old Greek Keys encoding. This switch disables that conversion so that Greek output stays in beta-code. |
| -l | Show lemma. When this switch is set, instead of printing the entire analysis, cruncher will only show the lemma or headword from which the given form is made. |
| -P | Turn off Perseus format. Output will be in the form `$feminam& is^M &from$ femina^M $fe\_minam^M [&stem $fe\_min-& ]^M & a\_ae fem acc sg^M`. Note the returns, without line feeds, between the fields. |
| -V | Analyze verbs only. |
| -q | Echo a `:form <token>` delimiter for every input, including words with no analysis, so batch output stays positionally alignable. |

## Python toolkit

`python/` contains **morpheus-toolkit**, a Unicode/JSON layer over the analyzer:
UTF-8 in, structured analyses (lemma, fine-grained POS, features) out, with
frequency-based ranking of the candidate readings. See
[`python/README.md`](python/README.md) for install, CLI, the measured effect
of ranking (top-1 lemma accuracy +~6 points on the SBLGNT and the Apostolic
Fathers), and LXX annotation support. Build the analyzer with `scripts/build.sh`
first.

## Septuagint (LXX)

The Greek stemlibs include a generated `stemsrc/nom.lxx` derived from a reference
morphological analysis of the Septuagint: ~4,500 proper names Morpheus lacked
(Ἰσραήλ, Δαυίδ, Ἱερουσαλήμ, …) plus a curated set of common words (σάββατον,
ἀμνός, τρυβλίον, …). The verb sources gained base entries (εὐλογέω, ἐγγίζω) and
explicit inflection lines for forms the generative paradigms miss. Against that
reference corpus Morpheus now analyzes **99.81%** of all 623,685 LXX tokens;
`todo.md` (Rounds 1–3) has the full story and metrics.

Regenerate the entries from a local checkout of the reference corpus:

```bash
scripts/build_lxx_stemlib.py --corpus-dir /path/to/lxx-corpus   # or LXX_CORPUS_DIR
bash scripts/build-stemlib.sh                                   # rebuild the stemlibs
```

The toolkit can also produce a full, disambiguated annotation of the whole corpus in
the reference format — see [`python/README.md`](python/README.md#the-septuagint-lxx).

## Tests

Requirements:

- `ruby` (~3.0)

`./test/test.rb`
