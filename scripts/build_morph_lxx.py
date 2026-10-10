#!/usr/bin/env python3
"""
Produce a full Morpheus morphological analysis of the LXX reference corpus.

Reads every *.mlxx file in the corpus, runs Morpheus over each distinct form
(two-pass accent handling + frequency ranking), disambiguates with the Viterbi
POS-bigram tagger trained on this corpus (pos_bigram_lxx.json), and writes
re-annotated files to --out-dir in the same column layout:

    form  type  parse  lemma  [prefix]

The type column carries Morpheus's coarse POS; the parse column its full 8-char
parsing code (person/tense/voice/mood/case/number/gender/degree) — a superset of
the corpus's 5-char codes. Lemma convention is compound lemmas in canonical beta,
uppercased to match the corpus style (see todo.md, Round 3). Tokens Morpheus
cannot analyze fall back to the corpus's own annotation; fallbacks are counted
in the summary report.

Convention modes (both off = the natural Morpheus output of Round 3):
  --dictionary-forms  closed-set forms get the reference's dictionary-form
                      convention: articles -> ὁ (RA), personal pronouns ->
                      ἐγώ/σύ (RP), demonstratives -> family nominative (RD);
                      unambiguous forms are forced, homographic article/
                      relative pairs stay contextual. Where Morpheus offers the
                      target lemma under several same-POS feature readings
                      (masc/neut homographs), a per-spelling tie-break derived
                      from the reference's own accent notation decides.
  --base-lemmas       compound verbs lemmatize to the base verb (preverb stays
                      in the prefix column); a preverb is stripped only when
                      the remainder is an attested verb.

Usage:
  scripts/build_morph_lxx.py --corpus-dir /path/to/lxx-corpus \
      [--out-dir tmp/lxx/morph-lxx] [--model .../pos_bigram_lxx.json] \
      [--frequencies .../lemma_frequencies_lxx.json]
      [--dictionary-forms] [--base-lemmas]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import re
import sys
import unicodedata

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "python"))

from morpheus_toolkit.api import Morpheus  # noqa: E402
from morpheus_toolkit.beta import from_beta, normalize_lemma, to_beta  # noqa: E402
from morpheus_toolkit.morphgnt import parsing_code  # noqa: E402
from morpheus_toolkit.ranking import Ranker  # noqa: E402
from morpheus_toolkit.tagger import PosTagger  # noqa: E402

PARSE_RE = re.compile(r"[A-Z0-9]+$")
LETTER_RE = re.compile(r"[A-Za-z]")

# --- Convention layer (--dictionary-forms) ----------------------------------
#
# Closed sets of surface forms with a single correct reading. The reference
# corpus's dictionary-form convention per class (see its coding sheet):
#   RA article -> ὁ ;  RP personal pronoun -> nominative ἐγώ/σύ ;
#   RD demonstrative -> family nominative (αὐτός, οὗτος, ἐκεῖνος, ὅδε).
#
# Keys are canonical beta (the to_beta∘from_beta round-trip of the corpus
# form — same canon() as below); values are (normalized lemma target,
# reference type code). Derived from the corpus + Morpheus candidate structure
# by tmp/lxx/gen_tables.py: a form is listed only where Morpheus offers a
# candidate with exactly that lemma. Coverage: RA 88,424/88,429 tokens,
# RP 26,628/26,934, RD 34,704/35,834.
#
# AMBIGUOUS_ARTICLES also has a relative-pronoun (RR) candidate — the unaccented
# article and relative are genuinely homographic there, so those forms get a
# boosted score instead of being forced; context still decides.
ARTICLE_FORMS = {
    'ai(': ('ὁ', 'RA'),
    'h(': ('ὁ', 'RA'),
    'o(': ('ὁ', 'RA'),
    'oi(': ('ὁ', 'RA'),
    'ta/': ('ὁ', 'RA'),
    'ta/s': ('ὁ', 'RA'),
    'ta\\': ('ὁ', 'RA'),
    'ta\\s': ('ὁ', 'RA'),
    'tai=s': ('ὁ', 'RA'),
    'th/n': ('ὁ', 'RA'),
    'th=s': ('ὁ', 'RA'),
    'th=|': ('ὁ', 'RA'),
    'th\\n': ('ὁ', 'RA'),
    'to/': ('ὁ', 'RA'),
    'to/n': ('ὁ', 'RA'),
    'to\\': ('ὁ', 'RA'),
    'to\\n': ('ὁ', 'RA'),
    'toi=s': ('ὁ', 'RA'),
    'tou/s': ('ὁ', 'RA'),
    'tou=': ('ὁ', 'RA'),
    'tou\\s': ('ὁ', 'RA'),
    'tw=n': ('ὁ', 'RA'),
    'tw=|': ('ὁ', 'RA'),
}
AMBIGUOUS_ARTICLES = {'ai(', 'h(', 'o(', 'oi('}
PERSONAL_PRONOUNS = {
    'e)/gwge': ('ἐγώ', 'RP'),
    'e)gw/': ('ἐγώ', 'RP'),
    'e)gw\\': ('ἐγώ', 'RP'),
    'e)me/': ('ἐγώ', 'RP'),
    'e)me\\': ('ἐγώ', 'RP'),
    'e)moi/': ('ἐγώ', 'RP'),
    'e)moi\\': ('ἐγώ', 'RP'),
    'e)mou=': ('ἐγώ', 'RP'),
    'h(ma=s': ('ἐγώ', 'RP'),
    'h(mei=s': ('ἐγώ', 'RP'),
    'h(mi=n': ('ἐγώ', 'RP'),
    'h(mw=n': ('ἐγώ', 'RP'),
    'me': ('ἐγώ', 'RP'),
    'me/': ('ἐγώ', 'RP'),
    'moi': ('ἐγώ', 'RP'),
    'moi/': ('ἐγώ', 'RP'),
    'mou': ('ἐγώ', 'RP'),
    'mou/': ('ἐγώ', 'RP'),
    'mou=': ('ἐγώ', 'RP'),
    'se': ('σύ', 'RP'),
    'se/': ('σύ', 'RP'),
    'se\\': ('σύ', 'RP'),
    'soi': ('σύ', 'RP'),
    'soi/': ('σύ', 'RP'),
    'soi\\': ('σύ', 'RP'),
    'sou': ('σύ', 'RP'),
    'sou/': ('σύ', 'RP'),
    'sou=': ('σύ', 'RP'),
    'su/': ('σύ', 'RP'),
    'su\\': ('σύ', 'RP'),
    'u(ma=s': ('σύ', 'RP'),
    'u(mei=s': ('σύ', 'RP'),
    'u(mi=n': ('σύ', 'RP'),
    'u(mw=n': ('σύ', 'RP'),
}
DEMONSTRATIVES = {
    'au(/th': ('οὗτος', 'RD'),
    'au(=tai': ('οὗτος', 'RD'),
    'au(=tai/': ('οὗτος', 'RD'),
    'au)ta/': ('αὐτός', 'RD'),
    'au)ta/s': ('αὐτός', 'RD'),
    'au)ta\\': ('αὐτός', 'RD'),
    'au)ta\\s': ('αὐτός', 'RD'),
    'au)tai/': ('αὐτός', 'RD'),
    'au)tai=s': ('αὐτός', 'RD'),
    'au)tai\\': ('αὐτός', 'RD'),
    'au)th/': ('αὐτός', 'RD'),
    'au)th/n': ('αὐτός', 'RD'),
    'au)th=s': ('αὐτός', 'RD'),
    'au)th=|': ('αὐτός', 'RD'),
    'au)th\\': ('αὐτός', 'RD'),
    'au)th\\n': ('αὐτός', 'RD'),
    'au)to/': ('αὐτός', 'RD'),
    'au)to/n': ('αὐτός', 'RD'),
    'au)to/s': ('αὐτός', 'RD'),
    'au)to\\': ('αὐτός', 'RD'),
    'au)to\\n': ('αὐτός', 'RD'),
    'au)to\\s': ('αὐτός', 'RD'),
    'au)toi/': ('αὐτός', 'RD'),
    'au)toi=s': ('αὐτός', 'RD'),
    'au)toi\\': ('αὐτός', 'RD'),
    'au)tou/': ('αὐτός', 'RD'),
    'au)tou/s': ('αὐτός', 'RD'),
    'au)tou=': ('αὐτός', 'RD'),
    'au)tou\\s': ('αὐτός', 'RD'),
    'au)tw=n': ('αὐτός', 'RD'),
    'au)tw=|': ('αὐτός', 'RD'),
    'e)kei/nais': ('ἐκεῖνος', 'RD'),
    'e)kei/nas': ('ἐκεῖνος', 'RD'),
    'e)kei/nh': ('ἐκεῖνος', 'RD'),
    'e)kei/nhn': ('ἐκεῖνος', 'RD'),
    'e)kei/nhs': ('ἐκεῖνος', 'RD'),
    'e)kei/nh|': ('ἐκεῖνος', 'RD'),
    'e)kei/nois': ('ἐκεῖνος', 'RD'),
    'e)kei/nou': ('ἐκεῖνος', 'RD'),
    'e)kei/nous': ('ἐκεῖνος', 'RD'),
    'e)kei/nwn': ('ἐκεῖνος', 'RD'),
    'e)kei/nw|': ('ἐκεῖνος', 'RD'),
    'e)kei=na': ('ἐκεῖνος', 'RD'),
    'e)kei=nai': ('ἐκεῖνος', 'RD'),
    'e)kei=no': ('ἐκεῖνος', 'RD'),
    'e)kei=noi': ('ἐκεῖνος', 'RD'),
    'e)kei=noi/': ('ἐκεῖνος', 'RD'),
    'e)kei=non': ('ἐκεῖνος', 'RD'),
    'e)kei=nos': ('ἐκεῖνος', 'RD'),
    'h(/de': ('ὅδε', 'RD'),
    'o(/de': ('ὅδε', 'RD'),
    'oi(/de': ('ὅδε', 'RD'),
    'ou(=to/s': ('οὗτος', 'RD'),
    'ou(=toi': ('οὗτος', 'RD'),
    'ou(=toi/': ('οὗτος', 'RD'),
    'ou(=tos': ('οὗτος', 'RD'),
    'ta/de': ('ὅδε', 'RD'),
    'ta/sde': ('ὅδε', 'RD'),
    'tau/tais': ('οὗτος', 'RD'),
    'tau/tas': ('οὗτος', 'RD'),
    'tau/thn': ('οὗτος', 'RD'),
    'tau/ths': ('οὗτος', 'RD'),
    'tau/th|': ('οὗτος', 'RD'),
    "tau=q'": ('οὗτος', 'RD'),
    "tau=t'": ('οὗτος', 'RD'),
    'tau=ta': ('οὗτος', 'RD'),
    'tau=ta/': ('οὗτος', 'RD'),
    'th/nde': ('ὅδε', 'RD'),
    'th=sde': ('ὅδε', 'RD'),
    'th=|de': ('ὅδε', 'RD'),
    'to/de': ('ὅδε', 'RD'),
    'to/nde': ('ὅδε', 'RD'),
    'tou/sde': ('ὅδε', 'RD'),
    'tou/tois': ('οὗτος', 'RD'),
    'tou/tou': ('οὗτος', 'RD'),
}

# Tied-candidate feature preference under --dictionary-forms. The Viterbi tagger
# keeps one candidate per coarse POS (first on score ties), so when Morpheus
# offers a forced form's lemma in several same-POS feature readings the choice
# is arbitrary — and usually wrong: e.g. AU)TW=N comes out GPN while 92% of the
# reference's tokens are GPM. For the forms below the reference's own accent
# notation correlates strongly with the reading (AU)TOU= is 97% GSM, AU)TOU\S is
# ~100% APM), so we break the tie toward that majority. Derived by
# tmp/lxx/gen_tiebreak.py; entries require >=10 tokens and a >=90% gold-feature
# majority per spelling (weaker cases like τὰ stay contextual).
TIE_BREAK = {
    'au)toi=s': '----DPM-',   # 1510 tok, gold DPM 95%
    'au)tou=': '----GSM-',    # 9176 tok, gold GSM 97%
    'au)tw=n': '----GPM-',    # 5117 tok, gold GPM 92%
    'au)tw=|': '----DSM-',    # 2187 tok, gold DSM 97%
    'e)kei/nou': '----GSM-',  # 42 tok, gold GSM 93%
    'e)kei/nw|': '----DSM-',  # 99 tok, gold DSM 98%
    'ta/': '----APN-',        # 11 tok, gold APN 91%
    'ta/de': '----APN-',      # 414 tok, gold APN 95%
    'tau/tas': '----APF-',    # 34 tok, gold APF 100%
}

# --- Base-lemma mode (--base-lemmas) -----------------------------------------
#
# The reference corpus lemmatizes compound verbs to the base verb and records
# the preverb in its prefix column (which this driver already preserves). With
# --base-lemmas we do the same: strip a leading preverb from a verb lemma when
# the remainder is itself an attested verb (the guard — it prevents stripping
# prefixes off words that merely start with a preverb-like string).
PREVERBS = ["ανα", "αντι", "απο", "αφ", "δια", "εκ", "εξ", "εν", "υπερ",
            "κατα", "παρα", "περι", "προσ", "συν", "υπο"]  # accents stripped

# Contracted/assimilated compounds lose the preverb's final vowel (δια+ἔρχομαι →
# διέρχομαι), so head-stripping misses them. Tail-matching recovers them, but a
# simplex can end in another verb's string (χωρίζω ~ ρίζω) — so a tail is accepted
# only when what precedes it is an attested preverb remnant. The set below is the
# remnants actually observed in the LXX (tmp/lxx/count_compounds.py) plus the full
# preverbs; hyphenated entries are Morpheus's explicit compound notation.
PREVERB_REMNANTS = {
    "επι", "κατ", "εισ", "αν", "απ", "παρ", "επ", "καθ", "δι", "εμ", "προ",
    "εξαπο", "υπ", "συμ", "παρεμ", "εγκατα", "συγ", "μετα", "συλ", "εκ-",
    "εν-", "ανταπο", "εφ", "κατα-", "διαρ", "ανθ", "εγ", "απορ", "συ",
    "προκατα", "συν-", "αποκαθ", "μεθ", "διαν", "υφ", "μετ", "απο-",
    "ανα-", "εξαν", "επι-",
} | set(PREVERBS)


def deacc(s: str) -> str:
    """Lowercase and strip all diacritics (incl. breathings)."""
    return "".join(ch for ch in unicodedata.normalize("NFD", s.lower())
                   if not unicodedata.combining(ch))


def canon(form_beta: str) -> str:
    """Corpus beta code -> canonical lowercase beta via a Unicode round-trip."""
    return to_beta(from_beta(form_beta)) or form_beta.lower()


def is_token_line(line: str) -> bool:
    fields = line.split()
    return len(fields) >= 3 and bool(LETTER_RE.search(fields[0]))


def parse_fields(line: str):
    """form, type, parse, lemma, prefix (the corpus's column layout)."""
    fields = line.split()
    form_b, typ = fields[0], fields[1]
    if len(fields) >= 4 and PARSE_RE.fullmatch(fields[2]):
        parse_c, lemma_b = fields[2], fields[3]
        prefix = fields[4] if len(fields) > 4 else ""
    else:
        parse_c, lemma_b = "", fields[2]
        prefix = fields[3] if len(fields) > 3 else ""
    return form_b, typ, parse_c, lemma_b, prefix


def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default=os.environ.get("LXX_CORPUS_DIR", ""))
    parser.add_argument(
        "--out-dir",
        default=os.path.join(REPO, "tmp", "lxx", "morph-lxx"),
    )
    parser.add_argument(
        "--model",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "pos_bigram_lxx.json"),
    )
    parser.add_argument(
        "--frequencies",
        default=os.path.join(REPO, "python", "morpheus_toolkit", "data", "lemma_frequencies_lxx.json"),
    )
    parser.add_argument(
        "--dictionary-forms",
        action="store_true",
        help="emit the reference's dictionary-form convention for closed-set forms "
             "(articles -> ὁ/RA, personal pronouns -> ἐγώ|σύ/RP, demonstratives -> family "
             "nominative/RD) and force those readings where unambiguous",
    )
    parser.add_argument(
        "--base-lemmas",
        action="store_true",
        help="lemmatize compound verbs to the base verb (the preverb stays in the prefix column)",
    )
    args = parser.parse_args()
    if not args.corpus_dir or not os.path.isdir(args.corpus_dir):
        parser.error("give --corpus-dir (or set LXX_CORPUS_DIR) pointing at the LXX reference corpus")

    files = sorted(glob.glob(os.path.join(args.corpus_dir, "*.mlxx")))
    if not files:
        parser.error(f"no *.mlxx files under {args.corpus_dir}")

    # Pass 1: read every file; collect distinct canonical forms and raw lines.
    per_file_lines = {}
    distinct = set()
    total_tokens = 0
    for path in files:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = [line.rstrip("\n") for line in handle]
        per_file_lines[path] = lines
        for line in lines:
            if is_token_line(line):
                total_tokens += 1
                distinct.add(canon(parse_fields(line)[0]))

    print(f"files={len(files)} tokens={total_tokens} distinct_forms={len(distinct)}", flush=True)

    # Pass 2: analyze every distinct form (two-pass accents + ranked candidates).
    freq_data = load_json(args.frequencies)

    # --base-lemmas guard: a preverb is stripped only when the remainder is an
    # attested verb (any V* type in the joint table).
    known_verbs = {}
    verbs_by_len = []
    base_memo = {}
    if args.base_lemmas:
        for lemma, row in freq_data.get("by_pos", {}).items():
            if any(pos.startswith("V") for pos in row):
                known_verbs[deacc(lemma)] = lemma
        verbs_by_len = sorted(known_verbs, key=len, reverse=True)

    def base_lemma_of(analysis):
        """Base verb for a compound-verb analysis (memoized), or None."""
        d = deacc(analysis.lemma)
        if d in base_memo:
            return base_memo[d]
        base = None
        # 1) intact preverb at the head
        for pv in PREVERBS:
            if d.startswith(pv) and len(d) > len(pv):
                rest = d[len(pv):]
                for cand in (rest, rest.replace("ει", "ε"), rest.replace("ου", "ο")):
                    base = known_verbs.get(cand)
                    if base is not None:
                        break
                if base is not None:
                    break
        # 2) contracted/assimilated: longest tail that is an attested verb AND is
        #    preceded by a preverb remnant (guards against simplexes like χωρίζω)
        if base is None and len(d) >= 6:
            for v in verbs_by_len:
                if len(v) < 4 or len(d) <= len(v) + 1:
                    continue
                if d.endswith(v) and d[:-len(v)] in PREVERB_REMNANTS:
                    base = known_verbs[v]
                    break
        base_memo[d] = base
        return base

    morpheus = Morpheus(ignore_accents=True)
    morpheus.ranker = Ranker(
        freq_data.get("frequencies", freq_data),
        joint_frequencies=freq_data.get("by_pos"),
    )
    candidates: dict[str, list] = {}
    forms = sorted(distinct)
    BATCH = 2000
    for i in range(0, len(forms), BATCH):
        chunk = forms[i : i + BATCH]
        for result in morpheus.analyze_beta(chunk):
            if result.analyses:
                candidates[result.beta] = list(result.analyses)
        print(f"  analyzed {min(i + BATCH, len(forms))}/{len(forms)}", flush=True)

    tagger = PosTagger(load_json(args.model))

    # Pass 3: per file — Viterbi-tag each contiguous token run, emit output.
    os.makedirs(args.out_dir, exist_ok=True)
    total_analyzed = 0
    total_fallback = 0
    fallback_by_type: collections.Counter = collections.Counter()
    book_stats = {}

    for path in files:
        book = os.path.basename(path)
        out_lines = []
        fallback_lines = []  # 1-based output line numbers using the corpus annotation
        run_items = []  # (raw_line, candidates)

        def convention_target(form_b):
            """(lemma, type) for closed-set forms under --dictionary-forms, else None."""
            k = canon(form_b)
            for table in (ARTICLE_FORMS, PERSONAL_PRONOUNS, DEMONSTRATIVES):
                if k in table:
                    return table[k]
            return None

        def emit_run():
            nonlocal total_analyzed, total_fallback
            if not run_items:
                return
            tag_inputs = [cands for _, cands in run_items]
            if args.dictionary_forms:
                # Closed-set forms have one correct reading: force it (the Viterbi
                # pass then has no choice). Genuinely ambiguous article forms —
                # homographic with the relative pronoun — are left to context.
                new_inputs = []
                for (raw, cands) in run_items:
                    target = convention_target(parse_fields(raw)[0])
                    k = canon(parse_fields(raw)[0])
                    if target is None or not cands or k in AMBIGUOUS_ARTICLES:
                        new_inputs.append(cands)
                        continue
                    lemma_t, typ = target
                    hits = [a for a in cands
                            if normalize_lemma(a.lemma) == lemma_t
                            and (typ == "RD" or a.pos == typ)]
                    # Keep every candidate with the target reading so Viterbi can
                    # still use context to choose among them (it matters when
                    # Morpheus offers the lemma under several POSes; same-POS
                    # candidates collapse in the tagger anyway). No hit -> leave
                    # the form fully contextual.
                    if len(hits) > 1 and k in TIE_BREAK:
                        pref = TIE_BREAK[k]
                        # Stable sort: preferred feature reading first, so the
                        # tagger's same-POS tie (first candidate wins) resolves
                        # toward the reference majority for this spelling.
                        hits.sort(key=lambda a: parsing_code(a) != pref)
                    new_inputs.append(hits if hits else cands)
                tag_inputs = new_inputs
            chosen = tagger.tag(tag_inputs)
            for (raw, _cands), analysis in zip(run_items, chosen):
                form_b, typ, parse_c, lemma_b, prefix = parse_fields(raw)
                if analysis is None or analysis.proposed:
                    out_lines.append(raw)  # fallback: corpus's own annotation
                    fallback_lines.append(len(out_lines))
                    total_fallback += 1
                    fallback_by_type[typ] += 1
                    continue
                # Type column: the reference scheme's code when the chosen reading
                # is a closed-set form (Morpheus has no demonstrative POS).
                out_typ = analysis.pos
                if args.dictionary_forms:
                    target = convention_target(form_b)
                    if target and normalize_lemma(analysis.lemma) == target[0]:
                        out_typ = target[1]
                # Lemma column: base verb for compounds under --base-lemmas.
                lemma_out = analysis.lemma_beta.upper()
                if args.base_lemmas and analysis.pos.startswith("V"):
                    base = base_lemma_of(analysis)
                    if base is not None:
                        lemma_out = to_beta(base).upper() or lemma_out
                fields = [form_b, out_typ, parsing_code(analysis), lemma_out]
                if prefix:
                    fields.append(prefix)
                out_lines.append("  ".join(fields))
                total_analyzed += 1
            run_items.clear()

        for line in per_file_lines[path]:
            if not line.strip() or not is_token_line(line):
                emit_run()
                out_lines.append(line)
                continue
            form_b = parse_fields(line)[0]
            run_items.append((line, candidates.get(canon(form_b), [])))
        emit_run()

        with open(os.path.join(args.out_dir, book), "w", encoding="utf-8") as handle:
            handle.write("\n".join(out_lines) + "\n")
        if fallback_lines:
            with open(os.path.join(args.out_dir, book + ".fb"), "w", encoding="utf-8") as handle:
                handle.write("\n".join(str(n) for n in fallback_lines) + "\n")
        book_tokens = sum(1 for line in per_file_lines[path] if is_token_line(line))
        book_stats[book] = book_tokens

    # Summary report.
    conventions = []
    if args.dictionary_forms:
        conventions.append("dictionary-forms")
    if args.base_lemmas:
        conventions.append("base-lemmas")
    summary = [
        "Morpheus LXX annotation — summary",
        "corpus: LXX reference corpus (*.mlxx)",
        f"conventions: {', '.join(conventions) or 'none (natural Morpheus output)'}",
        f"files={len(files)} tokens={total_tokens} distinct_forms={len(distinct)}",
        f"analyzed_by_morpheus={total_analyzed} ({100 * total_analyzed / max(total_tokens, 1):.2f}%)",
        f"fallback_to_corpus={total_fallback} ({100 * total_fallback / max(total_tokens, 1):.2f}%)",
        "",
        "fallbacks by corpus type:",
    ]
    for typ, count in fallback_by_type.most_common(15):
        summary.append(f"  {typ:6s} {count}")
    summary += ["", "tokens per book (all tokens; see output files for annotations):"]
    for book, count in sorted(book_stats.items()):
        summary.append(f"  {book:24s} {count}")

    out_summary = os.path.join(args.out_dir, "summary.txt")
    with open(out_summary, "w", encoding="utf-8") as handle:
        handle.write("\n".join(summary) + "\n")
    print(f"\nwrote {len(files)} files to {args.out_dir}; summary at {out_summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
