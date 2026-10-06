"""Invoke the Morpheus ``cruncher`` binary and return structured analyses."""
from __future__ import annotations

import os
import subprocess
from typing import List, Optional

from .analysis import Analysis, parse_perseus_analyses

_DEFAULT_BASE = os.environ.get("MORPHEUS_DIR") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


class MorpheusRunner:
    def __init__(
        self,
        morpheus_dir: Optional[str] = None,
        cruncher: Optional[str] = None,
        stemlib: Optional[str] = None,
        timeout: int = 600,
        echo: bool = True,
    ):
        base = os.path.abspath(morpheus_dir or _DEFAULT_BASE)
        self.cruncher = cruncher or os.path.join(base, "bin", "cruncher")
        self.stemlib = stemlib or os.path.join(base, "stemlib")
        self.timeout = timeout
        self.echo = echo
        if not os.path.exists(self.cruncher):
            raise FileNotFoundError(
                f"cruncher not found at {self.cruncher!r}; build it with scripts/build.sh"
            )

    def analyze_beta(self, forms: List[str]) -> List[List[Analysis]]:
        """Analyze a list of beta-code forms; the result is aligned to the input."""
        if not forms:
            return []
        env = dict(os.environ, MORPHLIB=self.stemlib)
        argv = [self.cruncher, "-S"]
        if self.echo:
            argv.append("-q")  # emit a `:form` delimiter for every input, including misses
        proc = subprocess.run(
            argv,
            input="\n".join(forms) + "\n",
            capture_output=True,
            text=True,
            env=env,
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"cruncher failed ({proc.returncode}): {proc.stderr[:400]}")
        if self.echo and ":form\t" in proc.stdout:
            return self._align_marked(proc.stdout, len(forms))
        return self._align_echo(proc.stdout, len(forms))

    @staticmethod
    def _align_marked(stdout: str, count: int) -> List[List[Analysis]]:
        """Align using the `:form` delimiters emitted by `cruncher -q`."""
        records: List[List[Analysis]] = []
        current: Optional[List[Analysis]] = None
        for line in stdout.splitlines():
            if line.startswith(":form\t"):
                current = []
                records.append(current)
            elif "<NL>" in line:
                analyses = parse_perseus_analyses(line)
                if current is None:
                    current = analyses
                    records.append(current)
                else:
                    current.extend(analyses)
        while len(records) < count:
            records.append([])
        return records[:count]

    @staticmethod
    def _align_echo(stdout: str, count: int) -> List[List[Analysis]]:
        """Legacy alignment for binaries without `-q` (unreliable when there are misses)."""
        records: List[List[Analysis]] = []
        current: Optional[List[Analysis]] = None
        for line in stdout.splitlines():
            if not line.strip() or line.startswith(":longtime"):
                continue
            if "<NL>" in line:
                analyses = parse_perseus_analyses(line)
                if current is None:
                    current = analyses
                    records.append(current)
                else:
                    current.extend(analyses)
            else:
                current = []
                records.append(current)
        while len(records) < count:
            records.append([])
        return records[:count]
