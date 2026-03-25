"""
Run the full ITE pipeline: extract from PDFs, then generate PowerPoints.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def main():
    print("Step 1: Extracting questions from PDFs...")
    r1 = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "extract_ite.py")],
        cwd=SCRIPT_DIR,
    )
    if r1.returncode != 0:
        print("Extraction failed.")
        return r1.returncode

    print("\nStep 2: Generating PowerPoints...")
    r2 = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "create_ite_pptx.py")],
        cwd=SCRIPT_DIR,
    )
    if r2.returncode != 0:
        print("PowerPoint generation failed.")
        return r2.returncode

    print("\nDone. Check ITE_PowerPoints/ folder.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
