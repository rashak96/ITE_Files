"""
Extract ITE questions and critiques from PDF files.
Parses Multiple Choice booklets and Critique manuals, matches by question number.
Outputs structured JSON for PowerPoint generation.

Some years (e.g. 2023) use scan-only PDFs with no text layer — those are OCR'd
with Tesseract if installed (Windows: https://github.com/UB-Mannheim/tesseract/wiki).
"""

import io
import json
import os
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    import fitz  # PyMuPDF
    HAS_PDF = True
except ImportError:
    try:
        import pdfplumber
        HAS_PDF = True
    except ImportError:
        HAS_PDF = False

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def _configure_tesseract() -> bool:
    """Point pytesseract at Tesseract on Windows if not in PATH."""
    if not HAS_OCR:
        return False
    if os.environ.get("TESSERACT_CMD"):
        pytesseract.pytesseract.tesseract_cmd = os.environ["TESSERACT_CMD"]
        return True
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for p in candidates:
            if Path(p).exists():
                pytesseract.pytesseract.tesseract_cmd = p
                return True
    return True


@dataclass
class ITEQuestion:
    number: int
    year: int
    stem: str
    options: dict[str, str]  # A, B, C, D, E
    answer: Optional[str] = None
    critique: Optional[str] = None
    topic: Optional[str] = None
    subtopic: Optional[str] = None


def _extract_native_fitz(path: Path) -> tuple[str, int]:
    import fitz as _fitz
    doc = _fitz.open(path)
    n = len(doc)
    parts = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(parts), n


def extract_text_from_pdf_ocr(path: Path, *, dpi: int = 300, progress: bool = True) -> str:
    """OCR every page (scan-only PDFs). Requires: pip install pytesseract pillow, and Tesseract installed."""
    if not HAS_OCR:
        raise RuntimeError(
            "OCR requires: pip install pytesseract pillow "
            "and Tesseract OCR (set TESSERACT_CMD if not on PATH)"
        )
    _configure_tesseract()
    import fitz as _fitz
    doc = _fitz.open(path)
    out: list[str] = []
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            txt = pytesseract.image_to_string(img, config="--psm 6")
            out.append(txt or "")
            if progress and (i + 1) % 5 == 0:
                print(f"    OCR page {i + 1}/{len(doc)} ...", flush=True)
    finally:
        doc.close()
    return "\n".join(out)


def extract_text_from_pdf(path: Path) -> str:
    """Extract text: native layer first; use OCR if the PDF looks like a scan (no text)."""
    if not HAS_PDF:
        raise ImportError("Install pymupdf or pdfplumber: pip install pymupdf")
    try:
        import fitz as _fitz  # noqa: F401
    except ImportError:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)

    text, n_pages = _extract_native_fitz(path)
    stripped = text.strip()
    # Heuristic: multi-page exam PDFs with almost no text are usually scanned
    need_ocr = n_pages >= 5 and len(stripped) < max(800, n_pages * 40)
    if need_ocr:
        if not HAS_OCR:
            raise RuntimeError(
                f"{path.name}: no extractable text (likely scanned). Install Tesseract + "
                "pip install pytesseract pillow, or use OCR manually."
            )
        print(f"    {path.name}: using OCR ({n_pages} pages) ...", flush=True)
        return extract_text_from_pdf_ocr(path)
    return text


