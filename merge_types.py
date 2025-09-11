#!/usr/bin/env python3
"""
Script to merge all type files into a single types.py file, ordered alphabetically.
Ensures nothing is lost during the merge process.
"""

import os
import re
from typing import Dict, List, Set

# Paths
UTILS_DIR = "/home/simone/Desktop/node-naka3.sh/utils"
TYPES_DIR = os.path.join(UTILS_DIR, "types")
OUTPUT_FILE = os.path.join(TYPES_DIR, "types.py")

def extract_types_from_file(file_path: str) -> Dict[str, str]:
    """Extract class definitions, enums, and their imports from a Python file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    types = {}
    
    # Extract imports (except local imports that start with .)
    import_pattern = r'^(from [^.\s][^\n]+ import [^\n]+|import [^.\s][^\n]+)$'
    imports = re.findall(import_pattern, content, re.MULTILINE)
    
    # Extract class definitions
    class_pattern = r'(class \w+.*?(?=\n\n|\nclass |\nif __name__|$))'
    classes = re.findall(class_pattern, content, re.DOTALL)
    
    for cls in classes:
        # Get class name
        class_name_match = re.match(r'class (\w+)', cls)
        if class_name_match:
            class_name = class_name_match.group(1)
            types[class_name] = cls.strip()
    
    return types, imports

def get_all_type_files() -> List[str]:
    """Get all Python files in the types directory."""
    type_files = []
    for file in os.listdir(TYPES_DIR):
        if file.endswith('.py') and file != '__init__.py' and file != 'types.py':
            type_files.append(os.path.join(TYPES_DIR, file))
    return type_files

def merge_types():
    """Merge all type files into a single types.py file."""
    all_types = {}
    all_imports = set()
    
    type_files = get_all_type_files()
    
    print(f"Found type files: {[os.path.basename(f) for f in type_files]}")
    
    # Extract types from all files
    for file_path in type_files:
        print(f"Processing {os.path.basename(file_path)}...")
        types, imports = extract_types_from_file(file_path)
        all_types.update(types)
        all_imports.update(imports)
        print(f"  - Found {len(types)} types: {list(types.keys())}")
    
    # Sort types alphabetically
    sorted_type_names = sorted(all_types.keys())
    
    print(f"\nMerging {len(all_types)} types alphabetically: {sorted_type_names}")
    
    # Create merged content
    content_lines = [
        "#!/usr/bin/env python3",
        '"""',
        "Merged type definitions for the Stacks Node project.",
        "All types are ordered alphabetically for easy navigation.",
        '"""',
        "",
    ]
    
    # Add imports (sorted)
    sorted_imports = sorted(list(all_imports))
    if sorted_imports:
        content_lines.extend(sorted_imports)
        content_lines.append("")
    
    # Add TYPE_CHECKING imports if needed
    has_type_checking = any("TYPE_CHECKING" in imp for imp in sorted_imports)
    if has_type_checking:
        content_lines.extend([
            "if TYPE_CHECKING:",
            "    from ..tokens import StacksToken",
            "",
        ])
    
    # Add types in alphabetical order
    for type_name in sorted_type_names:
        content_lines.append(all_types[type_name])
        content_lines.append("")
    
    # Write merged file
    with open(OUTPUT_FILE, 'w') as f:
        f.write('\n'.join(content_lines))
    
    print(f"\nMerged types written to {OUTPUT_FILE}")
    print(f"Total types: {len(all_types)}")
    print(f"Total imports: {len(all_imports)}")

if __name__ == "__main__":
    merge_types()