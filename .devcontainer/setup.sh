#!/usr/bin/env bash
# .devcontainer/setup.sh — runs once inside the container after creation.
# Safe to re-run; all steps are idempotent.
set -euo pipefail

# ── System packages ───────────────────────────────────────────────────────────
echo "→ Installing system packages (vim)…"
sudo apt-get update -qq && sudo apt-get install -y --no-install-recommends vim

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

# ── SSH config compatibility ─────────────────────────────────────────────────
# The host ~/.ssh/config may use options added in newer OpenSSH releases
# (e.g. `WarnWeakCrypto`, added in 10.2). An older client in the container
# rejects the *entire* file with "Bad configuration option", which breaks every
# git ssh operation (fetch/push). Comment out only the offending options, and
# keep doing so until the config parses cleanly.
if [ -f ~/.ssh/config ]; then
    for _ in $(seq 1 20); do
        err="$(ssh -F ~/.ssh/config -G github.com 2>&1 >/dev/null)" || true
        case "$err" in
            *"Bad configuration option:"*) ;;
            *) break ;;
        esac
        opt="$(printf '%s\n' "$err" \
            | sed -n 's/.*Bad configuration option: *\([A-Za-z][A-Za-z0-9]*\).*/\1/p' \
            | head -1)"
        [ -n "$opt" ] || break
        before="$(md5sum ~/.ssh/config | cut -d' ' -f1)"
        sed -i "s|^[[:space:]]*\(${opt}[[:space:]=]\)|# [devcontainer] '${opt}' unsupported by $(ssh -V 2>&1 | cut -d' ' -f1): \1|I" ~/.ssh/config
        after="$(md5sum ~/.ssh/config | cut -d' ' -f1)"
        [ "$before" = "$after" ] && break
        echo "  Disabled unsupported ssh option: ${opt}"
    done
fi

# ── GitHub CLI (gh) host login ───────────────────────────────────────────────
# ~/.config/gh is bind-mounted from the host so the host's `gh` login is
# reused as-is — no copy step and no re-authentication. A bind mount keeps the
# host uid, which usually differs from the container user, so grant the
# container user ownership (otherwise a 0600 hosts.yml is unreadable and gh
# fails).
echo "→ Configuring GitHub CLI (gh)…"
if [ -d ~/.config/gh ]; then
    sudo chown -R "$(id -u):$(id -g)" ~/.config/gh
    if gh auth status >/dev/null 2>&1; then
        echo "  Host gh login reused (authenticated)."
    else
        echo "  WARNING: gh is not logged in on the host — run 'gh auth login' on the host."
    fi
else
    echo "  No host ~/.config/gh found — gh will not be authenticated."
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
echo "   gh        : $(gh --version 2>&1 | head -1 || echo 'not installed')"
