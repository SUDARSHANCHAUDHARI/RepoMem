#!/usr/bin/env bash
# Installs RepoMem's cron jobs without touching anyone else's crontab lines.
#
# The old one-liner was:
#
#   (crontab -l | grep -v "repomem"; echo "$CRON_REFLECT"; echo "$CRON_DEFRAG") | crontab -
#
# `grep -v "repomem"` deletes every line containing that word, so any unrelated
# job whose command happens to mention repomem is destroyed on install. On a
# real machine that was 8 matching lines replaced by 2.
#
# This version manages only the block it wrote itself, delimited by sentinels.
# Lines that run RepoMem's crons but sit outside that block are reported and
# left alone: they may be deliberately re-scheduled wrappers, and guessing
# wrong would throw away a schedule the user chose.

set -euo pipefail

CRON_BEGIN="# >>> repomem (managed by RepoMem install.sh) >>>"
CRON_END="# <<< repomem (managed by RepoMem install.sh) <<<"

# Overridable so the test suite can run against a fake crontab.
CRONTAB_BIN="${CRONTAB_BIN:-crontab}"

# stdin -> stdout, dropping our own sentinel block (and nothing else).
repomem_cron_strip_block() {
    awk -v begin="$CRON_BEGIN" -v end="$CRON_END" '
        $0 == begin { skip = 1; next }
        $0 == end   { skip = 0; next }
        !skip
    '
}

# stdin -> stdout, listing lines that run our cron scripts. Used to detect a
# hand-managed or legacy job so we never duplicate or clobber its schedule.
repomem_cron_legacy_lines() {
    grep -E 'crons/(reflect|defrag)\.py' || true
}

# Writes the managed block. Returns 1 without touching the crontab when an
# unmanaged RepoMem job already exists.
repomem_cron_install() {
    local current stripped legacy

    current="$("$CRONTAB_BIN" -l 2>/dev/null || true)"
    stripped="$(printf '%s' "$current" | repomem_cron_strip_block)"
    legacy="$(printf '%s' "$stripped" | repomem_cron_legacy_lines)"

    if [ -n "$legacy" ]; then
        {
            echo "repomem: RepoMem cron jobs already exist outside the managed block:"
            printf '  %s\n' "$legacy"
            echo "repomem: the crontab was NOT changed, so your schedule is intact."
            echo "repomem: remove those lines (or keep them) and re-run to let the installer manage them."
        } >&2
        return 1
    fi

    {
        # Keep foreign lines exactly as they were, then append our block.
        [ -n "$stripped" ] && printf '%s\n' "$stripped"
        printf '%s\n%s\n%s\n%s\n' \
            "$CRON_BEGIN" "$CRON_REFLECT" "$CRON_DEFRAG" "$CRON_END"
    } | "$CRONTAB_BIN" -
}

# Only run when executed directly; the test suite sources this file.
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    : "${CRON_REFLECT:?CRON_REFLECT must be set}"
    : "${CRON_DEFRAG:?CRON_DEFRAG must be set}"
    repomem_cron_install
fi
