"""Rename event-listener orchestration (events.py::sync_nativeauth_on_rename).

Renaming a JupyterHub `orm.User` must sync the NativeAuthenticator `UserInfo`
row (so the account's authorisation + password survive the rename) and record a
rename event. Driven through the REAL SQLAlchemy `set` listener on
`orm.User.name`, against an in-memory DB carrying both the JupyterHub and
NativeAuthenticator tables. Creating the User fires the sibling `after_insert`
listener which auto-creates its `UserInfo` (exactly as the admin "create user"
path does), so we let that happen and clear the event log before the rename to
isolate the rename event. The activity + profile syncs have their own helper
tests (test_activity_monitor / test_user_profiles).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="module", autouse=True)
def _register_listeners():
    """Attach the SQLAlchemy listeners once for the module (calling register_events
    per test would stack duplicate listeners on the global orm.User.name)."""
    from optimum_hub_services.events import register_events
    register_events()


@pytest.fixture
def orm_session(tmp_path, monkeypatch):
    """In-memory DB with JupyterHub + NativeAuth tables; side-effect stores point
    at temp files so the listener's profile/event writes never touch /data."""
    monkeypatch.setenv("STELLARS_EVENT_LOG_DB_PATH", str(tmp_path / "events.sqlite"))
    monkeypatch.setenv("STELLARS_USER_PROFILES_DB_PATH", str(tmp_path / "profiles.sqlite"))
    from optimum_hub_services.event_log import EventLogManager
    from optimum_hub_services.user_profiles import UserProfileManager
    EventLogManager._instance = None
    UserProfileManager._instance = None

    from jupyterhub import orm as jh_orm
    from nativeauthenticator.orm import Base as NativeBase

    engine = create_engine("sqlite://")
    jh_orm.Base.metadata.create_all(engine)
    NativeBase.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    EventLogManager._instance = None
    UserProfileManager._instance = None


def test_rename_syncs_nativeauth_and_records_event(orm_session):
    from jupyterhub import orm as jh_orm
    from nativeauthenticator.orm import UserInfo
    from optimum_hub_services.event_log import EventLogManager

    # create the user -> after_insert auto-creates its (authorised) UserInfo row
    orm_session.add(jh_orm.User(name="old.name"))
    orm_session.commit()
    assert orm_session.query(UserInfo).filter_by(username="old.name").first() is not None
    EventLogManager.get_instance().clear()  # drop the create-time noise

    # the rename: assigning User.name fires sync_nativeauth_on_rename synchronously
    user = orm_session.query(jh_orm.User).filter_by(name="old.name").one()
    user.name = "new.name"
    orm_session.commit()

    # UserInfo followed the rename, authorisation preserved, old row gone
    moved = orm_session.query(UserInfo).filter_by(username="new.name").first()
    assert moved is not None
    assert moved.is_authorized is True
    assert orm_session.query(UserInfo).filter_by(username="old.name").first() is None

    # a rename event was recorded for the Events feed
    events = EventLogManager.get_instance().recent()
    assert any("renamed to" in e["text"] and "new.name" in e["text"] for e in events)


def test_rename_event_names_the_actor(orm_session):
    """With a rename actor set (as the rename API handler does), the recorded event
    names WHO renamed whom."""
    from jupyterhub import orm as jh_orm
    from optimum_hub_services.events import set_rename_actor, reset_rename_actor
    from optimum_hub_services.event_log import EventLogManager

    orm_session.add(jh_orm.User(name="bob"))
    orm_session.commit()
    EventLogManager.get_instance().clear()

    token = set_rename_actor("adminksh")
    try:
        user = orm_session.query(jh_orm.User).filter_by(name="bob").one()
        user.name = "robert"
        orm_session.commit()
    finally:
        reset_rename_actor(token)

    events = EventLogManager.get_instance().recent()
    assert any(
        "adminksh" in e["text"] and "renamed" in e["text"] and "robert" in e["text"]
        for e in events
    ), events


def test_rename_noop_when_name_unchanged(orm_session):
    """Setting User.name to its current value (oldvalue == value) must record no
    rename event - the listener early-returns."""
    from jupyterhub import orm as jh_orm
    from optimum_hub_services.event_log import EventLogManager

    orm_session.add(jh_orm.User(name="stable"))
    orm_session.commit()
    EventLogManager.get_instance().clear()

    user = orm_session.query(jh_orm.User).filter_by(name="stable").one()
    user.name = "stable"  # same value -> early return
    orm_session.commit()

    events = EventLogManager.get_instance().recent()
    assert not any("renamed to" in e["text"] for e in events)
