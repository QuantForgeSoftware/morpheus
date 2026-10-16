/* Unicode-native input path for cruncher (-u): UTF-8 Greek -> lowercase beta.
 *
 * Mirrors morpheus_toolkit.beta.to_beta + runner._normalize_beta exactly:
 *
 *   apostrophe translation (U+2019/2018/02BC/00B4 -> '),
 *   word-final U+0313 -> ',
 *   NFC (canonical ordering + composition),
 *   per-codepoint beta map (unmapped codepoints pass through),
 *   lowercase (ASCII beta letters + Unicode lowercase for pass-through
 *   Greek codepoints).
 *
 * Tables: gkunicode_tab.c, generated from the beta-code package's map by
 * scripts/gen_gkunicode_tables.py. Parity with the Python converter is
 * asserted by scripts/unicode_parity.py over the five corpora and an
 * exhaustive synthetic set (python/tests/test_unicode_c_path.py).
 */
#include <ctype.h>
#include <stddef.h>
#include <string.h>

#include "gkunicode_tab.h"

#define GKUNI_MAX 1024  /* max codepoints per token; longer input fails */

/* Decode one UTF-8 codepoint; returns bytes consumed or -1 on bad input. */
static int gkuni_utf8_decode(const unsigned char *s, int *cp) {
  unsigned char c = s[0];

  if (c < 0x80) {
    *cp = c;
    return 1;
  }
  if ((c & 0xE0) == 0xC0) {
    if ((s[1] & 0xC0) != 0x80) return -1;
    *cp = ((c & 0x1F) << 6) | (s[1] & 0x3F);
    return 2;
  }
  if ((c & 0xF0) == 0xE0) {
    if ((s[1] & 0xC0) != 0x80 || (s[2] & 0xC0) != 0x80) return -1;
    *cp = ((c & 0x0F) << 12) | ((s[1] & 0x3F) << 6) | (s[2] & 0x3F);
    return 3;
  }
  if ((c & 0xF8) == 0xF0) {
    if ((s[1] & 0xC0) != 0x80 || (s[2] & 0xC0) != 0x80
        || (s[3] & 0xC0) != 0x80) return -1;
    *cp = ((c & 0x07) << 18) | ((s[1] & 0x3F) << 12)
        | ((s[2] & 0x3F) << 6) | (s[3] & 0x3F);
    return 4;
  }
  return -1;
}

/* Encode one codepoint as UTF-8; returns bytes written (1-4). */
static int gkuni_utf8_encode(int cp, char *out) {
  if (cp < 0x80) {
    out[0] = (char) cp;
    return 1;
  }
  if (cp < 0x800) {
    out[0] = (char) (0xC0 | (cp >> 6));
    out[1] = (char) (0x80 | (cp & 0x3F));
    return 2;
  }
  if (cp < 0x10000) {
    out[0] = (char) (0xE0 | (cp >> 12));
    out[1] = (char) (0x80 | ((cp >> 6) & 0x3F));
    out[2] = (char) (0x80 | (cp & 0x3F));
    return 3;
  }
  out[0] = (char) (0xF0 | (cp >> 18));
  out[1] = (char) (0x80 | ((cp >> 12) & 0x3F));
  out[2] = (char) (0x80 | ((cp >> 6) & 0x3F));
  out[3] = (char) (0x80 | (cp & 0x3F));
  return 4;
}

static const char *gkuni_map_lookup(int cp) {
  int lo = 0, hi = gkuni_map_len - 1;

  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (gkuni_map[mid].cp == cp) return gkuni_map[mid].beta;
    if (gkuni_map[mid].cp < cp) lo = mid + 1; else hi = mid - 1;
  }
  return 0;
}

static int gkuni_comp_lookup(int cp1, int cp2) {
  int lo = 0, hi = gkuni_comp_len - 1;

  while (lo <= hi) {
    const gkuni_comp_entry *e;
    int mid = (lo + hi) / 2;
    e = &gkuni_comp[mid];
    if (e->cp1 == cp1 && e->cp2 == cp2) return e->result;
    if (e->cp1 < cp1 || (e->cp1 == cp1 && e->cp2 < cp2)) lo = mid + 1;
    else hi = mid - 1;
  }
  return -1;
}

static int gkuni_ccc_of(int cp) {
  int lo = 0, hi = gkuni_ccc_len - 1;

  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (gkuni_ccc[mid].cp == cp) return gkuni_ccc[mid].ccc;
    if (gkuni_ccc[mid].cp < cp) lo = mid + 1; else hi = mid - 1;
  }
  return 0;
}

