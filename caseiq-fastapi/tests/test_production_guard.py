"""Pure-function tests, no DB -- scripts.lib.production_guard's shared
write-confirmation gate (docs/evaluation.md, observability entry).

Monkeypatches scripts.lib.production_guard.settings directly (a simple
namespace with the two attributes the guard reads) rather than constructing
a real app.core.config.Settings -- this module's own job is just "read
settings.DATABASE_URL and settings.ENV, decide what to print/require", and
testing that logic shouldn't depend on a real DB URL parsing successfully
through the whole Settings validator stack.
"""
from types import SimpleNamespace

import pytest

from scripts.lib import production_guard


def _fake_settings(host: str, env: str = "production"):
    return SimpleNamespace(DATABASE_URL=f"postgresql+asyncpg://user:pw@{host}:5432/db", ENV=env)


class TestConfirmWritableTarget:
    def test_localhost_returns_silently_no_prompt(self, monkeypatch, capsys):
        monkeypatch.setattr(production_guard, "settings", _fake_settings("localhost"))
        production_guard.confirm_writable_target("my-script")
        assert capsys.readouterr().out == ""  # zero friction for the normal local case

    def test_loopback_ip_returns_silently_no_prompt(self, monkeypatch, capsys):
        monkeypatch.setattr(production_guard, "settings", _fake_settings("127.0.0.1"))
        production_guard.confirm_writable_target("my-script")
        assert capsys.readouterr().out == ""

    def test_non_local_host_with_skip_prompt_proceeds(self, monkeypatch, capsys):
        monkeypatch.setattr(production_guard, "settings", _fake_settings("ep-x.neon.tech"))
        production_guard.confirm_writable_target("my-script", skip_prompt=True)
        out = capsys.readouterr().out
        assert "ep-x.neon.tech" in out
        assert "Confirmed via --yes." in out

    def test_non_local_host_with_env_var_override_proceeds(self, monkeypatch, capsys):
        monkeypatch.setattr(production_guard, "settings", _fake_settings("ep-x.neon.tech"))
        monkeypatch.setenv("CONFIRM_PRODUCTION_WRITE", "1")
        production_guard.confirm_writable_target("my-script")
        assert "Confirmed via CONFIRM_PRODUCTION_WRITE=1." in capsys.readouterr().out

    def test_non_local_host_interactive_yes_proceeds(self, monkeypatch, capsys):
        monkeypatch.setattr(production_guard, "settings", _fake_settings("ep-x.neon.tech"))
        monkeypatch.setattr("builtins.input", lambda _: "yes")
        production_guard.confirm_writable_target("my-script")  # must not raise/exit

    def test_non_local_host_interactive_no_aborts(self, monkeypatch, capsys):
        monkeypatch.setattr(production_guard, "settings", _fake_settings("ep-x.neon.tech"))
        monkeypatch.setattr("builtins.input", lambda _: "no")
        with pytest.raises(SystemExit) as exc:
            production_guard.confirm_writable_target("my-script")
        assert exc.value.code == 1

    def test_non_local_host_garbage_answer_aborts(self, monkeypatch):
        # Anything other than the exact string "yes" -- no fuzzy matching on
        # a decision this consequential.
        monkeypatch.setattr(production_guard, "settings", _fake_settings("ep-x.neon.tech"))
        monkeypatch.setattr("builtins.input", lambda _: "sure")
        with pytest.raises(SystemExit):
            production_guard.confirm_writable_target("my-script")

    def test_env_shown_for_context_but_does_not_gate(self, monkeypatch, capsys):
        # The whole point: a NON-local host still requires confirmation
        # even when settings.ENV claims "development" -- exactly the real
        # .env shape (ENV=development sitting next to real production
        # credentials) that would defeat an ENV-based check.
        monkeypatch.setattr(production_guard, "settings", _fake_settings("ep-x.neon.tech", env="development"))
        production_guard.confirm_writable_target("my-script", skip_prompt=True)
        out = capsys.readouterr().out
        assert "ep-x.neon.tech" in out
        assert "development" in out
