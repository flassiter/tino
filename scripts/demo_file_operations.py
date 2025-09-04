#!/usr/bin/env python3
"""
Demonstration script showcasing FileManager features.

This script provides a simple, non-interactive demonstration of all
FileManager capabilities with clear output and examples.
"""

import sys
import time
from pathlib import Path
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tino.components.file_manager import FileManager
from tino.core.events.bus import EventBus


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print(f"{'='*60}")


def print_step(step_num, description):
    """Print a formatted step."""
    print(f"\n{step_num}. {description}")
    print("-" * 40)


def demo_basic_file_operations(manager, temp_dir):
    """Demonstrate basic file operations."""
    print_section("BASIC FILE OPERATIONS")
    
    # Create a test file
    test_file = temp_dir / "demo.txt"
    content = """Hello, Tino FileManager!

This is a demonstration file showing:
- Multi-line content
- UTF-8 encoding support
- Atomic save operations

Created by demo script.
"""
    
    print_step(1, "Saving a new file")
    success = manager.save_file(test_file, content)
    print(f"✅ File saved: {success}")
    print(f"📁 File path: {test_file}")
    print(f"📏 File size: {test_file.stat().st_size} bytes")
    
    print_step(2, "Reading the file back")
    loaded_content = manager.open_file(test_file)
    print(f"✅ Content loaded: {len(loaded_content)} characters")
    print(f"🔍 Content matches: {loaded_content == content}")
    
    print_step(3, "Getting file information")
    size, modified, encoding = manager.get_file_info(test_file)
    print(f"📊 Size: {size} bytes")
    print(f"📅 Modified: {time.ctime(modified)}")
    print(f"🔤 Encoding: {encoding}")
    
    print_step(4, "Checking file properties")
    print(f"📄 File exists: {manager.file_exists(test_file)}")
    print(f"🔍 Is binary: {manager.is_binary_file(test_file)}")
    
    return test_file


def demo_backup_functionality(manager, temp_dir):
    """Demonstrate backup creation and management."""
    print_section("BACKUP FUNCTIONALITY")
    
    # Create original file
    backup_file = temp_dir / "backup_demo.txt"
    original_content = "Original content for backup demonstration.\nThis will be preserved in backup."
    backup_file.write_text(original_content)
    
    print_step(1, "Creating original file externally")
    print(f"📁 File: {backup_file.name}")
    print(f"📝 Content: {len(original_content)} characters")
    
    print_step(2, "First save through FileManager (creates backup)")
    modified_content = "MODIFIED CONTENT!\nThis replaces the original content.\nBackup should preserve original."
    success = manager.save_file(backup_file, modified_content)
    print(f"✅ Save successful: {success}")
    
    # Check backup
    backup_path = backup_file.with_suffix(backup_file.suffix + '.tino.bak')
    print(f"💾 Backup created: {backup_path.exists()}")
    print(f"📁 Backup path: {backup_path.name}")
    
    if backup_path.exists():
        backup_content = backup_path.read_text()
        print(f"🔍 Backup preserves original: {backup_content == original_content}")
        print(f"📏 Backup size: {backup_path.stat().st_size} bytes")
    
    print_step(3, "Second save (no new backup created)")
    second_content = "Second modification.\nBackup should still have original content."
    manager.save_file(backup_file, second_content)
    
    if backup_path.exists():
        backup_content = backup_path.read_text()
        print(f"🔍 Backup still has original: {backup_content == original_content}")
    
    print_step(4, "Backup information")
    backup_info = manager.backup_manager.get_backup_info(backup_file)
    if backup_info:
        print(f"📊 Backup size: {backup_info['size']} bytes")
        print(f"📅 Backup exists: {backup_info['exists']}")
        print(f"📁 Backup path: {backup_info['path'].name}")
    
    print_step(5, "Backup restoration")
    try:
        restore_success = manager.backup_manager.restore_from_backup(backup_file)
        print(f"✅ Restore successful: {restore_success}")
        
        if restore_success:
            restored_content = backup_file.read_text()
            print(f"🔍 Content restored to original: {restored_content == original_content}")
    except Exception as e:
        print(f"❌ Restore failed: {e}")
    
    return backup_file


