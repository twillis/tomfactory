#!/bin/sh
# Install the /factory command for Claude Code, pointing at this clone of tomfactory.
#
#   orchestrator/install.sh            # for every project: ~/.claude/commands/factory.md
#   orchestrator/install.sh PROJECT    # for one project:   PROJECT/.claude/commands/factory.md
#
# It writes one file, with this clone's path filled in. Run it again after moving the clone.
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
dest=${1:+$1/.claude/commands}
dest=${dest:-$HOME/.claude/commands}
mkdir -p "$dest"
sed "s|@TOMFACTORY@|$here|g" "$here/orchestrator/factory.md" > "$dest/factory.md"
echo "installed $dest/factory.md, using the factory at $here"
