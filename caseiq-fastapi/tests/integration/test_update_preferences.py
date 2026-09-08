"""Integration tests for PATCH /auth/me (app.api.v1.auth.update_preferences),
added 2026-09-07 alongside the profile page's preferences section --
`preferred_language`/`state`/`district` all already existed as columns on
`User`; this is the first write path for any of them after registration.
`exclude_unset` is the behaviour actually worth testing here -- a full
overwrite would be the easy, wrong way to build this endpoint.
"""
from __future__ import annotations

import pytest

from app.api.v1.auth import update_preferences
from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import UpdatePreferencesIn

pytestmark = pytest.mark.integration


async def _make_user(db, email="prefs@example.com"):
    user = User(email=email, full_name="Prefs User", hashed_password=hash_password("testpassword123"))
    db.add(user)
    await db.flush()
    return user


async def test_update_preferences_sets_preferred_language(db):
    user = await _make_user(db)
    await db.commit()

    result = await update_preferences(UpdatePreferencesIn(preferred_language="hi"), user, db)

    assert result.preferred_language == "hi"
    assert user.preferred_language == "hi"


async def test_update_preferences_sets_state_and_district_together(db):
    user = await _make_user(db)
    await db.commit()

    result = await update_preferences(
        UpdatePreferencesIn(state="Maharashtra", district="Mumbai Suburban"), user, db,
    )

    assert result.state == "Maharashtra"
    assert result.district == "Mumbai Suburban"


async def test_update_preferences_partial_update_does_not_clear_other_fields(db):
    """The one behaviour this endpoint exists to get right: updating ONE
    field must not null out a field a DIFFERENT request already set --
    exclude_unset, not a full-object overwrite."""
    user = await _make_user(db)
    await db.commit()

    await update_preferences(
        UpdatePreferencesIn(state="Maharashtra", district="Mumbai Suburban"), user, db,
    )
    result = await update_preferences(UpdatePreferencesIn(preferred_language="mr"), user, db)

    assert result.preferred_language == "mr"
    assert result.state == "Maharashtra"  # still set -- not wiped by the language-only request
    assert result.district == "Mumbai Suburban"


async def test_update_preferences_empty_payload_changes_nothing(db):
    user = await _make_user(db)
    await db.commit()
    original_language = user.preferred_language

    result = await update_preferences(UpdatePreferencesIn(), user, db)

    assert result.preferred_language == original_language
    assert result.state is None
    assert result.district is None


async def test_update_preferences_response_includes_created_at(db):
    """UserOut gained created_at in this same pass -- the column already
    existed via the Timestamped mixin, this just exposes it."""
    user = await _make_user(db)
    await db.commit()

    result = await update_preferences(UpdatePreferencesIn(preferred_language="ta"), user, db)

    assert result.created_at is not None