def parse_questions_from_multchoice(text: str, year: int) -> list[ITEQuestion]:
    """Parse questions from Multiple Choice booklet text."""
    questions: list[ITEQuestion] = []
    # Pattern: "1." or "1)\t" at start, then stem, then A) ... E)
    # Questions are numbered 1, 2, 3... Options are A), B), C), D), E)
    option_pattern = re.compile(
        r'^([A-E])\)\s*(.+?)(?=^[A-E]\)|^\d+[\.\)]\s|Item \d+|$)', 
        re.MULTILINE | re.DOTALL
    )
    
    # Split by question number - "1. " or "2. " at line start
    q_blocks = re.split(r'\n(?=\d+[\.\)]\s)', text)
    
    for block in q_blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue
        # Get question number
        num_match = re.match(r'^(\d+)[\.\)]\s*', block)
        if not num_match:
            continue
        qnum = int(num_match.group(1))
        rest = block[num_match.end():]
        
        # Split stem and options - options start with A), B), etc. (with or without newline)
        opt_matches = list(re.finditer(r'(?:^|\n)([A-E])\)\s*', rest))
        if not opt_matches:
            continue
        
        # Stem is everything before first option
        first_opt_start = opt_matches[0].start()
        stem = rest[:first_opt_start].strip()
        stem = re.sub(r'\s+', ' ', stem)
        
        # Parse options
        options = {}
        for i, m in enumerate(opt_matches):
            letter = m.group(1)
            start = m.end()
            end = opt_matches[i + 1].start() if i + 1 < len(opt_matches) else len(rest)
            opt_text = rest[start:end].strip()
            opt_text = re.sub(r'\s+', ' ', opt_text)
            options[letter] = opt_text
        
        if len(options) >= 4:  # At least A-D
            questions.append(ITEQuestion(
                number=qnum, year=year, stem=stem, options=options
            ))
    
    return questions


def parse_questions_alternative(text: str, year: int) -> list[ITEQuestion]:
    """Alternative regex-based parser for MultChoice - handle varying formats."""
    questions: list[ITEQuestion] = []
    
    # Match: "N. " at start of line, content until next "N. " or end
    # Within content: stem before A), then A) ... E)
    q_re = re.compile(
        r'(?:^|\n)(\d+)[\.\)]\s+'
        r'((?:(?!^\d+[\.\)]\s).)*?)'
        r'((?:^[A-E]\)\s+.+?\n?)+)',
        re.MULTILINE | re.DOTALL
    )
    
    for m in q_re.finditer(text):
        qnum = int(m.group(1))
        stem = m.group(2).strip()
        opts_block = m.group(3).strip()
        
        stem = re.sub(r'\s+', ' ', stem)
        
        options = {}
        for opt_m in re.finditer(r'([A-E])\)\s*(.+?)(?=\n[A-E]\)|$)', opts_block, re.DOTALL):
            letter, opt_text = opt_m.group(1), opt_m.group(2).strip()
            opt_text = re.sub(r'\s+', ' ', opt_text)
            options[letter] = opt_text
        
        if options:
            questions.append(ITEQuestion(number=qnum, year=year, stem=stem, options=options))
    
    return questions


def parse_critiques(text: str, year: int) -> dict[int, tuple[str, str]]:
    """Parse critique manual. Returns {item_num: (answer_letter, critique_text)}."""
    result = {}
    
    # Split by "Item N" (works with OCR: optional CR, not always leading newline)
    items = re.split(r'(?:^|\r?\n)Item\s+(\d+)\s*\r?\n', text, flags=re.MULTILINE)
    
    for i in range(1, len(items), 2):
        if i + 1 >= len(items):
            break
        qnum = int(items[i])
        block = items[i + 1]
        
        ans_match = re.search(r'ANSWER:\s*([A-E])\b', block, re.IGNORECASE)
        if not ans_match:
            continue
        answer = ans_match.group(1).upper()
        
        # Critique is from after ANSWER to "Item N+1" or "Reference" or "Ref"
        critique_start = ans_match.end()
        # Remove References section
        ref_match = re.search(
            r'\r?\n(?:Reference|Ref)s?\s*\r?\n', block[critique_start:], re.IGNORECASE
        )
        if ref_match:
            critique = block[critique_start:critique_start + ref_match.start()].strip()
        else:
            critique = block[critique_start:].strip()
        
        # Clean up critique
        critique = re.sub(r'\s+', ' ', critique)
        critique = critique[:2000]  # Limit length
        
        result[qnum] = (answer, critique)
    
    return result


def detect_year_from_filename(name: str) -> Optional[int]:
    """Extract year from filename like 2024 ITE MultChoice Booklet.pdf."""
    m = re.search(r'20(2[2-9]|3[0-9]|4[0-9]|5[0-9])', name)
    return int(m.group(0)) if m else None


