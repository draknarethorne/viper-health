"""Progress reporting utilities for long-running scans."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path


class ProgressReporter:
    """Hierarchical progress reporter for console output."""
    
    def __init__(self, *, enabled: bool = True, update_interval: int = 100, root_path: Path | None = None):
        """
        Initialize progress reporter.
        
        Args:
            enabled: Whether to actually print progress
            update_interval: How often to update (every N calls)
            root_path: Root scan path for calculating relative display
        """
        self.enabled = enabled
        self.update_interval = update_interval
        self.root_path = Path(root_path).resolve() if root_path else None
        self.start_time: datetime | None = None
        self.last_update: datetime | None = None
        self.current_top_level: str | None = None
        
    def _get_display_path(self, current_path: str) -> tuple[str, str]:
        """
        Get hierarchical display path.
        
        Returns:
            (top_level_dir, relative_path) for display
        """
        if not self.root_path:
            # Truncate long paths
            if len(current_path) > 60:
                return ("", "..." + current_path[-57:])
            return ("", current_path)
        
        try:
            path = Path(current_path)
            
            # Get path relative to root
            try:
                rel = path.relative_to(self.root_path)
                parts = rel.parts
            except ValueError:
                # Path not under root
                if len(current_path) > 60:
                    return ("", "..." + current_path[-57:])
                return ("", current_path)
            
            if not parts:
                return (str(self.root_path), "")
            
            # Top-level directory under root
            top_level = str(self.root_path / parts[0])
            
            # For deep paths, show top-level + depth indicator
            if len(parts) > 3:
                display = f"{parts[0]}/.../{parts[-1]}"
            elif len(parts) > 1:
                display = "/".join(parts)
            else:
                display = parts[0]
            
            return (top_level, display)
            
        except Exception:
            # Fallback to simple truncation
            if len(current_path) > 60:
                return ("", "..." + current_path[-57:])
            return ("", current_path)
        
    def start(self, message: str = "Scanning...") -> None:
        """Start progress reporting."""
        if not self.enabled:
            return
        self.start_time = datetime.now()
        self.last_update = self.start_time
        print(f"\n🔍 {message}", file=sys.stderr)
        
    def update(self, dirs_scanned: int, files_scanned: int, current_path: str) -> None:
        """
        Report progress update.
        
        Args:
            dirs_scanned: Number of directories processed
            files_scanned: Number of files processed
            current_path: Current directory being scanned
        """
        if not self.enabled:
            return
            
        now = datetime.now()
        
        # Get hierarchical display
        top_level, display_path = self._get_display_path(current_path)
        
        # Track top-level directory changes
        if top_level and top_level != self.current_top_level:
            self.current_top_level = top_level
            # Print newline when moving to a new top-level directory
            if self.start_time and (now - self.start_time).total_seconds() > 1:
                print(file=sys.stderr)
                print(f"  ➜ Scanning: {display_path}", file=sys.stderr)
        
        # Calculate elapsed time
        if self.start_time:
            elapsed = now - self.start_time
            elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
        else:
            elapsed_str = "00:00:00"
        
        # Truncate display path if still too long
        if len(display_path) > 60:
            display_path = "..." + display_path[-57:]
        
        # Print progress (overwrite previous line with \r)
        print(
            f"\r  ⏱️  {elapsed_str} | 📁 {dirs_scanned:,} dirs | 📄 {files_scanned:,} files | {display_path}",
            end='',
            file=sys.stderr,
            flush=True
        )
        self.last_update = now
        
    def finish(self, dirs_scanned: int, files_scanned: int) -> None:
        """
        Finish progress reporting and print final summary.
        
        Args:
            dirs_scanned: Total directories processed
            files_scanned: Total files processed
        """
        if not self.enabled:
            return
            
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            elapsed_str = str(elapsed).split('.')[0]
        else:
            elapsed_str = "00:00:00"
        
        # Clear the progress line and print final stats
        print(
            f"\r  ✅ Completed: 📁 {dirs_scanned:,} directories | 📄 {files_scanned:,} files | ⏱️  {elapsed_str}    ",
            file=sys.stderr
        )
        print(file=sys.stderr)  # Extra newline
