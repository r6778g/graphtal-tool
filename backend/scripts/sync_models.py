#!/usr/bin/env python3
"""Synchronize approved private model artifacts into the local versioned cache."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import model_registry as registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, choices=sorted(registry.SUPPORTED_MODULES))
    parser.add_argument(
        "--version", default="latest",
        help="latest active versions, a numeric approved version, or a model UUID",
    )
    parser.add_argument("--target", help="Required for explicit numeric versions")
    parser.add_argument("--algorithm", help="Required for explicit numeric versions")
    parser.add_argument(
        "--cache-dir",
        default=os.getenv(
            "MODEL_CACHE_DIR", str(Path(__file__).resolve().parents[1] / "model-cache")
        ),
    )
    return parser.parse_args()


def resolve_models(args: argparse.Namespace) -> list[dict]:
    with registry.connect() as connection:
        if args.version == "latest":
            where = ["m.module = %s", "m.status = 'active'"]
            values: list[object] = [args.module]
            if args.target:
                where.append("m.target = %s")
                values.append(args.target)
            if args.algorithm:
                where.append("m.algorithm = %s")
                values.append(args.algorithm)
            rows = connection.execute(
                f"""
                SELECT m.* FROM active_models a
                JOIN model_versions m ON m.id = a.model_id
                WHERE {' AND '.join(where)}
                ORDER BY m.target, m.algorithm
                """,
                values,
            ).fetchall()
            return rows

        if args.version.isdecimal():
            if not args.target or not args.algorithm:
                raise ValueError("Numeric versions require both --target and --algorithm")
            row = connection.execute(
                """
                SELECT * FROM model_versions
                WHERE module = %s AND target = %s AND algorithm = %s
                  AND version = %s AND approved_at IS NOT NULL
                  AND status IN ('active', 'archived')
                """,
                (args.module, args.target, args.algorithm, int(args.version)),
            ).fetchone()
        else:
            try:
                model_id = UUID(args.version)
            except ValueError as exc:
                raise ValueError("version must be latest, an integer, or a model UUID") from exc
            row = connection.execute(
                """
                SELECT * FROM model_versions
                WHERE id = %s AND module = %s AND approved_at IS NOT NULL
                  AND status IN ('active', 'archived')
                """,
                (model_id, args.module),
            ).fetchone()
        return [row] if row else []


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def sync(args: argparse.Namespace) -> int:
    cache_root = Path(args.cache_dir).expanduser().resolve()
    models = resolve_models(args)
    if not models:
        raise LookupError("No approved model version matched the selection")

    staged: list[tuple[dict, Path, Path, str]] = []
    try:
        for row in models:
            registry.validate_model_artifact(row)
            artifact = registry.download_artifact(row)
            relative_path = Path(
                row["module"], safe_name(row["target"]), row["algorithm"],
                f"v{row['version']}-{row['id']}", "model.joblib",
            )
            destination = cache_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, prefix=".model-", delete=False
            ) as temp_file:
                temp_file.write(artifact)
                temp_path = Path(temp_file.name)
            staged.append((row, temp_path, relative_path, registry.sha256(artifact)))
    except Exception:
        for _, temp_path, _, _ in staged:
            if temp_path.exists():
                temp_path.unlink()
        raise

    pointer_path = cache_root / "active.json"
    cache_root.mkdir(parents=True, exist_ok=True)
    try:
        if pointer_path.exists():
            pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        else:
            pointer = {}
        module_pointer = dict(pointer.get(args.module, {}))

        for row, temp_path, relative_path, digest in staged:
            destination = cache_root / relative_path
            os.replace(temp_path, destination)
            key = f"{row['target']}:{row['algorithm']}"
            module_pointer[key] = {
                "path": relative_path.as_posix(),
                "checksum": digest,
                "model_id": str(row["id"]),
                "version": row["version"],
                "schema_version": row["schema_version"],
            }
        pointer[args.module] = module_pointer
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=cache_root,
            prefix=".active-", delete=False,
        ) as temp_file:
            json.dump(pointer, temp_file, indent=2)
            temp_file.flush()
            os.fsync(temp_file.fileno())
            temp_manifest = Path(temp_file.name)
        os.replace(temp_manifest, pointer_path)
    finally:
        for _, temp_path, _, _ in staged:
            if temp_path.exists():
                temp_path.unlink()

    for row in models:
        print(
            f"Synced {row['module']} / {row['target']} / {row['algorithm']} "
            f"v{row['version']} ({row['id']})"
        )
    print(f"Active local cache: {pointer_path}")
    return 0


def main() -> int:
    args = parse_args()
    try:
        return sync(args)
    except (LookupError, ValueError, RuntimeError) as exc:
        print(f"Model synchronization failed: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Model synchronization failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
