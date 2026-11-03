"""Tests for scripts/repomem-crontab.sh.

Regression cover for the install.sh crontab bug: the old one-liner piped
`crontab -l | grep -v "repomem"` back into `crontab -`, which deleted every
line containing that word. On a real machine that was 8 matching lines
replaced by 2, including jobs the installer never created.

Every test drives a fake `crontab` backed by a temp file through CRONTAB_BIN.
The real crontab is never read or written.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "repomem-crontab.sh"

REFLECT = "0 2 * * * REPOMEM_INSTALL=/r/lib python3 /r/crons/reflect.py >> /r/logs/reflect.log 2>&1"
DEFRAG = "0 3 * * 0 REPOMEM_INSTALL=/r/lib python3 /r/crons/defrag.py >> /r/logs/defrag.log 2>&1"

BEGIN = "# >>> repomem (managed by RepoMem install.sh) >>>"
END = "# <<< repomem (managed by RepoMem install.sh) <<<"

# A line that merely mentions the word, which the old grep -v destroyed.
FOREIGN_MENTIONING = "30 14 * * * /usr/local/bin/cron-run repomem-obsidian -- /bin/true"
FOREIGN_UNRELATED = "0 9 * * 1 /usr/local/bin/backup.sh"


@pytest.fixture
def fake_crontab(tmp_path: Path):
    """A stub `crontab` executable backed by a file, plus helpers."""
    store = tmp_path / "crontab.txt"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stub = bin_dir / "crontab"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        f'STORE="{store}"\n'
        'if [ "${1:-}" = "-l" ]; then\n'
        '  [ -f "$STORE" ] || exit 1\n'
        '  cat "$STORE"\n'
        'elif [ "${1:-}" = "-" ]; then\n'
        '  cat > "$STORE"\n'
        "else\n"
        '  echo "unexpected args: $*" >&2; exit 2\n'
        "fi\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)

    class Harness:
        path = store
        binary = stub

        def seed(self, *lines: str) -> None:
            store.write_text("\n".join(lines) + "\n", encoding="utf-8")

        def read(self) -> list[str]:
            if not store.exists():
                return []
            return store.read_text(encoding="utf-8").splitlines()

        def run(self) -> subprocess.CompletedProcess:
            env = dict(os.environ)
            env.update(
                CRONTAB_BIN=str(stub),
                CRON_REFLECT=REFLECT,
                CRON_DEFRAG=DEFRAG,
            )
            return subprocess.run(
                ["bash", str(SCRIPT)],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

    return Harness()


def test_script_exists():
    assert SCRIPT.is_file(), f"missing {SCRIPT}"


def test_installs_into_an_empty_crontab(fake_crontab):
    result = fake_crontab.run()
    assert result.returncode == 0, result.stderr
    lines = fake_crontab.read()
    assert lines == [BEGIN, REFLECT, DEFRAG, END]


def test_no_blank_line_when_crontab_was_empty(fake_crontab):
    fake_crontab.run()
    assert "" not in fake_crontab.read()


def test_keeps_a_foreign_line_that_mentions_repomem(fake_crontab):
    """The actual bug: this line used to be deleted."""
    fake_crontab.seed(FOREIGN_MENTIONING)
    result = fake_crontab.run()
    assert result.returncode == 0, result.stderr
    assert FOREIGN_MENTIONING in fake_crontab.read()


def test_keeps_unrelated_lines(fake_crontab):
    fake_crontab.seed(FOREIGN_UNRELATED, FOREIGN_MENTIONING)
    fake_crontab.run()
    lines = fake_crontab.read()
    assert FOREIGN_UNRELATED in lines
    assert FOREIGN_MENTIONING in lines


def test_foreign_lines_keep_their_order_and_come_first(fake_crontab):
    fake_crontab.seed(FOREIGN_UNRELATED, FOREIGN_MENTIONING)
    fake_crontab.run()
    lines = fake_crontab.read()
    assert lines[:2] == [FOREIGN_UNRELATED, FOREIGN_MENTIONING]
    assert lines[2] == BEGIN


def test_is_idempotent(fake_crontab):
    fake_crontab.seed(FOREIGN_UNRELATED)
    fake_crontab.run()
    first = fake_crontab.read()
    fake_crontab.run()
    assert fake_crontab.read() == first


def test_rewrites_only_its_own_block_on_reinstall(fake_crontab):
    fake_crontab.seed(FOREIGN_UNRELATED, BEGIN, "0 1 * * * /old/reflect", END)
    result = fake_crontab.run()
    assert result.returncode == 0, result.stderr
    lines = fake_crontab.read()
    assert "0 1 * * * /old/reflect" not in lines
    assert lines == [FOREIGN_UNRELATED, BEGIN, REFLECT, DEFRAG, END]
    assert lines.count(BEGIN) == 1


def test_refuses_when_an_unmanaged_repomem_cron_exists(fake_crontab):
    """A hand-scheduled wrapper around our crons must not be clobbered."""
    custom = "0 22 * * * /usr/local/bin/cron-run reflect-2200 -- python3 /r/crons/reflect.py"
    fake_crontab.seed(FOREIGN_UNRELATED, custom)
    result = fake_crontab.run()
    assert result.returncode == 1
    assert "NOT changed" in result.stderr
    assert "reflect-2200" in result.stderr


def test_refusal_leaves_the_crontab_byte_identical(fake_crontab):
    custom = "0 22 * * * /usr/local/bin/cron-run reflect-2200 -- python3 /r/crons/reflect.py"
    fake_crontab.seed(FOREIGN_UNRELATED, custom)
    before = fake_crontab.path.read_bytes()
    fake_crontab.run()
    assert fake_crontab.path.read_bytes() == before


def test_detects_an_unmanaged_defrag_too(fake_crontab):
    fake_crontab.seed("0 5 * * 0 python3 /r/crons/defrag.py")
    result = fake_crontab.run()
    assert result.returncode == 1
    assert "defrag.py" in result.stderr


def test_managed_block_is_not_treated_as_legacy(fake_crontab):
    """Our own block contains crons/reflect.py; that must not trip the guard."""
    fake_crontab.seed(BEGIN, REFLECT, DEFRAG, END)
    result = fake_crontab.run()
    assert result.returncode == 0, result.stderr
    assert fake_crontab.read() == [BEGIN, REFLECT, DEFRAG, END]


def test_requires_the_cron_variables(fake_crontab):
    env = dict(os.environ)
    env.update(CRONTAB_BIN=str(fake_crontab.binary))
    env.pop("CRON_REFLECT", None)
    env.pop("CRON_DEFRAG", None)
    result = subprocess.run(
        ["bash", str(SCRIPT)], env=env, capture_output=True, text=True, check=False
    )
    assert result.returncode != 0
    assert "CRON_REFLECT" in result.stderr


def test_old_buggy_oneliner_would_have_deleted_the_foreign_line(fake_crontab):
    """Pins the bug being fixed, so nobody reintroduces the grep -v."""
    fake_crontab.seed(FOREIGN_UNRELATED, FOREIGN_MENTIONING)
    survivors = subprocess.run(
        ["bash", "-c", f'cat "{fake_crontab.path}" | grep -v repomem'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    assert FOREIGN_MENTIONING not in survivors
    assert FOREIGN_UNRELATED in survivors
