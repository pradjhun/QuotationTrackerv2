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

def export_to_excel(df: pd.DataFrame, filename: str = None, customer_name: str = "", customer_address: str = "", quotation_date: str = "") -> bytes:
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
    
    # Add quotation header information
    current_row = 1
    
    # Title
    title_cell = ws.cell(row=current_row, column=1, value="QUOTATION")
    title_cell.font = Font(bold=True, size=16)
    title_cell.alignment = Alignment(horizontal='center')
    ws.merge_cells(f'A{current_row}:F{current_row}')
    current_row += 2
    
    # Organization Name
    if customer_name:
        # Label cell
        org_label_cell = ws.cell(row=current_row, column=1, value="Organization Name:")
        org_label_cell.font = Font(bold=True, size=12)
        
        # Customer name cell (merge if needed)
        org_name_cell = ws.cell(row=current_row, column=2, value=customer_name)
        org_name_cell.font = Font(size=12)
        
        # Merge cells B to F for organization name if it's long
        if len(customer_name) > 20:
            ws.merge_cells(f'B{current_row}:F{current_row}')
        
        current_row += 1
    
    # Customer Address
    if customer_address:
        # Label cell
        addr_label_cell = ws.cell(row=current_row, column=1, value="Address:")
        addr_label_cell.font = Font(bold=True, size=12)
        
        # Address cell (merge for more space)
        addr_cell = ws.cell(row=current_row, column=2, value=customer_address)
        addr_cell.font = Font(size=12)
        addr_cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        # Always merge cells B to F for address
        ws.merge_cells(f'B{current_row}:F{current_row}')
        
        # Increase row height for address
        ws.row_dimensions[current_row].height = 40
        
        current_row += 1
    
    # Date
    if quotation_date:
        # Label cell
        date_label_cell = ws.cell(row=current_row, column=1, value="Date:")
        date_label_cell.font = Font(bold=True, size=12)
        
        # Date cell
        date_cell = ws.cell(row=current_row, column=2, value=quotation_date)
        date_cell.font = Font(size=12)
        
        current_row += 1
    
    # Add some spacing
    current_row += 1
    
    # Add headers with styling
    headers = list(df_export.columns)
    
    # Replace 'picture' column header if it exists
    if 'picture' in [h.lower() for h in headers]:
        picture_idx = next(i for i, h in enumerate(headers) if h.lower() == 'picture')
        headers[picture_idx] = 'Product Image'
    
    # Write headers
    header_row = current_row
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row, column=col_num, value=header)
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
    
    current_row += 1
    
    # Set row height for image display
    image_row_height = 80
    
    # Add data rows
    for data_idx, (_, row) in enumerate(df_export.iterrows()):
        row_idx = current_row + data_idx
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
                # Check if this is a price or item_total column to add Rupee symbol
                header_name = headers[col_idx - 1].lower() if col_idx - 1 < len(headers) else ""
                if any(price_word in header_name for price_word in ['price', 'total', 'amount', 'cost']):
                    try:
                        # Try to format as currency with Rupee symbol
                        numeric_value = float(value)
                        formatted_value = f"₹{numeric_value:,.2f}"
                        ws.cell(row=row_idx, column=col_idx, value=formatted_value)
                    except (ValueError, TypeError):
                        # If not numeric, use original value
                        ws.cell(row=row_idx, column=col_idx, value=value)
                else:
                    # Regular cell value
                    ws.cell(row=row_idx, column=col_idx, value=value)
    
    # Calculate final row after data
    final_data_row = current_row + len(df_export) - 1
    
    # Add totals section
    totals_start_row = final_data_row + 2
    
    # Calculate totals from the data
    subtotal = 0
    
    # Debug: print available columns
    print(f"Available columns: {list(df_export.columns)}")
    
    # Priority order for finding the correct total column
    price_columns = ['item_total', 'Item Total', 'ITEM TOTAL', 'total', 'Total', 'TOTAL',
                    'final_price', 'Final Price', 'FINAL PRICE', 'final_amount', 'Final Amount', 'FINAL AMOUNT']
    
    for col in price_columns:
        # Check both exact match and case-insensitive match
        matching_cols = [c for c in df_export.columns if c.lower() == col.lower()]
        if matching_cols:
            actual_col = matching_cols[0]
            try:
                # Convert to numeric and sum, handling any non-numeric values
                numeric_values = pd.to_numeric(df_export[actual_col], errors='coerce').fillna(0)
                subtotal = numeric_values.sum()
                print(f"Using column '{actual_col}' for subtotal calculation: {subtotal}")
                if subtotal > 0:
                    break
            except Exception as e:
                print(f"Error calculating from column '{actual_col}': {e}")
                continue
    
    # If no price column found, try to calculate from quantity and unit price
    if subtotal == 0:
        print("No price column found, trying to calculate from quantity * unit_price")
        try:
            qty_cols = [c for c in df_export.columns if 'quantity' in c.lower() or 'qty' in c.lower()]
            price_cols = [c for c in df_export.columns if 'unit' in c.lower() and 'price' in c.lower()]
            
            if qty_cols and price_cols:
                qty_col = qty_cols[0]
                price_col = price_cols[0]
                quantities = pd.to_numeric(df_export[qty_col], errors='coerce').fillna(0)
                unit_prices = pd.to_numeric(df_export[price_col], errors='coerce').fillna(0)
                subtotal = (quantities * unit_prices).sum()
                print(f"Calculated subtotal from {qty_col} * {price_col}: {subtotal}")
        except Exception as e:
            print(f"Error calculating from quantity * unit_price: {e}")
            pass
    
    gst_amount = subtotal * 0.18  # 18% GST
    grand_total = subtotal + gst_amount
    
    # Add subtotal row
    subtotal_cell = ws.cell(row=totals_start_row, column=len(headers)-1, value="Subtotal:")
    subtotal_cell.font = Font(bold=True)
    subtotal_cell.alignment = Alignment(horizontal='right')
    
    subtotal_value_cell = ws.cell(row=totals_start_row, column=len(headers), value=f"₹{subtotal:,.2f}")
    subtotal_value_cell.font = Font(bold=True)
    subtotal_value_cell.alignment = Alignment(horizontal='right')
    
    # Add GST row
    gst_cell = ws.cell(row=totals_start_row + 1, column=len(headers)-1, value="GST (18%):")
    gst_cell.font = Font(bold=True)
    gst_cell.alignment = Alignment(horizontal='right')
    
    gst_value_cell = ws.cell(row=totals_start_row + 1, column=len(headers), value=f"₹{gst_amount:,.2f}")
    gst_value_cell.font = Font(bold=True)
    gst_value_cell.alignment = Alignment(horizontal='right')
    
    # Add grand total row
    total_cell = ws.cell(row=totals_start_row + 2, column=len(headers)-1, value="Grand Total:")
    total_cell.font = Font(bold=True, size=12)
    total_cell.alignment = Alignment(horizontal='right')
    
    total_value_cell = ws.cell(row=totals_start_row + 2, column=len(headers), value=f"₹{grand_total:,.2f}")
    total_value_cell.font = Font(bold=True, size=12)
    total_value_cell.alignment = Alignment(horizontal='right')
    
    # Add Terms & Conditions section
    terms_start_row = totals_start_row + 5
    terms_title_cell = ws.cell(row=terms_start_row, column=1, value="TERMS & CONDITIONS")
    terms_title_cell.font = Font(bold=True, size=14)
    terms_title_cell.alignment = Alignment(horizontal='center')
    ws.merge_cells(f'A{terms_start_row}:F{terms_start_row}')
    
    # Terms & Conditions content
    terms_conditions = [
        "GST & IGST ARE 18%",
        "100% ADVANCE PAYMENT",
        "PRICING ON FOB KOLKATA BASIS",
        "TWO YEAR WARRANTY ON LED",
        "TWO YEAR WARRANTY ON DRIVER",
        "SPOT LIGHTS ARE IP GRADED & DUSTPROOF",
        "DELIVERY WILL TAKE MINIMUM 10-15 WORKING DAYS FROM THE DATE OF CONFIRMED P.O AND ADVANCE PAYMENT.",
        "DELIVERY CHARGE EXTRA AS PER ACTUAL",
        "FOR EVERY BILLING GST NO OR PANCARD NO IS MANDATORY",
        "STRICTLY GOODS ONCE SOLD WILL NOT BE TAKEN BACK AS PER GST"
    ]
    
    # Add each term
    for i, term in enumerate(terms_conditions):
        term_row = terms_start_row + i + 2
        term_cell = ws.cell(row=term_row, column=1, value=f"• {term}")
        term_cell.font = Font(size=10)
        ws.merge_cells(f'A{term_row}:F{term_row}')
    
    # Auto-adjust column widths
    for col_idx in range(1, len(headers) + 1):
        max_length = 0
        column_letter = chr(64 + col_idx)  # A, B, C, etc.
        
        # Check all cells in this column for content length
        for row in ws.iter_rows(min_col=col_idx, max_col=col_idx):
            for cell in row:
                if hasattr(cell, 'value') and cell.value:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
        
        # Set minimum width and apply
        adjusted_width = max(min(max_length + 2, 50), 12)
        ws.column_dimensions[column_letter].width = adjusted_width
    
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
