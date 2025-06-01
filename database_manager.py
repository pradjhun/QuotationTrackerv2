import pandas as pd
import streamlit as st
from typing import Tuple, Dict, Any

class DatabaseManager:
    def __init__(self):
        """Initialize the database manager with session state storage."""
        if 'quotation_database' not in st.session_state:
            st.session_state.quotation_database = pd.DataFrame()
    
    def import_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Import data from DataFrame into the database.
        
        Args:
            df: DataFrame containing the data to import
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Clean the data
            df_clean = self._clean_dataframe(df)
            
            # Check if database is empty
            if st.session_state.quotation_database.empty:
                st.session_state.quotation_database = df_clean.copy()
                return True, f"Successfully imported {len(df_clean)} records into the database."
            else:
                # Append new data (avoiding duplicates if possible)
                existing_count = len(st.session_state.quotation_database)
                
                # Combine data
                combined_df = pd.concat([st.session_state.quotation_database, df_clean], ignore_index=True)
                
                # Remove duplicates based on all columns except SL.NO
                columns_for_dedup = [col for col in combined_df.columns if col.upper() != 'SL.NO']
                if columns_for_dedup:
                    combined_df = combined_df.drop_duplicates(subset=columns_for_dedup, keep='first')
                
                # Reset SL.NO to be sequential
                if 'SL.NO' in combined_df.columns:
                    combined_df['SL.NO'] = range(1, len(combined_df) + 1)
                
                st.session_state.quotation_database = combined_df
                new_count = len(combined_df)
                added_count = new_count - existing_count
                
                return True, f"Successfully added {added_count} new records. Total records: {new_count}"
                
        except Exception as e:
            return False, f"Error importing data: {str(e)}"
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean the dataframe by standardizing column names and handling missing values.
        
        Args:
            df: DataFrame to clean
            
        Returns:
            Cleaned DataFrame
        """
        df_clean = df.copy()
        
        # Standardize column names (strip whitespace, convert to uppercase)
        df_clean.columns = df_clean.columns.str.strip().str.upper()
        
        # Map common column name variations
        column_mapping = {
            'SERIAL NO': 'SL.NO',
            'SERIAL NUMBER': 'SL.NO',
            'S.NO': 'SL.NO',
            'SNO': 'SL.NO',
            'BODY COLOR': 'BODY COLOUR',
            'SINGLE COLOR OPTION': 'SINGLE COLOUR OPTION',
            'SINGLE COLOR': 'SINGLE COLOUR OPTION',
            'CUTOUT': 'CUT OUT',
            'CUT-OUT': 'CUT OUT'
        }
        
        df_clean = df_clean.rename(columns=column_mapping)
        
        # Convert numeric columns
        numeric_columns = ['SL.NO', 'WATT', 'SIZE']
        for col in numeric_columns:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # Fill missing values appropriately
        df_clean = df_clean.fillna('')
        
        return df_clean
    
    def search_data(self, search_term: str = "", filters: Dict[str, Any] = None) -> pd.DataFrame:
        """
        Search and filter data based on search term and filters.
        
        Args:
            search_term: Text to search across all columns
            filters: Dictionary of column-value pairs to filter by
            
        Returns:
            Filtered DataFrame
        """
        if st.session_state.quotation_database.empty:
            return pd.DataFrame()
        
        df = st.session_state.quotation_database.copy()
        
        # Apply text search across all columns
        if search_term:
            search_term = search_term.lower()
            mask = df.astype(str).apply(
                lambda x: x.str.lower().str.contains(search_term, na=False)
            ).any(axis=1)
            df = df[mask]
        
        # Apply column-specific filters
        if filters:
            for column, value in filters.items():
                if column in df.columns and value is not None:
                    if isinstance(value, str):
                        df = df[df[column].astype(str).str.contains(str(value), case=False, na=False)]
                    else:
                        df = df[df[column] == value]
        
        return df
    
    def get_all_data(self) -> pd.DataFrame:
        """
        Get all data from the database.
        
        Returns:
            Complete DataFrame
        """
        return st.session_state.quotation_database.copy()
    
    def get_total_records(self) -> int:
        """
        Get the total number of records in the database.
        
        Returns:
            Number of records
        """
        return len(st.session_state.quotation_database)
    
    def clear_database(self) -> None:
        """Clear all data from the database."""
        st.session_state.quotation_database = pd.DataFrame()
    
    def get_column_unique_values(self, column: str) -> list:
        """
        Get unique values for a specific column.
        
        Args:
            column: Column name
            
        Returns:
            List of unique values
        """
        if column in st.session_state.quotation_database.columns:
            return st.session_state.quotation_database[column].dropna().unique().tolist()
        return []
