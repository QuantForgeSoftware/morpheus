#!/usr/bin/env python3
"""Parity oracle for the Unicode-native cruncher input path (Round 19.4).

Asserts that the C converter (``bin/gkconvert`` - the same ``gkunicode.c``
linked into ``cruncher -u``) produces exactly
``morpheus_toolkit.beta.to_beta(form).lower()`` for:

  * synthetic exhaustive: every single-codepoint key of the beta-code map and
    every Greek/combining codepoint in isolation, after a lowercase and after
    an uppercase letter; every NFC composition pair (NFD and NFC spellings);
    base x mark x mark combinations in both mark orders; apostrophe variants
    and word-final U+0313; N random Greek-like strings;
  * corpora (when the environment directories exist): every distinct form in
    MorphGNT (``MORPHGNT_DIR``), Apostolic Fathers (``AF_CORPUS_DIR``), AGLDT
    (``AGLDT_DIR``), PROIEL (``PROIEL_DIR``) and PapyGreek (``PAPYGREEK_DIR``).

Usage: .venv/bin/python scripts/unicode_parity.py [--synthetic-only]
       [--random N] [--binary PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import unicodedata as ud

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))
sys.path.insert(0, os.path.join(REPO, "scripts"))

from morpheus_toolkit.beta import to_beta  # noqa: E402

import beta_code  # noqa: E402

FOCUS_MARKS = [0x0300, 0x0301, 0x0304, 0x0306, 0x0308, 0x0313, 0x0314,
               0x0342, 0x0343, 0x0345]


def map_keys():
    path = os.path.join(os.path.dirname(beta_code.__file__),
                        "vendor", "beta-code-json", "unicode_to_beta_code.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    return sorted({ord(key) for key in data if len(key) == 1})


def synthetic_forms(random_count: int):
    forms = set()
    keys = map_keys()
    greek = list(range(0x0370, 0x0400)) + list(range(0x1F00, 0x2000)) \
        + list(range(0x0300, 0x0370))
    for cp in sorted(set(keys) | set(greek)):
        char = chr(cp)
        forms.add(char)
        forms.add("α" + char)
        forms.add("Α" + char)
        forms.add("λόγος" + char)
    starters = sorted(set(keys) | set(range(0x0370, 0x0400))
                      | set(range(0x1F00, 0x2000)))
    for starter in starters:
        for mark in range(0x0300, 0x0370):
            composed = ud.normalize("NFC", chr(starter) + chr(mark))
            if len(composed) == 1 and ord(composed) != starter:
                forms.add(chr(starter) + chr(mark))
                forms.add(composed)
    for base in "αΑεΕηΗιΙοΟυΥωΩ":
        for mark1 in FOCUS_MARKS:
            forms.add(base + chr(mark1))
            for mark2 in FOCUS_MARKS:
                forms.add(base + chr(mark1) + chr(mark2))
                forms.add(base + chr(mark2) + chr(mark1))
    for apostrophe in ("\u2019", "\u2018", "\u02bc", "\u00b4"):
        forms.add("ἀλλ" + apostrophe)
        forms.add(apostrophe)
        forms.add("λόγος" + apostrophe)
        forms.add("τοῦτ" + apostrophe)
    forms.add("\u0313")
    forms.add("δ\u0313")
    forms.add("λόγος\u0313")
    forms.add("α\u0313")
    rng = random.Random(19)
    alphabet = [chr(cp) for cp in sorted(set(keys) | set(range(0x0300, 0x0370)))]
    for _ in range(random_count):
        length = rng.randint(1, 8)
        forms.add("".join(rng.choice(alphabet) for _ in range(length)))
    return sorted(f for f in forms if f and not any(c.isspace() for c in f))


def corpus_forms():
    import benchmark as bench

    forms = set()
    morphgnt = os.environ.get("MORPHGNT_DIR", "")
    if morphgnt and os.path.isdir(morphgnt):
        rows = bench.read_morphgnt(morphgnt)
        forms |= {row.token for row in rows}
        print(f"  MorphGNT: {len(rows)} rows")
    af_dir = os.environ.get("AF_CORPUS_DIR", "")
    if af_dir and os.path.isdir(af_dir):
        import glob

        rows = bench.read_columnar(sorted(glob.glob(os.path.join(af_dir, "*.txt"))))
        forms |= {row.token for row in rows}
        print(f"  Apostolic Fathers: {len(rows)} rows")
    agldt = os.environ.get("AGLDT_DIR", "")
    if agldt and os.path.isdir(agldt):
        rows = bench.read_agldt(agldt)
        forms |= {row.token for row in rows}
        print(f"  AGLDT: {len(rows)} rows")
    proiel = os.environ.get("PROIEL_DIR", "")
    if proiel and os.path.exists(proiel):
        rows = bench.read_proiel(proiel)
        forms |= {row.token for row in rows}
        print(f"  PROIEL: {len(rows)} rows")
    pg = os.environ.get("PAPYGREEK_DIR", "")
    if pg and os.path.isdir(pg):
        rows = bench.read_papygreek(pg)
        forms |= {row.token for row in rows}
        print(f"  PapyGreek: {len(rows)} rows")
    return sorted(f for f in forms if f and not any(c.isspace() for c in f))


def c_convert(binary: str, forms, chunk: int = 4000):
    converted = []
    for start in range(0, len(forms), chunk):
        batch = forms[start:start + chunk]
        proc = subprocess.run([binary], input="\n".join(batch) + "\n",
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise SystemExit(f"gkconvert failed: {proc.stderr[:400]}")
        lines = proc.stdout.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        if len(lines) != len(batch):
            raise SystemExit(f"gkconvert line count mismatch in chunk at {start}")
        converted.extend(lines)
    return converted


def check(binary: str, label: str, forms):
    converted = c_convert(binary, forms)
    mismatches = []
    for form, got in zip(forms, converted):
        expected = to_beta(form).lower()
        if got == "\x1fFAIL":
            got = None
        if got != expected:
            mismatches.append((form, expected, got))
    print(f"{label}: {len(forms)} forms, {len(mismatches)} mismatches")
    for form, expected, got in mismatches[:40]:
        cps = " ".join(f"U+{ord(c):04X}" for c in form)
        print(f"  {form!r} [{cps}] python={expected!r} c={got!r}")
    return mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--synthetic-only", action="store_true")
    parser.add_argument("--random", type=int, default=3000)
    parser.add_argument("--binary", default=os.path.join(REPO, "bin", "gkconvert"))
    args = parser.parse_args()

    binary = args.binary
    if not os.path.exists(binary):
        fallback = os.path.join(REPO, "src", "anal", "gkconvert")
        if os.path.exists(fallback):
            binary = fallback
        else:
            raise SystemExit(f"gkconvert not found ({args.binary}); run scripts/build.sh")

    total = 0
    failures = 0
    forms = synthetic_forms(args.random)
    failures += len(check(binary, "synthetic", forms))
    total += len(forms)
    if not args.synthetic_only:
        forms = corpus_forms()
        if forms:
            failures += len(check(binary, "corpora", forms))
            total += len(forms)
        else:
            print("corpora: no corpus directories in the environment; skipped")
    print(f"TOTAL: {total} forms, {failures} mismatches")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
