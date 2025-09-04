#!/usr/bin/env python3
"""
CLI tool for testing and demonstrating FileManager functionality.

This script provides an interactive interface to test all FileManager
features including file operations, backups, recent files, and cursor memory.
"""

import argparse
import sys
from pathlib import Path
import tempfile
import shutil
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tino.components.file_manager import FileManager, MockFileManager
from tino.core.events.bus import EventBus
from tino.core.events.types import FileOpenedEvent, FileSavedEvent


class FileManagerDemo:
    """Interactive demonstration of FileManager functionality."""
    
    def __init__(self, use_mock: bool = False, temp_dir: Optional[Path] = None):
        """
        Initialize the demo.
        
        Args:
            use_mock: Use MockFileManager instead of real FileManager
            temp_dir: Temporary directory for testing (created if None)
        """
        self.event_bus = EventBus()
        
        if use_mock:
            self.manager = MockFileManager(event_bus=self.event_bus)
            print("🔧 Using MockFileManager for demonstration")
        else:
            self.manager = FileManager(event_bus=self.event_bus)
            print("📁 Using real FileManager for demonstration")
        
        # Set up temporary directory
        if temp_dir:
            self.temp_dir = temp_dir
            self.cleanup_temp = False
        else:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="tino_demo_"))
            self.cleanup_temp = True
        
        print(f"📂 Working directory: {self.temp_dir}")
        
        # Track events
        self.events_received = []
        self.event_bus.subscribe(FileOpenedEvent, self._on_file_event)
        self.event_bus.subscribe(FileSavedEvent, self._on_file_event)
        
        # Pre-populate some test files for mock
        if use_mock:
            self._setup_mock_files()
    
    def _on_file_event(self, event):
        """Handle file events for demonstration."""
        self.events_received.append(event)
        event_type = type(event).__name__
        print(f"📢 Event: {event_type} - {event.file_path}")
    
    def _setup_mock_files(self):
        """Set up some mock files for demonstration."""
        test_files = [
            ("demo.txt", "Demo file content\nWith multiple lines\nFor testing"),
            ("readme.md", "# Demo README\n\nThis is a demo markdown file."),
            ("config.json", '{\n  "setting": "value",\n  "demo": true\n}'),
        ]
        
        for filename, content in test_files:
            file_path = self.temp_dir / filename
            self.manager.add_mock_file(file_path, content)
            print(f"📝 Added mock file: {filename}")
    
    def cleanup(self):
        """Clean up temporary resources."""
        if self.cleanup_temp and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up: {self.temp_dir}")
    
    def run_interactive_demo(self):
        """Run interactive demonstration."""
        print("\n" + "="*60)
        print("🎯 TINO FILEMANAGER INTERACTIVE DEMO")
        print("="*60)
        
        while True:
            try:
                self._show_menu()
                choice = input("\nEnter your choice (or 'q' to quit): ").strip().lower()
                
                if choice in ['q', 'quit', 'exit']:
                    break
                elif choice == '1':
                    self._demo_file_operations()
                elif choice == '2':
                    self._demo_backup_operations()
                elif choice == '3':
                    self._demo_recent_files()
                elif choice == '4':
                    self._demo_cursor_memory()
                elif choice == '5':
                    self._demo_encoding_detection()
                elif choice == '6':
                    self._demo_file_validation()
                elif choice == '7':
                    self._show_manager_stats()
                elif choice == '8':
                    self._show_event_history()
                elif choice == 'auto':
                    self._run_automated_demo()
                else:
                    print("❌ Invalid choice. Please try again.")
                
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n\n👋 Demo interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
    
    def _show_menu(self):
        """Display the main menu."""
        print("\n" + "-"*40)
        print("📋 DEMO MENU")
        print("-"*40)
        print("1. File Operations (save/open)")
        print("2. Backup Operations") 
        print("3. Recent Files Management")
        print("4. Cursor Position Memory")
        print("5. Encoding Detection")
        print("6. File Validation")
        print("7. Manager Statistics")
        print("8. Event History")
        print("auto. Run Automated Demo")
        print("q. Quit")
    
    def _demo_file_operations(self):
        """Demonstrate basic file operations."""
        print("\n🔧 FILE OPERATIONS DEMO")
        print("-" * 30)
        
        # Create a test file
        test_file = self.temp_dir / "file_ops_demo.txt"
        content = "Hello, Tino FileManager!\nThis is a test file.\nWith multiple lines."
        
        print(f"📝 Saving file: {test_file.name}")
        success = self.manager.save_file(test_file, content)
        print(f"✅ Save result: {success}")
        
        if not isinstance(self.manager, MockFileManager):
            print(f"📊 File exists: {test_file.exists()}")
            print(f"📏 File size: {test_file.stat().st_size} bytes")
        
        print(f"📖 Opening file: {test_file.name}")
        loaded_content = self.manager.open_file(test_file)
        print(f"✅ Content loaded: {len(loaded_content)} characters")
        print(f"🔍 Content preview: {loaded_content[:50]}...")
        
        # Test file info
        size, modified, encoding = self.manager.get_file_info(test_file)
        print(f"📊 File info - Size: {size}, Encoding: {encoding}")
        
        # Test binary detection
        is_binary = self.manager.is_binary_file(test_file)
        print(f"🔍 Binary file: {is_binary}")
    
    def _demo_backup_operations(self):
        """Demonstrate backup functionality."""
        print("\n💾 BACKUP OPERATIONS DEMO")
        print("-" * 30)
        
        # Create original file
        test_file = self.temp_dir / "backup_demo.txt"
        original_content = "Original content for backup demo\nThis will be backed up"
        
        if isinstance(self.manager, MockFileManager):
            self.manager.add_mock_file(test_file, original_content)
        else:
            test_file.write_text(original_content)
        
        print(f"📝 Created file: {test_file.name}")
        
        # Modify through manager (should create backup)
        new_content = "Modified content\nThis replaces the original\nBackup should exist"
        print(f"🔄 Modifying file through FileManager...")
        self.manager.save_file(test_file, new_content)
        
        # Check backup
        backup_path = self.manager.backup_manager.get_backup_path(test_file)
        print(f"🔍 Backup path: {backup_path.name}")
        
        if isinstance(self.manager, MockFileManager):
            backup_exists = self.manager.file_exists(backup_path)
        else:
            backup_exists = backup_path.exists()
        
        print(f"💾 Backup exists: {backup_exists}")
        
        if backup_exists:
            # Get backup info
            info = self.manager.backup_manager.get_backup_info(test_file)
            if info:
                print(f"📊 Backup size: {info['size']} bytes")
                print(f"📅 Backup created: {info['exists']}")
        
        # Demonstrate restore
        print(f"🔄 Restoring from backup...")
        try:
            success = self.manager.backup_manager.restore_from_backup(test_file)
            print(f"✅ Restore result: {success}")
            
            if success:
                restored_content = self.manager.open_file(test_file)
                print(f"🔍 Restored content matches original: {restored_content == original_content}")
        except Exception as e:
            print(f"❌ Restore failed: {e}")
    
    def _demo_recent_files(self):
        """Demonstrate recent files functionality."""
        print("\n📂 RECENT FILES DEMO")
        print("-" * 30)
        
        # Create and open multiple files
        test_files = ["recent1.txt", "recent2.md", "recent3.py"]
        
        for i, filename in enumerate(test_files):
            file_path = self.temp_dir / filename
            content = f"Content for {filename}\nFile number {i+1}"
            
            if isinstance(self.manager, MockFileManager):
                self.manager.add_mock_file(file_path, content)
            else:
                file_path.write_text(content)
            
            print(f"📖 Opening: {filename}")
            self.manager.open_file(file_path)
        
        # Show recent files
        recent = self.manager.get_recent_files()
        print(f"\n📋 Recent files ({len(recent)} total):")
        for i, file_path in enumerate(recent):
            print(f"  {i+1}. {file_path.name}")
        
        # Show last file (Ctrl+Tab functionality)
        last_file = self.manager.get_last_file()
        if last_file:
            print(f"\n⏮️ Last file (Ctrl+Tab): {last_file.name}")
        else:
            print(f"\n⏮️ No last file available")
        
        # Demonstrate file switching simulation
        if recent:
            print(f"\n🔄 Simulating file switch...")
            # Open the second file to change order
            self.manager.open_file(recent[1])
            
            updated_recent = self.manager.get_recent_files()
            print(f"📋 Updated recent files:")
            for i, file_path in enumerate(updated_recent):
                print(f"  {i+1}. {file_path.name}")
            
            updated_last = self.manager.get_last_file()
            if updated_last:
                print(f"⏮️ New last file: {updated_last.name}")
    
    def _demo_cursor_memory(self):
        """Demonstrate cursor position memory."""
        print("\n🖱️ CURSOR MEMORY DEMO")
        print("-" * 30)
        
        # Create test files and set cursor positions
        cursor_tests = [
            ("cursor1.txt", (5, 10)),
            ("cursor2.md", (15, 25)),
            ("cursor3.py", (0, 0)),
        ]
        
        for filename, position in cursor_tests:
            file_path = self.temp_dir / filename
            content = f"Content for cursor test\n" * 20  # Multiple lines
            
            if isinstance(self.manager, MockFileManager):
                self.manager.add_mock_file(file_path, content)
            else:
                file_path.write_text(content)
            
            print(f"🖱️ Setting cursor for {filename} at {position}")
            self.manager.set_cursor_position(file_path, position[0], position[1])
        
        # Retrieve and display cursor positions
        print(f"\n📋 Stored cursor positions:")
        for filename, expected_position in cursor_tests:
            file_path = self.temp_dir / filename
            stored_position = self.manager.get_cursor_position(file_path)
            
            if stored_position:
                print(f"  {filename}: Line {stored_position[0]}, Col {stored_position[1]}")
                match = stored_position == expected_position
                print(f"    ✅ Match: {match}")
            else:
                print(f"  {filename}: No position stored ❌")
        
        # Test cursor memory stats
        stats = self.manager.cursor_memory.get_stats()
        print(f"\n📊 Cursor Memory Stats:")
        print(f"  Total files: {stats['total_files']}")
        if stats['max_line'] is not None:
            print(f"  Max line: {stats['max_line']}")
            print(f"  Max column: {stats['max_column']}")
    
    def _demo_encoding_detection(self):
        """Demonstrate encoding detection."""
        print("\n🔤 ENCODING DETECTION DEMO")
        print("-" * 30)
        
        # Test different encodings
        encoding_tests = [
            ("utf8_test.txt", "UTF-8 content with émojis 🎉", 'utf-8'),
            ("ascii_test.txt", "Simple ASCII content", 'ascii'),
        ]
        
        for filename, content, encoding in encoding_tests:
            file_path = self.temp_dir / filename
            
            if isinstance(self.manager, MockFileManager):
                self.manager.add_mock_file(file_path, content, encoding)
                detected = encoding  # Mock returns what we set
            else:
                # Write with specific encoding
                with open(file_path, 'w', encoding=encoding) as f:
                    f.write(content)
                detected = self.manager.get_encoding(file_path)
            
            print(f"📄 File: {filename}")
            print(f"  Expected encoding: {encoding}")
            print(f"  Detected encoding: {detected}")
            print(f"  ✅ Match: {detected.lower() in [encoding.lower(), 'utf-8']}")  # utf-8 compatible with ascii
        
        # Test binary detection
        if not isinstance(self.manager, MockFileManager):
            binary_file = self.temp_dir / "binary_test.bin"
            binary_file.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00' * 50)
            
            is_binary = self.manager.is_binary_file(binary_file)
            print(f"\n🔍 Binary detection:")
            print(f"  File: {binary_file.name}")
            print(f"  Detected as binary: {is_binary}")
    
    def _demo_file_validation(self):
        """Demonstrate file path validation."""
        print("\n✅ FILE VALIDATION DEMO")
        print("-" * 30)
        
        # Test various paths
        validation_tests = [
            (self.temp_dir / "valid_file.txt", "Valid file path"),
            (Path("/nonexistent/invalid/path.txt"), "Invalid parent directory"),
        ]
        
        for test_path, description in validation_tests:
            is_valid, error = self.manager.validate_file_path(test_path)
            
            print(f"📁 {description}:")
            print(f"  Path: {test_path}")
            print(f"  Valid: {is_valid}")
            if error:
                print(f"  Error: {error}")
        
        # Test temp file path generation
        test_file = self.temp_dir / "temp_test.txt"
        temp_path = self.manager.get_temp_file_path(test_file)
        
        print(f"\n🔄 Temp file generation:")
        print(f"  Original: {test_file.name}")
        print(f"  Temp path: {temp_path.name}")
        print(f"  Same directory: {temp_path.parent == test_file.parent}")
    
    def _show_manager_stats(self):
        """Show FileManager statistics."""
        print("\n📊 MANAGER STATISTICS")
        print("-" * 30)
        
        stats = self.manager.get_manager_stats()
        
        print("📂 Recent Files:")
        rf_stats = stats['recent_files']
        print(f"  Total files: {rf_stats['total_files']}")
        print(f"  Max files: {rf_stats['max_files']}")
        print(f"  Has last file: {rf_stats['has_last_file']}")
        
        print("\n🖱️ Cursor Memory:")
        cm_stats = stats['cursor_memory']
        print(f"  Total files: {cm_stats['total_files']}")
        if cm_stats['max_line'] is not None:
            print(f"  Max line: {cm_stats['max_line']}")
            print(f"  Max column: {cm_stats['max_column']}")
        
        print("\n💾 Backup Info:")
        backup_stats = stats['backup_info']
        print(f"  Backed up files: {backup_stats['backed_up_files']}")
        
        # Additional stats for mock
        if isinstance(self.manager, MockFileManager):
            mock_files = self.manager.get_mock_files()
            print(f"\n🔧 Mock Manager:")
            print(f"  Total mock files: {len(mock_files)}")
            
            history = self.manager.get_operation_history()
            print(f"  Operations recorded: {len(history)}")
    
    def _show_event_history(self):
        """Show event history."""
        print("\n📢 EVENT HISTORY")
        print("-" * 30)
        
        if not self.events_received:
            print("No events recorded yet.")
            return
        
        for i, event in enumerate(self.events_received, 1):
            event_type = type(event).__name__
            print(f"{i}. {event_type}")
            print(f"   File: {event.file_path}")
            print(f"   Time: {event.timestamp}")
            if hasattr(event, 'size'):
                print(f"   Size: {event.size}")
            if hasattr(event, 'encoding'):
                print(f"   Encoding: {event.encoding}")
            if hasattr(event, 'backup_created'):
                print(f"   Backup created: {event.backup_created}")
    
    def _run_automated_demo(self):
        """Run automated demonstration of all features."""
        print("\n🤖 AUTOMATED DEMO")
        print("=" * 50)
        
        print("Running comprehensive FileManager demonstration...\n")
        
        # File operations
        print("1️⃣ Testing file operations...")
        self._demo_file_operations()
        
        print("\n2️⃣ Testing backup operations...")
        self._demo_backup_operations()
        
        print("\n3️⃣ Testing recent files...")
        self._demo_recent_files()
        
        print("\n4️⃣ Testing cursor memory...")
        self._demo_cursor_memory()
        
        print("\n5️⃣ Testing encoding detection...")
        self._demo_encoding_detection()
        
        print("\n6️⃣ Testing file validation...")
        self._demo_file_validation()
        
        print("\n📊 Final statistics:")
        self._show_manager_stats()
        
        print("\n🎉 Automated demo completed successfully!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Tino FileManager Demo Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_file_manager.py                    # Interactive demo with real files
  python test_file_manager.py --mock             # Interactive demo with mock files
  python test_file_manager.py --auto             # Automated demo
  python test_file_manager.py --auto --mock      # Automated demo with mock files
        """
    )
    
    parser.add_argument(
        '--mock',
        action='store_true',
        help='Use MockFileManager instead of real FileManager'
    )
    
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Run automated demo instead of interactive'
    )
    
    parser.add_argument(
        '--temp-dir',
        type=Path,
        help='Temporary directory for testing (created if not exists)'
    )
    
    args = parser.parse_args()
    
    # Set up temp directory
    temp_dir = args.temp_dir
    if temp_dir:
        temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and run demo
    demo = FileManagerDemo(use_mock=args.mock, temp_dir=temp_dir)
    
    try:
        if args.auto:
            demo._run_automated_demo()
        else:
            demo.run_interactive_demo()
    
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        demo.cleanup()
    
    print("\n👋 Thanks for testing Tino FileManager!")
    return 0


if __name__ == '__main__':
    sys.exit(main())