import pandas as pd
from typing import Tuple

def validate_excel_structure(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate that the Excel file has the expected structure.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    if df.empty:
        return False, "The Excel file is empty."
    
    # Clean column names for comparison
    columns = [col.strip().upper() for col in df.columns]
    
    # Expected columns (some variations allowed)
    expected_columns = [
        'SL.NO', 'MODULE', 'BODY COLOUR', 'PICTURE', 
        'SINGLE COLOUR OPTION', 'WATT', 'SIZE', 'BEAM ANGLE', 'CUT OUT'
    ]
    
    # Alternative column names that are acceptable
    column_alternatives = {
        'SL.NO': ['SERIAL NO', 'SERIAL NUMBER', 'S.NO', 'SNO'],
        'BODY COLOUR': ['BODY COLOR'],
        'SINGLE COLOUR OPTION': ['SINGLE COLOR OPTION', 'SINGLE COLOR'],
        'CUT OUT': ['CUTOUT', 'CUT-OUT']
    }
    
    # Check if we have at least some key columns
    key_columns = ['MODULE', 'WATT', 'SIZE']
    found_key_columns = []
    
    for key_col in key_columns:
        if key_col in columns:
            found_key_columns.append(key_col)
        else:
            # Check alternatives
            alternatives = column_alternatives.get(key_col, [])
            for alt in alternatives:
                if alt in columns:
                    found_key_columns.append(key_col)
                    break
    
    if len(found_key_columns) < 2:
        return False, f"Missing key columns. Expected at least 2 of: {key_columns}. Found: {found_key_columns}"
    
    # Check for minimum number of rows
    if len(df) < 1:
        return False, "The Excel file must contain at least one data row."
    
    # Validate data types for numeric columns
    numeric_columns = ['WATT', 'SIZE']
    for col in numeric_columns:
        if col in df.columns:
            # Try to convert to numeric
            numeric_series = pd.to_numeric(df[col], errors='coerce')
            if numeric_series.isna().all():
                return False, f"Column '{col}' should contain numeric values."
    
    return True, f"File structure validated successfully. Found {len(df)} rows with {len(df.columns)} columns."

def format_dataframe_display(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format DataFrame for better display in Streamlit.
    
    Args:
        df: DataFrame to format
        
    Returns:
        Formatted DataFrame
    """
    if df.empty:
        return df
    
    formatted_df = df.copy()
    
    # Format numeric columns
    numeric_columns = ['SL.NO', 'WATT', 'SIZE']
    for col in numeric_columns:
        if col in formatted_df.columns:
            # Convert to numeric and format
            numeric_series = pd.to_numeric(formatted_df[col], errors='coerce')
            # Format integers without decimal places
            formatted_df[col] = numeric_series.apply(
                lambda x: f"{int(x)}" if pd.notna(x) and x == int(x) else f"{x:.1f}" if pd.notna(x) else ""
            )
    
    # Ensure string columns are properly formatted
    string_columns = ['MODULE', 'BODY COLOUR', 'PICTURE', 'SINGLE COLOUR OPTION', 'BEAM ANGLE', 'CUT OUT']
    for col in string_columns:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].astype(str).replace('nan', '').replace('None', '')
    
    # Reorder columns to match expected order
    preferred_order = [
        'SL.NO', 'MODULE', 'BODY COLOUR', 'PICTURE', 
        'SINGLE COLOUR OPTION', 'WATT', 'SIZE', 'BEAM ANGLE', 'CUT OUT'
    ]
    
    # Only include columns that exist in the DataFrame
    ordered_columns = [col for col in preferred_order if col in formatted_df.columns]
    remaining_columns = [col for col in formatted_df.columns if col not in ordered_columns]
    final_order = ordered_columns + remaining_columns
    
    return formatted_df[final_order]

def export_to_excel(df: pd.DataFrame, filename: str = None) -> bytes:
    """
    Export DataFrame to Excel format as bytes.
    
    Args:
        df: DataFrame to export
        filename: Optional filename (not used in bytes export)
        
    Returns:
        Excel file as bytes
    """
    import io
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Quotation_Data', index=False)
    
    output.seek(0)
    return output.getvalue()

def clean_search_term(search_term: str) -> str:
    """
    Clean and prepare search term for database queries.
    
    Args:
        search_term: Raw search term
        
    Returns:
        Cleaned search term
    """
    if not search_term:
        return ""
    
    # Remove extra whitespace and convert to lowercase
    cleaned = search_term.strip().lower()
    
    # Remove special characters that might interfere with search
    import re
    cleaned = re.sub(r'[^\w\s.-]', '', cleaned)
    
    return cleaned
