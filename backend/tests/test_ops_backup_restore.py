"""Test and verify backup and restore procedures for ECDAT."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from sqlmodel import Session, create_engine, select

from api.db_models import AuditLogRecord, PolicyRecord, TargetRecord


def test_sqlite_backup_and_restore_cycle(tmp_path: Path) -> None:
    """Proves: create data -> backup -> delete DB -> restore -> data is fully back."""
    db_path = tmp_path / "live_ecdat.db"
    backup_path = tmp_path / "backup_ecdat.db"
    db_url = f"sqlite:///{db_path}"

    engine = create_engine(db_url)
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)

    # 1. Insert test records into live database
    with Session(engine) as session:
        policy = PolicyRecord(
            id="policy_test",
            name="Backup Test Policy",
            crqc_years=10,
            default_shelf_life_years=5,
            default_migration_years=3,
            algorithm_overrides="{}",
            path_contexts="[]",
        )
        target = TargetRecord(
            id="target_test",
            name="Backup Target",
            kind="path",
            uri="/tmp/test",
            policy_id="policy_test",
            schedule="0 0 * * *",
            enabled=True,
        )
        audit = AuditLogRecord(
            action="target.create",
            entity_type="target",
            entity_id="target_test",
            detail={"name": "Backup Target"},
            prev_hash="genesis",
            record_hash="hash123",
            actor="operator-1",
        )
        session.add(policy)
        session.add(target)
        session.add(audit)
        session.commit()

    # 2. Perform SQLite online backup (equivalent to `sqlite3 ecdat.db ".backup backup.db"`)
    src_conn = sqlite3.connect(db_path)
    dst_conn = sqlite3.connect(backup_path)
    try:
        src_conn.backup(dst_conn)
    finally:
        src_conn.close()
        dst_conn.close()

    assert backup_path.exists()
    assert backup_path.stat().st_size > 0

    # 3. Destroy / delete the live database
    engine.dispose(close=True)
    del engine
    import gc
    gc.collect()

    db_path.unlink()
    assert not db_path.exists()

    # 4. Restore: copy backup back to live database path
    src_restore = sqlite3.connect(backup_path)
    dst_restore = sqlite3.connect(db_path)
    try:
        src_restore.backup(dst_restore)
    finally:
        src_restore.close()
        dst_restore.close()

    assert db_path.exists()

    # 5. Verify restored database has identical state and records
    restored_engine = create_engine(db_url)
    with Session(restored_engine) as session:
        targets = session.exec(select(TargetRecord)).all()
        assert len(targets) == 1
        assert targets[0].id == "target_test"
        assert targets[0].name == "Backup Target"

        policies = session.exec(select(PolicyRecord)).all()
        assert len(policies) == 1
        assert policies[0].id == "policy_test"

        audits = session.exec(select(AuditLogRecord)).all()
        assert len(audits) == 1
        assert audits[0].entity_id == "target_test"
        assert audits[0].actor == "operator-1"
    restored_engine.dispose()


def test_postgres_engine_url_compatibility() -> None:
    """Confirm SQLAlchemy engine configuration supports PostgreSQL URLs."""
    from sqlalchemy.engine.url import make_url

    pg_url = "postgresql://ecdat_user:secretpass@localhost:5432/ecdat_db"
    url_obj = make_url(pg_url)
    assert url_obj.drivername.startswith("postgresql")
    assert url_obj.username == "ecdat_user"
    assert url_obj.host == "localhost"
    assert url_obj.database == "ecdat_db"
