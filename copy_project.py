#!/usr/bin/env python3
import os
import argparse
import pathspec
import pyperclip
import sys
import re
from typing import List, Tuple, Dict, Any, Optional

# --- Configuration ---
DEFAULT_ENCODING = 'utf-8'
READ_ERROR_BEHAVIOR = 'ignore' # or 'replace' or 'strict'
ALWAYS_EXCLUDE = ['.git', "logo.png", "logo_small.png", "loading-animation.svg"] # Directories/files to always exclude
DEFAULT_MAX_SIZE_STR = "1M" # Default max file size

# --- Globals for Verbose Output ---
verbose_print = lambda *a, **k: None # No-op function by default

# --- Helper Functions ---

def parse_size(size_str: str) -> Optional[int]:
    """Parses a human-readable size string (e.g., '1M', '500K', '1024') into bytes."""
    size_str = size_str.strip().upper()
    match = re.match(r'^(\d+(\.\d+)?)\s*([KMGT]?)$', size_str)
    if not match:
        return None
    value_str, _, suffix = match.groups()
    value = float(value_str)
    multiplier = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}.get(suffix, 1)
    return int(value * multiplier)

def read_gitignore(path: str) -> List[str]:
    """Reads .gitignore file and returns a list of patterns found."""
    gitignore_path = os.path.join(path, '.gitignore')
    patterns = []
    if os.path.exists(gitignore_path) and os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding=DEFAULT_ENCODING) as f:
                lines = f.readlines()
            # Clean patterns: remove comments, strip whitespace, ignore empty
            patterns = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
            verbose_print(f"--- Read {len(patterns)} patterns from {gitignore_path} ---")
            # verbose_print(f"--- .gitignore patterns: {patterns} ---") # Uncomment for extreme debug
        except Exception as e:
            print(f"Warning: Could not read .gitignore: {e}", file=sys.stderr)
            patterns = [] # Ensure empty list on error
    else:
        verbose_print(f"--- No .gitignore file found at {gitignore_path} ---")

    return patterns

def get_included_files(root_dir: str, gitignore_patterns: List[str], extra_exclude_patterns: List[str]) -> List[str]:
    """Walks the directory and returns a list of relative paths of included files."""
    included_files = []
    root_dir = os.path.abspath(root_dir)
    script_path_rel = None
    try:
        script_path_abs = os.path.abspath(__file__)
        if script_path_abs.startswith(root_dir):
             script_path_rel = os.path.relpath(script_path_abs, root_dir).replace(os.sep, '/')
             verbose_print(f"--- Will exclude script itself: {script_path_rel} ---")
    except NameError:
        pass # __file__ not defined

    # Combine all patterns: .gitignore + CLI exclude + Always exclude
    all_patterns = []
    all_patterns.extend(gitignore_patterns)
    all_patterns.extend(extra_exclude_patterns)
    # Ensure ALWAYS_EXCLUDE are present (avoid simple duplicates)
    for pattern in ALWAYS_EXCLUDE:
         if pattern not in all_patterns:
              all_patterns.append(pattern)

    # Create ONE PathSpec object from all combined patterns
    combined_spec = pathspec.PathSpec.from_lines('gitwildmatch', all_patterns) if all_patterns else None

    if combined_spec:
         verbose_print(f"--- Using combined ignore patterns ({len(all_patterns)} total): ---")
         for p in all_patterns: verbose_print(f"    - '{p}'")
    else:
         verbose_print("--- No ignore patterns specified or active. ---")

    verbose_print(f"--- Scanning directory: {root_dir} ---")
    for current_root, dirs, files in os.walk(root_dir, topdown=True):
        relative_root = os.path.relpath(current_root, root_dir)
        if relative_root == '.':
            relative_root = '' # Root directory relative path is empty

        # --- Filter directories ---
        dirs_original = list(dirs) # Copy for iteration while modifying dirs
        dirs[:] = [] # Clear dirs in-place, we will re-add included ones

        for d in dirs_original:
            dir_rel_path = os.path.join(relative_root, d).replace(os.sep, '/')
            is_ignored = False
            if combined_spec:
                # Check both 'dir_name' and 'dir_name/' for gitignore compatibility
                match_norm = combined_spec.match_file(dir_rel_path)
                match_dir = combined_spec.match_file(dir_rel_path + '/')
                if match_norm or match_dir:
                    is_ignored = True
                    verbose_print(f"--- Ignoring directory '{dir_rel_path}' (Match: norm={match_norm}, dir={match_dir}) ---")

            if not is_ignored:
                verbose_print(f"--- Descending into directory '{dir_rel_path}' ---")
                dirs.append(d) # Add back to dirs list if not ignored

        # --- Process files in the current directory ---
        for f in files:
            file_rel_path = os.path.join(relative_root, f).replace(os.sep, '/')
            is_ignored = False

            # 1. Check against combined ignore spec
            if combined_spec and combined_spec.match_file(file_rel_path):
                is_ignored = True
                verbose_print(f"--- Ignoring file '{file_rel_path}' (Pattern Match) ---")

            # 2. Check against self (script path)
            if not is_ignored and script_path_rel and file_rel_path == script_path_rel:
                is_ignored = True
                verbose_print(f"--- Ignoring file '{file_rel_path}' (Self) ---")

            # 3. If not ignored by any rule, include it
            if not is_ignored:
                verbose_print(f"--- Including file '{file_rel_path}' ---")
                included_files.append(file_rel_path)
            # else: # Already printed reason above
            #    pass

    # Sort for consistent order
    included_files.sort()
    return included_files