static int gkuni_lower_of(int cp) {
  int lo = 0, hi = gkuni_lower_len - 1;

  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (gkuni_lower[mid].cp == cp) return gkuni_lower[mid].lower;
    if (gkuni_lower[mid].cp < cp) lo = mid + 1; else hi = mid - 1;
  }
  return cp;
}

static const gkuni_nfd_entry *gkuni_nfd_lookup(int cp) {
  int lo = 0, hi = gkuni_nfd_len - 1;

  while (lo <= hi) {
    int mid = (lo + hi) / 2;
    if (gkuni_nfd[mid].cp == cp) return &gkuni_nfd[mid];
    if (gkuni_nfd[mid].cp < cp) lo = mid + 1; else hi = mid - 1;
  }
  return 0;
}

/* Convert UTF-8 Greek to lowercase beta code.
 *
 * Returns 0 on success (NUL-terminated in out), -1 on malformed input,
 * an over-long token, or an output-buffer overflow; callers treat -1 like a
 * miss. Empty input converts to "".
 */
int gkuni_convert(const char *in, char *out, size_t outsz) {
  const unsigned char *p = (const unsigned char *) in;
  int cps[GKUNI_MAX];
  int res[GKUNI_MAX];
  int n = 0, rn = 0;
  int i, j, o = 0;

  while (*p) {
    int cp, len = gkuni_utf8_decode(p, &cp);
    if (len < 0 || n >= GKUNI_MAX) return -1;
    /* to_beta's pre-translations run before NFC: curly apostrophes first ... */
    if (cp == 0x2019 || cp == 0x2018 || cp == 0x02BC || cp == 0x00B4) cp = '\'';
    cps[n++] = cp;
    p += len;
  }
  if (outsz < 1) return -1;
  if (n == 0) {
    out[0] = 0;
    return 0;
  }
  /* ... then the word-final elision comma. */
  if (n > 1 && cps[n - 1] == 0x0313) cps[n - 1] = '\'';

  /* Canonical decomposition: NFC is full NFD followed by recomposition, and
   * singleton decompositions (U+0340, U+0343, U+0344, ...) are not pairs. */
  {
    int expanded[GKUNI_MAX];
    int en = 0, k;
    for (i = 0; i < n; i++) {
      const gkuni_nfd_entry *e = gkuni_nfd_lookup(cps[i]);
      if (e) {
        for (k = 0; e->nfd[k]; k++) {
          if (en >= GKUNI_MAX) return -1;
          expanded[en++] = e->nfd[k];
        }
      } else {
        if (en >= GKUNI_MAX) return -1;
        expanded[en++] = cps[i];
      }
    }
    memcpy(cps, expanded, sizeof(int) * (size_t) en);
    n = en;
  }

  /* Canonical ordering: stable insertion sort of each combining-mark run. */
  for (i = 1; i < n; i++) {
    int mark = cps[i], k = i;
    if (gkuni_ccc_of(mark) == 0) continue;
    while (k > 0 && gkuni_ccc_of(cps[k - 1]) > gkuni_ccc_of(mark)) {
      cps[k] = cps[k - 1];
      k--;
    }
    cps[k] = mark;
  }

  /* NFC composition: greedy pairs against the current starter; marks that do
   * not compose stay pending and block later marks with the same or higher
   * combining class (UAX #15 blocking rule). */
  i = 0;
  while (i < n) {
    int starter = cps[i++];
    int pending[8], np = 0;

    while (i < n && gkuni_ccc_of(cps[i]) > 0) {
      int mark = cps[i++], blocked = 0, composed;
      for (j = 0; j < np; j++) {
        if (gkuni_ccc_of(pending[j]) >= gkuni_ccc_of(mark)) blocked = 1;
      }
      composed = blocked ? -1 : gkuni_comp_lookup(starter, mark);
      if (composed >= 0) starter = composed;
      else if (np < 8) pending[np++] = mark;
      else return -1;
    }
    if (rn + np + 1 > GKUNI_MAX) return -1;
    res[rn++] = starter;
    for (j = 0; j < np; j++) res[rn++] = pending[j];
  }

  /* Map + lowercase (pass-through codepoints get their Unicode lowercase). */
  for (i = 0; i < rn; i++) {
    const char *beta = gkuni_map_lookup(res[i]);
    if (beta) {
      size_t len = strlen(beta);
      if (o + (int) len + 1 > (int) outsz) return -1;
      for (j = 0; j < (int) len; j++) {
        out[o++] = (char) tolower((unsigned char) beta[j]);
      }
    } else {
      char tmp[4];
      int len = gkuni_utf8_encode(gkuni_lower_of(res[i]), tmp);
      if (o + len + 1 > (int) outsz) return -1;
      for (j = 0; j < len; j++) out[o++] = tmp[j];
    }
  }
  out[o] = 0;
  return 0;
}
