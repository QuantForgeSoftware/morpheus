from morpheus_toolkit.runner import MorpheusRunner

# `cruncher -q` emits `:form <token>` before every input, including misses.
MARKED = (
    ":form\ta)/nqrwpos\n"
    "a)/nqrwpos\n"
    "<NL>N a)/nqrwpos  masc nom sg\t\t\tos_ou</NL>\n"
    ":form\tzzzzqq\n"
    "zzzzqq\n"
    ":form\tlo/gos\n"
    ":longtime\t0.00\tlo/gos\n"
    "lo/gos\n"
    "<NL>N lo/gos  masc nom sg\t\t\tos_ou</NL>\n"
)


def test_marked_alignment_keeps_misses_in_position():
    records = MorpheusRunner._align_marked(MARKED, 3)
    assert len(records) == 3
    assert records[0][0].lemma == "ἄνθρωπος"
    assert records[1] == []  # the miss stays aligned
    assert records[2][0].lemma == "λόγος"


def test_marked_alignment_pads_to_input_count():
    records = MorpheusRunner._align_marked(":form\ta)/nqrwpos\na)/nqrwpos\n", 2)
    assert records == [[], []]


def test_ignore_accents_adds_the_n_flag(monkeypatch):
    runner = MorpheusRunner(cruncher="/bin/echo")
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    runner.analyze_beta(["qeos"], ignore_accents=True)
    assert "-n" in captured["argv"]
    runner.analyze_beta(["qeos"])
    assert "-n" not in captured["argv"]
