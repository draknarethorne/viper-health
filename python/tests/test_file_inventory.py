from pathlib import Path

from viper_health.collectors.file_inventory import scan_file_inventory


def _write_file(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def test_scan_file_inventory_counts_files_and_tiny_files(tmp_path: Path) -> None:
    _write_file(tmp_path / "a" / "small-1.bin", 10)
    _write_file(tmp_path / "a" / "small-2.bin", 4096)
    _write_file(tmp_path / "a" / "large.bin", 5000)
    _write_file(tmp_path / "b" / "small-3.bin", 1)

    result = scan_file_inventory(tmp_path, tiny_file_max_bytes=4096)

    assert result.total_files == 4
    assert result.tiny_files == 3
    assert result.total_bytes == 10 + 4096 + 5000 + 1
    assert result.directories_scanned >= 3

    a_dir = str((tmp_path / "a").resolve())
    b_dir = str((tmp_path / "b").resolve())

    assert result.per_directory[a_dir].total_files == 3
    assert result.per_directory[a_dir].tiny_files == 2
    assert result.per_directory[b_dir].total_files == 1
    assert result.per_directory[b_dir].tiny_files == 1


def test_scan_file_inventory_raises_for_missing_root(tmp_path: Path) -> None:
    missing = tmp_path / "missing"

    try:
        scan_file_inventory(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_scan_file_inventory_prunes_literal_exclude(tmp_path: Path) -> None:
    _write_file(tmp_path / "keep" / "a.bin", 10)
    _write_file(tmp_path / "skip" / "b.bin", 10)
    _write_file(tmp_path / "skip" / "nested" / "c.bin", 10)

    excluded = tmp_path / "skip"
    result = scan_file_inventory(tmp_path, exclude_paths=[excluded])

    assert result.total_files == 1
    keep_dir = str((tmp_path / "keep").resolve())
    assert keep_dir in result.per_directory
    # Excluded directory and its descendants must not be traversed.
    assert not any("skip" in Path(d).parts for d in result.per_directory)


def test_scan_file_inventory_prunes_glob_exclude(tmp_path: Path) -> None:
    _write_file(tmp_path / "app" / "data" / "keep.bin", 10)
    _write_file(tmp_path / "app" / "cache" / "drop.bin", 10)

    result = scan_file_inventory(tmp_path, exclude_paths=[str(tmp_path / "*" / "cache")])

    assert result.total_files == 1
    assert not any("cache" in Path(d).parts for d in result.per_directory)

