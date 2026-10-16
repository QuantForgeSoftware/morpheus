/* gkconvert: parity oracle for the Unicode-native input path (Round 19.4).
 *
 * Reads one form per line from stdin (first whitespace-delimited token, like
 * cruncher), converts UTF-8 Greek to lowercase beta with the same code the
 * cruncher's -u flag uses, and prints the result. A line the converter rejects
 * prints \x1fFAIL. Used by scripts/unicode_parity.py and
 * python/tests/test_unicode_c_path.py; not part of the analyzer pipeline.
 */
#include <stdio.h>
#include <string.h>

#include "gkunicode.proto.h"

int main(void) {
  char line[BUFSIZ * 4];
  char conv[BUFSIZ * 4];

  while (fgets(line, (int) sizeof line, stdin)) {
    char *p = line;

    while (*p && *p != '\n' && *p != '\r') p++;
    *p = 0;
    p = line;
    while (*p && *p != ' ' && *p != '\t') p++;
    *p = 0;
    if (!line[0]) {
      printf("\n");
      continue;
    }
    if (gkuni_convert(line, conv, sizeof conv) != 0) printf("\x1f" "FAIL\n");
    else printf("%s\n", conv);
  }
  return 0;
}