def build_tree_structure(files: List[str]) -> str:
    """Builds an ASCII tree structure from a sorted list of relative file paths."""
    if not files:
        return "[Empty Project or All Files Ignored]"

    structure: Dict[str, Any] = {}
    for fpath in files:
        parts = fpath.split('/')
        current_level = structure
        for i, part in enumerate(parts):
            if i == len(parts) - 1: # File
                current_level[part] = None
            else: # Directory
                if part not in current_level:
                    current_level[part] = {}
                # Ensure we only descend into dicts, handle file/dir name clashes if any
                if isinstance(current_level.get(part), dict):
                     current_level = current_level[part]
                else:
                     # This part is already marked as a file, stop descending for this path
                     break


    def generate_tree_lines_recursive(level_dict: Dict, indent: str) -> List[str]:
        lines = []
        items = sorted(level_dict.keys())
        for i, name in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            lines.append(f"{indent}{connector}{name}")

            value = level_dict[name]
            if isinstance(value, dict): # It's a directory, recurse
                sub_indent = indent + ("    " if is_last else "│   ")
                lines.extend(generate_tree_lines_recursive(value, sub_indent))
        return lines

    # Generate tree starting from the root level dictionary
    tree_lines = generate_tree_lines_recursive(structure, "")
    return "\n".join(tree_lines)


def read_file_content(filepath: str) -> Tuple[Optional[str], Optional[str]]:
    """Reads file content, handling potential encoding errors."""
    try:
        with open(filepath, 'r', encoding=DEFAULT_ENCODING, errors=READ_ERROR_BEHAVIOR) as f:
            return f.read(), None
    except FileNotFoundError:
        return None, f"File not found: {filepath}"
    except UnicodeDecodeError as e:
         return None, f"Encoding error ({DEFAULT_ENCODING}) reading {filepath}: {e}. Consider adding pattern to exclusions if binary."
    except Exception as e:
        return None, f"Error reading {filepath}: {e}"

# --- Main Execution ---

