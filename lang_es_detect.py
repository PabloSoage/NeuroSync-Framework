import os
import re
import argparse
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Ensure consistent results
DetectorFactory.seed = 0

def is_spanish_comment(text):
    try:
        language = detect(text)
        return language == "es"
    except LangDetectException:
        return False

def analyze_file(path, show_lines=False):
    found = False
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                if "#" in line:
                    comment = line.split("#", 1)[-1].strip()
                    if comment and is_spanish_comment(comment):
                        found = True
                        if show_lines:
                            print(f"{path}:{i}: {comment}")
                        else:
                            print(path)
                            break
    except Exception as e:
        print(f"Error reading {path}: {e}")
    return found

def main():
    parser = argparse.ArgumentParser(description="Detect Spanish comments in Python files.")
    parser.add_argument("--lines", action="store_true", help="Show lines instead of just filenames.")
    args = parser.parse_args()

    for root, dirs, files in os.walk("."):
        if ".venv" in dirs:
            dirs.remove(".venv")  # Skip .venv directory

        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                analyze_file(filepath, show_lines=args.lines)

if __name__ == "__main__":
    main()
