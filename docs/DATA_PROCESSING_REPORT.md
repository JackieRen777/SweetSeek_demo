# Data Processing & Quality Report

## Overview
This report summarizes the data processing, cleaning, and validation steps implemented for the Sweet Compounds Database feature.

## Source Data
- **File**: `data/compounds_sweet.xlsx`
- **Expected Structure**: Contains columns for compound properties including `Compound Name`, `PubChem CID`, `MolecularFormula`, `Relative_Sweetness`, etc.

## Data Cleaning & ETL Process
The `CompoundService` implements the following ETL (Extract, Transform, Load) pipeline:

1.  **Extraction**:
    - Loads data from the Excel file using `pandas`.
    - Handles missing files gracefully (logs warning, initializes empty DataFrame).

2.  **Transformation (Cleaning)**:
    - **Column Normalization**: Maps user-provided column names (e.g., `Compound Name`) to internal standard keys (e.g., `name`).
    - **Missing Value Handling**: Fills `NaN` values with empty strings for text fields and `0` for numeric fields to prevent runtime errors.
    - **Type Enforcement**: Forces numeric types for critical columns:
        - `sweetness`, `mw`, `logp`, `cid`, `tpsa`, `hbond_donor`, `hbond_acceptor`, `rotatable_bond`, `heavy_atom`, `qed`, `sa_score`, `lipinski`
        - Invalid numeric entries are coerced to `NaN` and then filled with `0`.
    - **Deduplication**: Removes duplicate entries based on `PubChem CID` (keeping the first occurrence) to ensure data uniqueness.
    - **ID Generation**: Ensures every record has a unique `id`. If `cid` exists, it uses `cid`; otherwise, it generates a sequential integer ID.

3.  **Loading**:
    - The cleaned DataFrame is stored in memory for fast querying.

## Data Validation
- **Unit Tests**: `tests/test_compound_service.py` verifies:
    - Correct column mapping.
    - Duplicate removal logic.
    - Numeric type conversion.
    - Exact and Fuzzy search functionality.
    - API response structure.

## Quality Metrics
- **Deduplication**: Verified that duplicates are removed.
- **Type Safety**: Verified that numeric columns do not contain string garbage.
- **Search Robustness**: Verified that fuzzy search can handle typos (e.g., "Sugr" -> "Sugar").

## Error Handling
- The service wraps data loading in `try-except` blocks to catch `FileNotFoundError` or parsing errors.
- Errors are logged to the application logger (`sweetseek.compound_service`).
