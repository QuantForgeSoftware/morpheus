"""Parity tests for the Unicode-native cruncher input path (Round 19.4).

The C converter (``src/anal/gkunicode.c``, built as ``bin/gkconvert`` and
linked into ``cruncher -u``) must produce exactly
``morpheus_toolkit.beta.to_beta(form).lower()``. The exhaustive synthetic
oracle lives in ``scripts/unicode_parity.py``; these tests run it as a
subprocess and add direct behavior checks. Skipped when the binary is not
built (run ``scripts/build.sh``).
"""
import os
import subprocess
import sys

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GKCONVERT = os.path.join(REPO, "bin", "gkconvert")

pytestmark = pytest.mark.skipif(
    not os.path.exists(GKCONVERT),
    reason="bin/gkconvert not built (scripts/build.sh)",
)


def convert(forms):
    proc = subprocess.run(
        [GKCONVERT], input="\n".join(forms) + "\n", capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.split("\n")
    assert lines[-1] == ""
    return lines[:-1]


def test_synthetic_oracle_passes():
    proc = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "unicode_parity.py"),
         "--synthetic-only"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    assert "0 mismatches" in proc.stdout


def test_direct_conversions():
    # Reference values are the Python converter's (to_beta + lower).
    forms = [
        "\u1f04\u03bd\u03b8\u03c1\u03c9\u03c0\u03bf\u03c2",  # ἄνθρωπος
        "\u1f0c\u03bd\u03b8\u03c1\u03c9\u03c0\u03bf\u03c2",  # Ἄνθρωπος
        "\u03bb\u03cc\u03b3\u1ff3",                          # λόγῳ
        "\u1f00\u03bb\u03bb\u2019",                          # ἀλλ’ (curly)
        "\u1f00\u03bb\u03bb'",                               # ἀλλ' (ASCII)
        "\u03b4\u0313",                                      # δ + elision comma
        "\u1fcd",                                            # ῍ (spacing psili+grave)
    ]
    assert convert(forms) == [
        "a)/nqrwpos",
        "*)/anqrwpos",
        "lo/gw|",
        "a)ll'",
        "a)ll'",
        "d'",
        "\u1fcd",
    ]


def test_uppercase_and_unmapped_pass_through():
    # ΑΝΘΡΩΠΟΣ: each capital maps to *x; ASCII tolower is a no-op on beta.
    assert convert(["\u0391\u039d\u0398\u03a1\u03a9\u03a0\u039f\u03a3"]) == [
        "*a*n*q*r*w*p*o*s"
    ]
    # Unmapped codepoints pass through and are lowercased (Greek lowercase).
    assert convert(["\u03dc"]) == ["\u03dd"]  # Ϝ -> ϝ


def test_cruncher_unicode_flag_matches_beta_path():
    """cruncher -u on Unicode input == cruncher on the beta conversion."""
    from morpheus_toolkit.beta import to_beta

    words = ["\u1f04\u03bd\u03b8\u03c1\u03c9\u03c0\u03bf\u03c2",
             "\u03bb\u03cc\u03b3\u03bf\u03c2",
             "\u1f00\u03bb\u03bb\u2019",
             "\u03b4\u03b9\u03b4\u03ac\u03c3\u03ba\u03b5\u03b9\u03bd"]
    stemlib = os.path.join(REPO, "stemlib")
    env = dict(os.environ, MORPHLIB=stemlib)
    cruncher = os.path.join(REPO, "bin", "cruncher")

    def run(flag, forms):
        proc = subprocess.run(
            [cruncher, "-S", flag, "-q"] if flag else [cruncher, "-S", "-q"],
            input="\n".join(forms) + "\n", capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, proc.stderr
        return proc.stdout

    beta_forms = [to_beta(word).lower() for word in words]
    assert run("-u", words) == run("", beta_forms)