def demo_recent_files(manager, temp_dir):
    """Demonstrate recent files tracking."""
    print_section("RECENT FILES TRACKING")
    
    # Create multiple test files
    test_files = []
    for i in range(5):
        filename = f"recent_file_{i+1}.txt"
        file_path = temp_dir / filename
        content = f"This is recent file #{i+1}\nCreated for demonstration.\nFile: {filename}"
        file_path.write_text(content)
        test_files.append(file_path)
    
    print_step(1, "Opening multiple files in sequence")
    for file_path in test_files:
        print(f"📖 Opening: {file_path.name}")
        manager.open_file(file_path)
        time.sleep(0.001)  # Ensure different timestamps
    
    print_step(2, "Recent files list (most recent first)")
    recent = manager.get_recent_files()
    print(f"📋 Total recent files: {len(recent)}")
    for i, file_path in enumerate(recent, 1):
        print(f"  {i}. {file_path.name}")
    
    print_step(3, "Last file functionality (Ctrl+Tab simulation)")
    last_file = manager.get_last_file()
    if last_file:
        print(f"⏮️ Last file: {last_file.name}")
        print(f"🔍 This would be opened with Ctrl+Tab")
    else:
        print("⏮️ No last file available")
    
    print_step(4, "File switching simulation")
    if len(recent) >= 2:
        # Open second file to change order
        switch_file = recent[1]
        print(f"🔄 Switching to: {switch_file.name}")
        manager.open_file(switch_file)
        
        # Show updated order
        updated_recent = manager.get_recent_files()
        print(f"📋 Updated order:")
        for i, file_path in enumerate(updated_recent, 1):
            print(f"  {i}. {file_path.name}")
        
        updated_last = manager.get_last_file()
        if updated_last:
            print(f"⏮️ New last file: {updated_last.name}")
    
    print_step(5, "Recent files with limit")
    limited = manager.get_recent_files(limit=3)
    print(f"📋 Recent files (limit 3): {len(limited)}")
    for i, file_path in enumerate(limited, 1):
        print(f"  {i}. {file_path.name}")
    
    return test_files


def demo_cursor_memory(manager, temp_dir):
    """Demonstrate cursor position memory."""
    print_section("CURSOR POSITION MEMORY")
    
    # Test files with different cursor positions
    cursor_tests = [
        ("cursor_test_1.txt", (0, 0), "Start of file"),
        ("cursor_test_2.txt", (5, 10), "Middle position"),
        ("cursor_test_3.txt", (15, 25), "Further down"),
    ]
    
    print_step(1, "Creating files and setting cursor positions")
    for filename, position, description in cursor_tests:
        file_path = temp_dir / filename
        # Create file with enough content for cursor positions
        content = "\n".join([f"Line {i+1}: This is content for cursor testing." for i in range(20)])
        file_path.write_text(content)
        
        print(f"🖱️ {filename}: {description} - Line {position[0]}, Column {position[1]}")
        manager.set_cursor_position(file_path, position[0], position[1])
    
    print_step(2, "Retrieving stored cursor positions")
    for filename, expected_position, description in cursor_tests:
        file_path = temp_dir / filename
        stored_position = manager.get_cursor_position(file_path)
        
        if stored_position:
            print(f"✅ {filename}: Line {stored_position[0]}, Column {stored_position[1]}")
            match = stored_position == expected_position
            print(f"   🔍 Position matches: {match}")
        else:
            print(f"❌ {filename}: No position stored")
    
    print_step(3, "Cursor memory statistics")
    stats = manager.cursor_memory.get_stats()
    print(f"📊 Total files tracked: {stats['total_files']}")
    if stats['max_line'] is not None:
        print(f"📊 Highest line number: {stats['max_line']}")
        print(f"📊 Highest column number: {stats['max_column']}")
        print(f"📊 Average line: {stats['avg_line']:.1f}")
        print(f"📊 Average column: {stats['avg_column']:.1f}")
    
    print_step(4, "Cursor position updates")
    test_file = temp_dir / cursor_tests[0][0]
    original_pos = manager.get_cursor_position(test_file)
    print(f"🖱️ Original position: {original_pos}")
    
    # Update position
    new_position = manager.cursor_memory.update_cursor_position(test_file, 3, -2)
    print(f"🔄 Updated position (+3 lines, -2 columns): {new_position}")


