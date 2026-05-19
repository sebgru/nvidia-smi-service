#!/usr/bin/env bash
# .devcontainer/setup.sh — runs once inside the container after creation.
# Safe to re-run; all steps are idempotent.
set -euo pipefail

# ── Dev tools ─────────────────────────────────────────────────────────────────
echo "→ Installing dev tools (ruff, pytest)…"
pip install --quiet ruff pytest

# ── SSH keys ──────────────────────────────────────────────────────────────────
# .ssh is staged at /tmp/host-ssh (bind-mounted read-only from the host).
# We copy it to ~/.ssh with the permissions SSH requires (700/600).
# Contributors without an .ssh directory simply skip this step.
echo "→ Configuring SSH…"
if [ -d /tmp/host-ssh ] && [ -n "$(ls -A /tmp/host-ssh 2>/dev/null)" ]; then
    mkdir -p ~/.ssh
    cp -rp /tmp/host-ssh/. ~/.ssh/
    chmod 700 ~/.ssh
    find ~/.ssh -type f -exec chmod 600 {} \;
    echo "  SSH keys installed."
else
    echo "  No SSH keys found on host — skipping."
fi

# ── .profile (SSH signing env vars etc.) ─────────────────────────────────────
# The host .profile is mounted to ~/.profile-host.
# VS Code terminals start as non-login interactive shells, so ~/.profile is
# not sourced automatically.  We add a one-time source line to both rc files.
echo "→ Wiring ~/.profile-host into shell init files…"
if [ -s ~/.profile-host ]; then
    for rc in ~/.bashrc ~/.zshrc; do
        if [ -f "$rc" ] && ! grep -q 'profile-host' "$rc" 2>/dev/null; then
            echo '' >> "$rc"
            echo '# Sourced by devcontainer setup — host .profile (SSH signing, etc.)' >> "$rc"
            echo 'source ~/.profile-host 2>/dev/null || true' >> "$rc"
        fi
    done
    echo "  Done."
else
    echo "  ~/.profile-host is empty — skipping."
fi

echo ""
echo "✅ Container setup complete."
echo "   Workspace : /workspace"
echo "   Python    : $(python3 --version)"
echo "   ruff      : $(ruff --version)"
echo "   pytest    : $(pytest --version 2>&1 | head -1)"
