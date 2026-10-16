/* Table declarations for the Unicode-native input path (Round 19.4).
 *
 * Generated data lives in gkunicode_tab.c
 * (scripts/gen_gkunicode_tables.py); the conversion itself is in gkunicode.c.
 */
#ifndef GKUNICODE_TAB_H
#define GKUNICODE_TAB_H

typedef struct {
  int cp;
  const char *beta;
} gkuni_map_entry;

typedef struct {
  int cp1;
  int cp2;
  int result;
} gkuni_comp_entry;

typedef struct {
  int cp;
  int ccc;
} gkuni_ccc_entry;

typedef struct {
  int cp;
  int lower;
} gkuni_lower_entry;

typedef struct {
  int cp;
  int nfd[5];  /* zero-terminated canonical decomposition (max 4 codepoints) */
} gkuni_nfd_entry;

extern const gkuni_map_entry gkuni_map[];
extern const int gkuni_map_len;
extern const gkuni_comp_entry gkuni_comp[];
extern const int gkuni_comp_len;
extern const gkuni_ccc_entry gkuni_ccc[];
extern const int gkuni_ccc_len;
extern const gkuni_lower_entry gkuni_lower[];
extern const int gkuni_lower_len;
extern const gkuni_nfd_entry gkuni_nfd[];
extern const int gkuni_nfd_len;

#endif