def load_all_ite_data(oldite_dir: Path) -> list[ITEQuestion]:
    """Load all questions and critiques from OldITE folder, match and return complete list."""
    oldite_dir = Path(oldite_dir)
    if not oldite_dir.exists():
        raise FileNotFoundError(f"OldITE folder not found: {oldite_dir}")
    
    all_questions: list[ITEQuestion] = []
    critique_by_year: dict[int, dict[int, tuple[str, str]]] = {}
    
    # Find and parse Critique manuals
    for f in sorted(oldite_dir.glob("*[Cc]ritique*.pdf")):
        year = detect_year_from_filename(f.name)
        if year:
            try:
                text = extract_text_from_pdf(f)
                critique_by_year[year] = parse_critiques(text, year)
                print(f"  Parsed {len(critique_by_year[year])} critiques from {f.name} ({year})")
            except Exception as e:
                print(f"  Error parsing {f.name}: {e}")
    
    # Find and parse Multiple Choice booklets
    for f in sorted(oldite_dir.glob("*[Mm]ult*[Cc]hoice*.pdf")):
        year = detect_year_from_filename(f.name)
        if year:
            try:
                text = extract_text_from_pdf(f)
                questions = parse_questions_from_multchoice(text, year)
                if len(questions) < 5:
                    questions = parse_questions_alternative(text, year)
                print(f"  Parsed {len(questions)} questions from {f.name} ({year})")
                
                critiques = critique_by_year.get(year, {})
                for q in questions:
                    if q.number in critiques:
                        ans, crit = critiques[q.number]
                        q.answer = ans
                        q.critique = crit
                    all_questions.append(q)
            except Exception as e:
                print(f"  Error parsing {f.name}: {e}")
    
    return all_questions