def demo_encoding_detection(manager, temp_dir):
    """Demonstrate encoding detection capabilities."""
    print_section("ENCODING DETECTION")
    
    # Test different encodings
    encoding_tests = [
        ("utf8_test.txt", "UTF-8 content with unicode: café, naïve, 世界, 🎉", 'utf-8'),
        ("ascii_test.txt", "Simple ASCII content without special characters", 'ascii'),
        ("latin1_test.txt", "Latin-1 content: café, naïve, résumé", 'latin-1'),
    ]
    
    print_step(1, "Creating files with different encodings")
    for filename, content, encoding in encoding_tests:
        file_path = temp_dir / filename
        
        try:
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
            print(f"✅ Created {filename} with {encoding} encoding")
        except UnicodeEncodeError:
            # Fallback for problematic encodings
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"⚠️ Created {filename} with UTF-8 (fallback)")
    
    print_step(2, "Detecting file encodings")
    for filename, content, expected_encoding in encoding_tests:
        file_path = temp_dir / filename
        
        if file_path.exists():
            try:
                detected = manager.get_encoding(file_path)
                print(f"🔤 {filename}:")
                print(f"   Expected: {expected_encoding}")
                print(f"   Detected: {detected}")
                
                # Check if compatible
                compatible = (detected.lower() == expected_encoding.lower() or 
                            (expected_encoding == 'ascii' and detected.lower() == 'utf-8'))
                print(f"   Compatible: {compatible}")
                
            except Exception as e:
                print(f"❌ Failed to detect encoding for {filename}: {e}")
    
    print_step(3, "Binary file detection")
    # Create a binary file
    binary_file = temp_dir / "binary_test.bin"
    binary_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100  # PNG signature + null bytes
    binary_file.write_bytes(binary_data)
    
    is_binary = manager.is_binary_file(binary_file)
    print(f"🔍 Binary file detection: {is_binary}")
    print(f"📁 File: {binary_file.name}")
    print(f"📏 Size: {len(binary_data)} bytes")
    
    # Try to open binary file (should fail)
    try:
        manager.open_file(binary_file)
        print("❌ Binary file opened successfully (unexpected)")
    except ValueError as e:
        print(f"✅ Binary file rejected: {e}")


def demo_file_validation(manager, temp_dir):
    """Demonstrate file path validation."""
    print_section("FILE PATH VALIDATION")
    
    validation_tests = [
        (temp_dir / "valid_test.txt", "Valid file in temp directory"),
        (temp_dir / "subdir" / "nested.txt", "File in subdirectory (parent needs creation)"),
        (Path("/nonexistent/directory/file.txt"), "File with non-existent parent"),
    ]
    
    print_step(1, "Testing various file paths")
    for test_path, description in validation_tests:
        print(f"\n🔍 {description}:")
        print(f"   Path: {test_path}")
        
        is_valid, error = manager.validate_file_path(test_path)
        print(f"   Valid: {is_valid}")
        if error:
            print(f"   Error: {error}")
        
        # Create parent directory if needed for demonstration
        if not is_valid and "does not exist" in error.lower() and test_path.parent != Path("/nonexistent/directory"):
            try:
                test_path.parent.mkdir(parents=True, exist_ok=True)
                print(f"   📁 Created parent directory: {test_path.parent}")
                
                # Re-validate
                is_valid_after, error_after = manager.validate_file_path(test_path)
                print(f"   Valid after parent creation: {is_valid_after}")
            except Exception as e:
                print(f"   ❌ Failed to create parent: {e}")
    
    print_step(2, "Temporary file path generation")
    test_files = [
        temp_dir / "original.txt",
        temp_dir / "file with spaces.txt",
        temp_dir / "file.with.dots.txt",
    ]
    
    for test_file in test_files:
        temp_path = manager.get_temp_file_path(test_file)
        print(f"\n📄 Original: {test_file.name}")
        print(f"🔄 Temp path: {temp_path.name}")
        print(f"📁 Same directory: {temp_path.parent == test_file.parent}")
        print(f"✅ Valid temp path: {'.tino_temp_' in str(temp_path) and temp_path.suffix == '.tmp'}")


