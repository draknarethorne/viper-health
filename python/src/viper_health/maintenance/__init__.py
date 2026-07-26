"""Viper Health maintenance (mutation) subpackage.

Everything here can modify the filesystem and is therefore gated by the project
safety model: read-only/dry-run by default, allowlist + immutable-root
enforcement, quarantine-first, manifest generation, and action caps. No module
here performs silent or unbounded deletion.
"""
