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
    
    # Validate data types for numeric columns (allow mixed content)
    numeric_columns = ['WATT', 'SIZE']
    for col in numeric_columns:
        if col in df.columns:
            # Check if column has some valid numeric values or is mostly empty
            non_empty_values = df[col].dropna()
            if len(non_empty_values) > 0:
                numeric_series = pd.to_numeric(non_empty_values, errors='coerce')
                valid_numeric_ratio = numeric_series.notna().sum() / len(non_empty_values)
                # Allow if at least 30% of non-empty values are numeric or if all are empty/text
                if valid_numeric_ratio < 0.3 and len(non_empty_values) > 3:
                    return False, f"Column '{col}' should contain mostly numeric values. Found {valid_numeric_ratio:.1%} valid numbers."
    
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
    string_columns = ['MODULE', 'BODY COLOUR', 'PICTURE', 'PRICE', 'BEAM ANGLE', 'CUT OUT']
    for col in string_columns:
        if col in formatted_df.columns:
            formatted_df[col] = formatted_df[col].astype(str).replace('nan', '').replace('None', '').fillna('')
    
    # Reorder columns to match expected order
    preferred_order = [
        'SL.NO', 'MODULE', 'BODY COLOUR', 'PICTURE', 
        'PRICE', 'WATT', 'SIZE', 'BEAM ANGLE', 'CUT OUT'
    ]
    
    # Only include columns that exist in the DataFrame
    ordered_columns = [col for col in preferred_order if col in formatted_df.columns]
    remaining_columns = [col for col in formatted_df.columns if col not in ordered_columns]
    final_order = ordered_columns + remaining_columns
    
    return formatted_df[final_order]

def export_to_excel(df: pd.DataFrame, filename: str = None) -> bytes:
    """
    Export DataFrame to Excel format as bytes with embedded images.
    
    Args:
        df: DataFrame to export
        filename: Optional filename (not used in bytes export)
        
    Returns:
        Excel file as bytes
    """
    import io
    import os
    from openpyxl import Workbook
    from openpyxl.drawing import image
    from openpyxl.utils.dataframe import dataframe_to_rows
    from openpyxl.styles import Font, Alignment, Border, Side
    
    # Create a copy of the dataframe and remove product_id if it exists
    df_export = df.copy()
    if 'product_id' in df_export.columns:
        df_export = df_export.drop('product_id', axis=1)
    
    # Create workbook and worksheet
    wb = Workbook()
    ws = wb.active
    ws.title = "Quotation"
    
    # Add headers with styling
    headers = list(df_export.columns)
    
    # Replace 'picture' column header if it exists
    if 'picture' in [h.lower() for h in headers]:
        picture_idx = next(i for i, h in enumerate(headers) if h.lower() == 'picture')
        headers[picture_idx] = 'Product Image'
    
    # Write headers
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    # Set row height for image display
    image_row_height = 80
    
    # Add data rows
    for row_idx, (_, row) in enumerate(df_export.iterrows(), start=2):
        ws.row_dimensions[row_idx].height = image_row_height
        
        for col_idx, (col_name, value) in enumerate(row.items(), start=1):
            if col_name.lower() == 'picture':
                # Handle image insertion
                if value and str(value) != 'nan' and str(value) != '':
                    image_path = os.path.join("uploaded_images", str(value))
                    if os.path.exists(image_path):
                        try:
                            # Insert image
                            img = image.Image(image_path)
                            img.width = 60
                            img.height = 60
                            
                            # Position image in cell
                            cell_address = ws.cell(row=row_idx, column=col_idx).coordinate
                            img.anchor = cell_address
                            ws.add_image(img)
                            
                            # Set cell value to empty since we have image
                            ws.cell(row=row_idx, column=col_idx, value="")
                        except Exception:
                            # If image fails to load, show filename
                            ws.cell(row=row_idx, column=col_idx, value=str(value))
                    else:
                        ws.cell(row=row_idx, column=col_idx, value="Image not found")
                else:
                    ws.cell(row=row_idx, column=col_idx, value="No image")
            else:
                # Regular cell value
                ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Auto-adjust column widths
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column].width = adjusted_width
    
    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
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
