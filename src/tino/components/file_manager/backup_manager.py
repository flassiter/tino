"""
Backup Manager for file backup operations.

Handles creation and management of .tino.bak files with atomic operations
and single-backup-per-file policy.
"""

import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages backup files for the editor.

    Creates .tino.bak files on first modification of a file and manages
    their lifecycle. Only one backup per original file is maintained.
    """

    def __init__(self) -> None:
        """Initialize the backup manager."""
        self._backed_up_files: set[Path] = set()

    def needs_backup(self, file_path: Path) -> bool:
        """
        Check if a file needs to be backed up.

        Args:
            file_path: Path to the original file

        Returns:
            True if backup is needed, False otherwise
        """
        if not file_path.exists():
            return False

        # Check if we've already backed up this file in this session
        if file_path in self._backed_up_files:
            return False

        # Check if backup already exists
        backup_path = self.get_backup_path(file_path)
        return not backup_path.exists()

    def get_backup_path(self, file_path: Path) -> Path:
        """
        Get the backup file path for a given original file.

        Args:
            file_path: Path to the original file

        Returns:
            Path where the backup would be stored
        """
        return file_path.with_suffix(file_path.suffix + ".tino.bak")

    def create_backup(self, file_path: Path) -> Path | None:
        """
        Create a backup of the specified file.

        Uses atomic operations to ensure backup integrity. Only creates
        backup if one doesn't already exist and we haven't backed up
        this file in the current session.

        Args:
            file_path: Path to the file to backup

        Returns:
            Path to the backup file if created, None otherwise

        Raises:
            PermissionError: If backup cannot be created due to permissions
            OSError: If backup creation fails due to I/O error
        """
        if not self.needs_backup(file_path):
            logger.debug(f"Backup not needed for {file_path}")
            return None

        backup_path = self.get_backup_path(file_path)

        try:
            # Use atomic copy operation
            with tempfile.NamedTemporaryFile(
                dir=file_path.parent,
                prefix=f".tino_backup_{file_path.name}_",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            # Copy the file content atomically
            shutil.copy2(file_path, temp_path)

            # Atomically move to final backup location
            temp_path.replace(backup_path)

            # Mark as backed up in this session
            self._backed_up_files.add(file_path)

            logger.info(f"Created backup: {backup_path}")
            return backup_path

        except PermissionError as e:
            logger.error(f"Permission denied creating backup for {file_path}: {e}")
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

        except OSError as e:
            logger.error(f"I/O error creating backup for {file_path}: {e}")
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

    def restore_from_backup(self, file_path: Path) -> bool:
        """
        Restore a file from its backup.

        Args:
            file_path: Path to the original file to restore

        Returns:
            True if restore was successful, False otherwise

        Raises:
            FileNotFoundError: If backup file doesn't exist
            PermissionError: If restore cannot be completed due to permissions
            OSError: If restore fails due to I/O error
        """
        backup_path = self.get_backup_path(file_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            # Use atomic copy operation
            with tempfile.NamedTemporaryFile(
                dir=file_path.parent,
                prefix=f".tino_restore_{file_path.name}_",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)

            # Copy backup content to temp file
            shutil.copy2(backup_path, temp_path)

            # Atomically replace original file
            temp_path.replace(file_path)

            # Remove from backed up set since we've restored
            self._backed_up_files.discard(file_path)

            logger.info(f"Restored file from backup: {file_path}")
            return True

        except (PermissionError, OSError) as e:
            logger.error(f"Error restoring {file_path} from backup: {e}")
            # Clean up temp file if it exists
            if "temp_path" in locals() and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

    def delete_backup(self, file_path: Path) -> bool:
        """
        Delete the backup file for a given original file.

        Args:
            file_path: Path to the original file

        Returns:
            True if backup was deleted, False if no backup existed
        """
        backup_path = self.get_backup_path(file_path)

        if not backup_path.exists():
            return False

        try:
            backup_path.unlink()
            self._backed_up_files.discard(file_path)
            logger.info(f"Deleted backup: {backup_path}")
            return True

        except OSError as e:
            logger.error(f"Error deleting backup {backup_path}: {e}")
            return False

    def cleanup_old_backups(self, directory: Path, max_age_days: int = 30) -> int:
        """
        Clean up old backup files in a directory.

        Args:
            directory: Directory to clean up
            max_age_days: Maximum age of backup files to keep

        Returns:
            Number of backup files deleted
        """
        import time

        if not directory.exists() or not directory.is_dir():
            return 0

        deleted_count = 0
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)

        try:
            for backup_file in directory.glob("*.tino.bak"):
                try:
                    if backup_file.stat().st_mtime < cutoff_time:
                        backup_file.unlink()
                        deleted_count += 1
                        logger.debug(f"Cleaned up old backup: {backup_file}")
                except OSError as e:
                    logger.error(f"Error cleaning up {backup_file}: {e}")

        except OSError as e:
            logger.error(f"Error accessing directory {directory}: {e}")

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backup files in {directory}")

        return deleted_count

    def get_backup_info(self, file_path: Path) -> dict | None:
        """
        Get information about a backup file.

        Args:
            file_path: Path to the original file

        Returns:
            Dictionary with backup info, None if no backup exists
        """
        backup_path = self.get_backup_path(file_path)

        if not backup_path.exists():
            return None

        try:
            stat_info = backup_path.stat()
            return {
                "path": backup_path,
                "size": stat_info.st_size,
                "modified": stat_info.st_mtime,
                "exists": True,
            }
        except OSError:
            return None

    def list_backups(self, directory: Path) -> list[Path]:
        """
        List all backup files in a directory.

        Args:
            directory: Directory to search for backups

        Returns:
            List of backup file paths
        """
        if not directory.exists() or not directory.is_dir():
            return []

        try:
            return list(directory.glob("*.tino.bak"))
        except OSError:
            return []