def demo_manager_statistics(manager, temp_dir):
    """Show comprehensive manager statistics."""
    print_section("MANAGER STATISTICS")
    
    stats = manager.get_manager_stats()
    
    print_step(1, "Recent Files Statistics")
    rf_stats = stats['recent_files']
    print(f"📂 Total files: {rf_stats['total_files']}")
    print(f"📂 Maximum capacity: {rf_stats['max_files']}")
    print(f"📂 Has last file: {rf_stats['has_last_file']}")
    if rf_stats['has_last_file']:
        print(f"📂 Last file: {rf_stats.get('last_file', 'N/A')}")
    
    print_step(2, "Cursor Memory Statistics")
    cm_stats = stats['cursor_memory']
    print(f"🖱️ Files tracked: {cm_stats['total_files']}")
    if cm_stats['total_files'] > 0:
        print(f"🖱️ Highest line: {cm_stats['max_line']}")
        print(f"🖱️ Highest column: {cm_stats['max_column']}")
        print(f"🖱️ Average line: {cm_stats['avg_line']:.1f}")
        print(f"🖱️ Average column: {cm_stats['avg_column']:.1f}")
    
    print_step(3, "Backup Statistics")
    backup_stats = stats['backup_info']
    print(f"💾 Files backed up this session: {backup_stats['backed_up_files']}")
    
    # List all backup files in temp directory
    backup_files = manager.backup_manager.list_backups(temp_dir)
    print(f"💾 Backup files found: {len(backup_files)}")
    for backup in backup_files:
        print(f"   📁 {backup.name}")


def main():
    """Run the complete demonstration."""
    print("🎯 TINO FILEMANAGER DEMONSTRATION")
    print("This script demonstrates all FileManager capabilities")
    print(f"⏰ Started at: {time.ctime()}")
    
    # Create temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="tino_file_demo_"))
    print(f"📂 Working directory: {temp_dir}")
    
    try:
        # Initialize FileManager with event bus
        event_bus = EventBus()
        manager = FileManager(event_bus=event_bus)
        
        # Track events
        events_received = []
        def track_events(event):
            events_received.append(event)
            print(f"📢 Event: {type(event).__name__} - {event.file_path.name if hasattr(event, 'file_path') else 'N/A'}")
        
        from tino.core.events.types import FileOpenedEvent, FileSavedEvent
        event_bus.subscribe(FileOpenedEvent, track_events)
        event_bus.subscribe(FileSavedEvent, track_events)
        
        # Run demonstrations
        print("\n🏁 Starting demonstrations...")
        
        demo_basic_file_operations(manager, temp_dir)
        demo_backup_functionality(manager, temp_dir)
        demo_recent_files(manager, temp_dir)
        demo_cursor_memory(manager, temp_dir)
        demo_encoding_detection(manager, temp_dir)
        demo_file_validation(manager, temp_dir)
        demo_manager_statistics(manager, temp_dir)
        
        # Event summary
        print_section("EVENT SUMMARY")
        print(f"📊 Total events captured: {len(events_received)}")
        for i, event in enumerate(events_received, 1):
            event_type = type(event).__name__
            print(f"  {i}. {event_type}")
        
        # Cleanup demonstration
        print_section("CLEANUP")
        cleaned_temps = manager.cleanup_temp_files()
        print(f"🧹 Temporary files cleaned: {cleaned_temps}")
        
        print(f"\n🎉 Demonstration completed successfully!")
        print(f"📊 Files created: {len(list(temp_dir.glob('*')))}")
        print(f"💾 Backup files: {len(list(temp_dir.glob('*.tino.bak')))}")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Cleanup temp directory
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
            print(f"🧹 Cleaned up: {temp_dir}")
    
    print("\n👋 Thank you for exploring Tino FileManager!")
    return 0


if __name__ == '__main__':
    sys.exit(main())