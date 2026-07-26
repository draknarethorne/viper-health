"""Tests for the lean filesystem tree counter."""

from pathlib import Path

from viper_health.utils.fs_counter import (
    TreeCount,
    bytes_to_gib,
    bytes_to_mib,
    count_tree,
    format_bytes,
)


def test_count_tree_empty_dir(tmp_path: Path):
    result = count_tree(tmp_path)
    assert result.file_count == 0
    assert result.total_bytes == 0
    assert result.tiny_files == 0
    assert result.errors == 0


def test_count_tree_missing_root(tmp_path: Path):
    missing = tmp_path / "does_not_exist"
    result = count_tree(missing)
    assert result.file_count == 0
    assert result.errors == 1


def test_count_tree_counts_files_and_tiny(tmp_path: Path):
    # Tiny file (<= 4096)
    (tmp_path / "small.txt").write_bytes(b"x" * 100)
    # Large file (> 4096)
    (tmp_path / "big.bin").write_bytes(b"y" * 8192)

    result = count_tree(tmp_path)
    assert result.file_count == 2
    assert result.total_bytes == 100 + 8192
    assert result.tiny_files == 1


def test_count_tree_nested(tmp_path: Path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    (sub / "f1").write_bytes(b"z" * 10)
    (tmp_path / "a" / "f2").write_bytes(b"z" * 20)

    result = count_tree(tmp_path)
    assert result.file_count == 2
    assert result.tiny_files == 2
    assert result.directories >= 3  # root, a, a/b


def test_count_tree_single_file(tmp_path: Path):
    f = tmp_path / "solo.txt"
    f.write_bytes(b"a" * 50)
    result = count_tree(f)
    assert result.file_count == 1
    assert result.tiny_files == 1
    assert result.total_bytes == 50


def test_byte_converters():
    assert bytes_to_gib(1024**3) == 1.0
    assert bytes_to_mib(1024**2) == 1.0


def test_format_bytes_auto_scales_with_gb_mb_tb_labels():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(5 * 1024**2) == "5.0 MB"
    assert format_bytes(2 * 1024**3) == "2.00 GB"
    assert format_bytes(3 * 1024**4) == "3.00 TB"
    # Never uses the binary "iB" labels.
    assert "iB" not in format_bytes(4 * 1024**3)


def test_format_bytes_handles_negative():
    assert format_bytes(-2 * 1024**2) == "-2.0 MB"

