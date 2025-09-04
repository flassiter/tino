#!/usr/bin/env python3
"""
Test script to verify scroll synchronization functionality.
"""
import tempfile
from pathlib import Path
import time

# Create a test markdown file with enough content to scroll
test_content = """# Test Document

This is a test document to verify scroll synchronization between the editor and preview panes.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor 
incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis 
nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.

### Subsection 1.1

Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore 
eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident.

## Section 2

Sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut 
perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque 
laudantium.

### Subsection 2.1

Totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi 
architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem.

### Subsection 2.2

Quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni 
dolores eos qui ratione voluptatem sequi nesciunt.

## Section 3

Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, 
adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore.

### Subsection 3.1

Et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis 
nostrum exercitationem ullam corporis suscipit laboriosam.

### Subsection 3.2

Nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure 
reprehenderit qui in ea voluptate velit esse quam nihil molestiae consequatur.

## Section 4

Vel illum qui dolorem eum fugiat quo voluptas nulla pariatur? At vero eos et 
accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium.

### Subsection 4.1

Voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi 
sint occaecati cupiditate non provident, similique sunt in culpa qui officia 
deserunt mollitia animi, id est laborum et dolorum fuga.

### Subsection 4.2

Et harum quidem rerum facilis est et expedita distinctio. Nam libero tempore, 
cum soluta nobis est eligendi optio cumque nihil impedit quo minus id quod 
maxime placeat facere possimus.

## Section 5

Omnis voluptas assumenda est, omnis dolor repellendus. Temporibus autem 
quibusdam et aut officiis debitis aut rerum necessitatibus saepe eveniet ut 
et voluptates repudiandae sint et molestiae non recusandae.

### Final Subsection

This is the end of our test document. If you can see this in the preview 
when scrolling to the bottom of the editor, the scroll synchronization is 
working correctly!
"""

def main():
    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_content)
        temp_file = Path(f.name)
    
    print("Created test file:", temp_file)
    print("\nTo test scroll synchronization:")
    print("1. Run: python -m tino", str(temp_file))
    print("2. Use arrow keys to navigate up and down in the editor")
    print("3. Watch if the preview pane scrolls synchronously")
    print("4. Look for DEBUG messages in the console output")
    print("\nExpected behavior:")
    print("- Moving the cursor should trigger scroll sync events")
    print("- Preview pane should scroll to match editor position")
    print("- DEBUG messages should show cursor movement detection")
    
    # Keep the temp file for manual testing
    print(f"\nTest file will remain at: {temp_file}")
    print("Delete it manually when done testing.")

if __name__ == "__main__":
    main()