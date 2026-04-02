# Natural Language to G-code Generator

A Streamlit app that converts plain-English 3D printing requests into draft G-code using the OpenAI Responses API.

> **Important:** This app is best for constrained path-generation tasks (calibration squares, purge lines, simple spirals, geometric paths, and custom motion patterns).

## Features

- Clean Streamlit UI with printer settings in a sidebar
- Structured prompt sent to OpenAI for firmware-aware, bounded output
- Strict JSON response format (`summary`, `assumptions`, `warnings`, `gcode`)
- Built-in validation before generation
- Lightweight post-generation safety checks (bounds, temps, homing)
- Download generated G-code as `generated_output.gcode`

## Project Structure

```text
.
├── app.py
├── services/
│   ├── openai_client.py
│   └── prompt_builder.py
├── utils/
│   └── validators.py
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### 1) Create and activate a virtual environment

**macOS/Linux**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy the example file and add your OpenAI API key:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
OPENAI_API_KEY=your_real_openai_api_key
```

### 4) Run the app

```bash
streamlit run app.py
```

Open the local URL shown in your terminal (commonly `http://localhost:8501`).

## How to Use

1. Enter your desired print path in the main text area.
2. Configure printer settings in the sidebar.
3. Click **Generate G-code**.
4. Review:
   - Summary
   - Assumptions
   - Warnings
   - Generated G-code
5. Download the `.gcode` file if it looks correct.

## Safety Notes

- Always inspect generated G-code before printing.
- Test with small, low-risk movements first.
- Verify temperatures and travel limits for your specific printer.
- If output is vague or task is too complex, provide more detail or use a slicer-based workflow.

## Disclaimer

This tool provides AI-generated draft paths and does **not** replace slicer-generated workflows for complex parts. For production or complex geometry, slicer-generated G-code is still recommended.
