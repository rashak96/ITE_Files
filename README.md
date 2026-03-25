# ITE Presentation Pipeline

Extracts ITE exam questions and critiques from PDFs, groups them by topic and sub-topic, and builds PowerPoint decks:

1. **Question slide** — stem and all choices (A–E)  
2. **Poll responses slide** — bar chart (counts filled automatically from CSV; see below)  
3. **Critique slide** — correct answer and rationale  

## Running the pipeline

```powershell
cd "c:\Users\L\Downloads\ITE_Files"
pip install pymupdf python-pptx pytesseract Pillow
# Windows (for 2023 scanned PDFs): install Tesseract from
# https://github.com/UB-Mannheim/tesseract/wiki

python extract_ite.py
python create_ite_pptx.py
```

Outputs: `ite_data.json`, `ITE_PowerPoints\*.pptx`

Or one step: `python run_pipeline.py` (extract + PowerPoint).

## Automate poll results on the charts

After your session, put vote counts in a CSV (one row per question):

| year | number | A | B | C | D | E |
|------|--------|---|---|---|---|---|
| 2024 | 1      | 12| 5 | 3 | 0 | 2 |

Generate a blank template for every extracted question:

```powershell
python export_poll_template.py -o my_polls.csv
```

Fill counts (from Vevox/Slido export, Excel, etc.), then apply to all topic decks:

```powershell
python apply_poll_results.py --csv my_polls.csv --all
```

Single deck: `python apply_poll_results.py --csv my_polls.csv --pptx ITE_PowerPoints\Cardiology.pptx`

The script updates each **Poll responses** bar chart and keeps the **correct** choice bar green (uses `ite_data.json`).

JSON is also supported: see `apply_poll_results.py` header for formats.

## Format

- **Fonts**: Montserrat (titles), Segoe UI (body)  
- **Layout**: 16:9, grey header bars, sub-topic on each slide  

## Notes

- **2023 PDFs** are scan-only; first OCR run can take several minutes.  
- **Topics** are keyword-matched; some items may land in General Medicine.
