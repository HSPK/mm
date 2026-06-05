"""Library initialization workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mm.config import add_database, get_config, set_active_database
from mm.db.sync_client import DBClient
from mm.io import local_storage
from mm.library.settings import LibraryConfig


@dataclass(frozen=True)
class LibrarySetupRequirements:
    destination: Path
    db_path: Path
    needs_admin_user: bool


@dataclass(frozen=True)
class LibrarySetupResult:
    db_path: Path
    active_index: int
    seeded_smart_albums: int
    created_admin_user: str | None


def inspect_library_setup(directory: Path) -> LibrarySetupRequirements:
    """Resolve setup paths and report what interactive inputs are needed."""
    destination = directory.resolve()
    local_storage.mkdir(destination)
    db_path = destination / get_config().import_.db_name
    db = DBClient(db_path)
    try:
        needs_admin = db.user.count() == 0
    finally:
        db.close()
    return LibrarySetupRequirements(destination, db_path, needs_admin)


def initialize_library(
    *,
    destination: Path,
    name: str,
    import_template: str,
    library_root: Path,
    admin_username: str | None = None,
    admin_password: str | None = None,
    seed_smart_albums: bool = True,
) -> LibrarySetupResult:
    """Create or update a library database and register it as active."""
    local_storage.mkdir(destination)
    db_path = destination / get_config().import_.db_name
    config = LibraryConfig(
        library_name=name,
        import_template=import_template,
        library_root=library_root,
    )
    db = DBClient(db_path)
    created_admin: str | None = None
    seeded = 0
    try:
        db.library_config.set(config)

        if db.user.count() == 0 and admin_username and admin_password:
            db.user.create(
                admin_username,
                password=admin_password,
                display_name=admin_username,
                is_admin=True,
            )
            created_admin = admin_username

        if seed_smart_albums:
            seeded = db.smart_album.seed()
    finally:
        db.close()

    index = add_database(db_path, name=name)
    set_active_database(index)
    return LibrarySetupResult(
        db_path=db_path,
        active_index=index,
        seeded_smart_albums=seeded,
        created_admin_user=created_admin,
    )
