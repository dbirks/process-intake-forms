# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python application that processes wildlife intake form images using OpenAI's vision capabilities. The application extracts structured data from scanned intake forms and converts them into CSV format for wildlife rehabilitation center reporting.

## Setup and Environment

Copy the environment template and configure:
```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env
```

The `.env` file requires:
- `OPENAI_API_KEY`: Your OpenAI API key
- `OPENAI_MODEL`: Default is gpt-4o  
- `YEAR`: Two-digit year (e.g., "25" for 2025)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OpenTelemetry endpoint (optional)

## Running the Application

The main application processes all images in `inputs/images/`:
```bash
uv run main.py
```

Run utility scripts with uv:
```bash
uv run scripts/list_species.py
```

## Image Processing Workflow

1. **Image Preparation**: Copy images to `inputs/images/` and optionally rotate them:
   ```bash
   find ~/Pictures -type f -mmin -30 -exec cp {} inputs/images \;
   find inputs/images -maxdepth 1 -type f | xargs -I {} magick {} -rotate -90 {}
   ```

2. **Processing**: The application processes each JPG image through OpenAI's vision model using structured output parsing with Pydantic models

3. **Output**: Results are written to timestamped CSV files in `outputs/` directory

## Architecture

- **main.py**: Core application with image processing pipeline
- **Data Models**: `IntakeForm` and `IntakeForms` Pydantic models for structured output
- **Image Processing**: Base64 encoding and OpenAI vision API integration
- **Data Processing**: Uses Polars for CSV operations and dataframe management
- **Reference Data**: Previous years' reports in `inputs/previous_years_reports/` provide validation lists for species and conditions

## Key Processing Logic

The system handles:
- Multiple ID numbers per form (ranges like 081-084 become separate entries)
- Species abbreviation mapping (CAGO → Canada Goose, GHOW → Great Horned Owl, etc.)
- Indiana-specific location validation
- Date formatting (MM.DD.YY)
- Condition text normalization and orphan classification