# Topic and subtopic classification - keyword matching (order matters: more specific first)
TOPIC_SUBTOPIC_MAP: list[tuple[str, str, list[str]]] = [
    # (Topic, Subtopic, keywords)
    ("Cardiology", "Atrial Fibrillation", ["atrial fibrillation", "afib", "anticoagulation", "warfarin", "chads", "cha2ds2"]),
    ("Cardiology", "Heart Failure", ["heart failure", "chf", "ejection fraction", "systolic", "diastolic"]),
    ("Cardiology", "Hypertension", ["hypertension", "blood pressure", "antihypertensive", "aldosterone", "renin"]),
    ("Cardiology", "ACS and MI", ["myocardial infarction", "stemi", "nstemi", "acute coronary", "chest pain"]),
    ("Cardiology", "Arrhythmia", ["qtc", "qt prolongation", "torsades", "palpitations", "amiodarone"]),
    ("Cardiology", "Perioperative Cardiology", ["perioperative", "bridging", "surgery", "anticoagulation"]),
    ("Endocrinology", "Diabetes", ["diabetes", "diabetic", "a1c", "metformin", "insulin", "hypoglycemia"]),
    ("Endocrinology", "Thyroid", ["thyroid", "hypothyroid", "hyperthyroid", "tsh", "levothyroxine"]),
    ("Endocrinology", "Adrenal", ["aldosteronism", "cushing", "adrenal", "cortisol"]),
    ("Endocrinology", "Calcium/Bone", ["osteoporosis", "dexa", "t-score", "bisphosphonate", "teriparatide", "calcium", "vitamin d"]),
    ("Gastroenterology", "Cirrhosis/Liver", ["cirrhosis", "varices", "hepatitis", "nafld", "masld", "steatohepatitis", "transaminase"]),
    ("Gastroenterology", "GI Bleeding", ["gi bleeding", "upper gi", "lower gi", "melena", "hematochezia"]),
    ("Gastroenterology", "IBD/Functional", ["ibd", "crohn", "ulcerative colitis", "celiac", "ibs"]),
    ("Nephrology", "CKD", ["chronic kidney", "ckd", "glomerular filtration", "dialysis"]),
    ("Nephrology", "AKI/Electrolytes", ["acute kidney", "aki", "hyponatremia", "hyperkalemia", "diabetes insipidus"]),
    ("Pulmonology", "COPD/Asthma", ["copd", "asthma", "exacerbation", "inhaler"]),
    ("Pulmonology", "Pneumonia", ["pneumonia", "community-acquired"]),
    ("Infectious Disease", "UTI", ["uti", "pyelonephritis", "cystitis", "nitrofurantoin"]),
    ("Infectious Disease", "Skin/Soft Tissue", ["cellulitis", "abscess", "mrsa", "hidradenitis"]),
    ("Infectious Disease", "Fungal/Viral", ["coccidioidomycosis", "valley fever", "hiv", "antimicrobial"]),
    ("Dermatology", "Rashes", ["erythema", "rash", "dermatitis", "eczema"]),
    ("Dermatology", "Hidradenitis", ["hidradenitis suppurativa"]),
    ("OB/GYN", "Abnormal Uterine Bleeding", ["uterine bleeding", "menorrhagia", "tranexamic", "progestin"]),
    ("OB/GYN", "Contraception", ["contraception", "iud", "oral contraceptive"]),
    ("OB/GYN", "Pregnancy", ["pregnancy", "prenatal", "gestational"]),
    ("Neurology", "Dementia", ["dementia", "alzheimer", "sundowning", "bpsd"]),
    ("Neurology", "Stroke", ["stroke", "cerebrovascular", "tia"]),
    ("Neurology", "Headache", ["migraine", "headache", "cluster"]),
    ("Psychiatry", "Depression/Anxiety", ["depression", "anxiety", "ssri", "escitalopram", "sertraline"]),
    ("Psychiatry", "Bipolar", ["bipolar", "lithium"]),
    ("Musculoskeletal", "Osteoporosis", ["osteoporosis", "fracture", "dexa"]),
    ("Musculoskeletal", "Arthritis", ["arthritis", "knee replacement", "rheumatoid"]),
    ("Musculoskeletal", "Antibiotic Prophylaxis", ["antibiotic prophylaxis", "dental", "joint replacement"]),
    ("Ophthalmology", "Eye", ["lasik", "myopia", "cataract", "glaucoma", "retinal"]),
    ("Prevention", "Cancer Screening", ["screening", "colonoscopy", "colon cancer", "psa", "mammography"]),
    ("Prevention", "USPSTF", ["uspstf", "preventive services", "screening"]),
    ("Pharmacology", "Drug Interactions", ["drug interaction", "qt prolongation", "cyp"]),
    ("Pharmacology", "Medication Management", ["medication", "dosing", "contraindication"]),
    ("Surgery", "Burns", ["burn", "partial-thickness", "silver sulfadiazine"]),
    ("Urology", "Incontinence", ["incontinence", "overactive bladder", "urinary"]),
]


def assign_topic_subtopic(question: ITEQuestion) -> None:
    """Assign topic and subtopic based on keyword matching."""
    combined = f"{question.stem} {' '.join(question.options.values())} {question.critique or ''}".lower()
    
    for topic, subtopic, keywords in TOPIC_SUBTOPIC_MAP:
        if any(kw in combined for kw in keywords):
            question.topic = topic
            question.subtopic = subtopic
            return
    
    # Default
    question.topic = "General Medicine"
    question.subtopic = "Other"


def main():
    script_dir = Path(__file__).parent
    oldite = script_dir / "OldITE"
    
    print("Extracting ITE data...")
    questions = load_all_ite_data(oldite)
    print(f"Total questions: {len(questions)}")
    
    # Assign topics
    for q in questions:
        assign_topic_subtopic(q)
    
    # Build output structure
    output = []
    for q in questions:
        output.append({
            "number": q.number,
            "year": q.year,
            "stem": q.stem,
            "options": q.options,
            "answer": q.answer,
            "critique": q.critique,
            "topic": q.topic,
            "subtopic": q.subtopic,
        })
    
    out_path = script_dir / "ite_data.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"Saved to {out_path}")
    
    # Summary by topic
    from collections import defaultdict
    by_topic = defaultdict(list)
    for q in questions:
        by_topic[q.topic or "Unknown"].append(q)
    print("\nQuestions by topic:")
    for topic in sorted(by_topic.keys()):
        print(f"  {topic}: {len(by_topic[topic])}")


if __name__ == "__main__":
    main()