def main():
    parser = argparse.ArgumentParser(
        description="Copies project files (respecting .gitignore, size limits) to clipboard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Example Usage:
  python {os.path.basename(__file__)} ./my_project
  python {os.path.basename(__file__)} -e "*.log" -e "temp/" --max-size 500K
  python {os.path.basename(__file__)} --max-size 2M -v

Default max file size: {DEFAULT_MAX_SIZE_STR}
Size units: K (KB), M (MB), G (GB), T (TB). No suffix means bytes.
Use -v or --verbose for detailed ignore pattern matching output.

Output format:
[filestructure (like tree)]

[relative/path/to/file1.py]:'''
[content of file1.py]
'''
..."""
    )
    parser.add_argument(
        "project_directory",
        nargs='?',
        default=".",
        help="The root directory of the project (default: current directory)."
    )
    parser.add_argument(
        "-e", "--exclude",
        action='append',
        default=[],
        help="Additional gitignore-style patterns to exclude (can be used multiple times)."
    )
    parser.add_argument(
        "--max-size",
        default=DEFAULT_MAX_SIZE_STR,
        help=f"Maximum file size to include (e.g., '1M', '500K', '1024'). Default: {DEFAULT_MAX_SIZE_STR}."
    )
    parser.add_argument(
        "-o", "--output-file",
        metavar="FILE",
        help="Optional file path to write the output to (instead of clipboard)."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging to stderr to see ignore pattern matching."
    )

    args = parser.parse_args()

    # --- Setup Verbose Logging ---
    if args.verbose:
        # Redefine verbose_print to actually print to stderr
        def verbose_print_func(*a, **k):
            print(*a, file=sys.stderr, **k)
        # Make it globally accessible within this module
        global verbose_print
        verbose_print = verbose_print_func
    # --- End Verbose Setup ---


    project_dir = os.path.abspath(args.project_directory) # Use absolute path
    if not os.path.isdir(project_dir):
        print(f"Error: Project directory not found or not a directory: {project_dir}", file=sys.stderr)
        sys.exit(1)

    max_size_bytes = parse_size(args.max_size)
    if max_size_bytes is None:
        print(f"Error: Invalid format for --max-size: '{args.max_size}'. Use formats like '1M', '500K', '1024'.", file=sys.stderr)
        sys.exit(1)

    verbose_print(f"--- Max file size set to: {args.max_size} ({max_size_bytes} bytes) ---")
    print(f"--- Starting project copy for: {project_dir} ---", file=sys.stderr)

    # 1. Read .gitignore patterns (only reads, doesn't create spec yet)
    gitignore_patterns = read_gitignore(project_dir)

    # 2. Get list of potentially included files (applies combined ignore spec)
    potential_files_rel = get_included_files(project_dir, gitignore_patterns, args.exclude)

    if not potential_files_rel:
        print("--- No files found matching initial criteria (check ignore patterns / project path). ---", file=sys.stderr)
        output_string = "[No files included]"
    else:
        print(f"--- Found {len(potential_files_rel)} potential files. Checking sizes and reading... ---", file=sys.stderr)

        # 3. Filter by size AND read content
        included_files_data = {} # Store {rel_path: content} for included files
        skipped_files_error = []
        skipped_files_size = []

        for rel_path in potential_files_rel:
            full_path = os.path.join(project_dir, rel_path) # Use absolute project dir
            try:
                file_size = os.path.getsize(full_path)
                if file_size > max_size_bytes:
                    verbose_print(f"--- Skipping file '{rel_path}' ({file_size} bytes) - Exceeds max size {max_size_bytes} bytes. ---")
                    skipped_files_size.append(rel_path)
                    continue

                content, error = read_file_content(full_path)
                if error:
                    print(f"Warning: Skipping file {rel_path}: {error}", file=sys.stderr)
                    skipped_files_error.append(rel_path)
                    continue

                # Store content if included
                included_files_data[rel_path] = content

            except FileNotFoundError:
                 print(f"Warning: Skipping file {rel_path} - File vanished during processing.", file=sys.stderr)
                 skipped_files_error.append(rel_path)
            except Exception as e:
                 print(f"Warning: Skipping file {rel_path} - Unexpected error during size check/read prep: {e}", file=sys.stderr)
                 skipped_files_error.append(rel_path)

        # 4. Build the file structure tree ONLY from files that were ACTUALLY included
        included_files_final_list = sorted(included_files_data.keys())

        if not included_files_final_list:
             print("--- No files included after applying size limits and checking readability. ---", file=sys.stderr)
             output_string = "[No files included]"
        else:
            print(f"--- Included {len(included_files_final_list)} files. Building structure tree... ---", file=sys.stderr)
            tree_structure_str = build_tree_structure(included_files_final_list)
            verbose_print("--- File structure tree built. ---")

            # 5. Combine tree and file contents
            print("--- Formatting final output... ---", file=sys.stderr)
            final_output_parts = [f"[{tree_structure_str}]\n"]
            for rel_path in included_files_final_list: # Iterate in sorted order
                 content = included_files_data[rel_path]
                 output_rel_path = rel_path.replace(os.sep, '/') # Ensure forward slashes
                 final_output_parts.append(f"[{output_rel_path}]:'''\n{content}\n'''\n")

            output_string = "\n".join(final_output_parts).strip()

            if skipped_files_size:
                 print(f"--- Info: Skipped {len(skipped_files_size)} files due to size limit. ---", file=sys.stderr)
            if skipped_files_error:
                 print(f"--- Warning: Skipped {len(skipped_files_error)} files due to reading errors. ---", file=sys.stderr)


    # 6. Output to File or Clipboard (same as before)
    if args.output_file:
        try:
            with open(args.output_file, 'w', encoding=DEFAULT_ENCODING) as f:
                f.write(output_string)
            print(f"--- Output successfully written to: {args.output_file} ---", file=sys.stderr)
        except Exception as e:
            print(f"Error: Could not write to output file {args.output_file}: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        try:
            pyperclip.copy(output_string)
            output_size_kb = len(output_string.encode(DEFAULT_ENCODING, errors='ignore')) / 1024
            print(f"--- Output ({output_size_kb:.2f} KB) copied to clipboard! ---", file=sys.stderr)
            if output_size_kb > 4000: # Warn if > ~4MB, common clipboard limit area
                 print(f"--- Warning: Output size ({output_size_kb:.2f} KB) is large, clipboard may have truncated content. Consider using the -o FILE option. ---", file=sys.stderr)
        except pyperclip.PyperclipException as e:
             # Error message adjusted based on previous feedback
             print(f"\n--- Error: Could not copy to clipboard: {e} ---", file=sys.stderr)
             print("--- Ensure clipboard utilities (like xclip/xsel on Linux) are installed and accessible. ---", file=sys.stderr)
             print("--- Outputting to console instead: ---\n", file=sys.stderr)
             print(output_string)
             sys.exit(1)
        except Exception as e:
             print(f"Error: An unexpected error occurred during clipboard copy: {e}", file=sys.stderr)
             print("\n--- Clipboard failed, printing output below: ---\n", file=sys.stderr)
             print(output_string)
             sys.exit(1)


if __name__ == "__main__":
    main()