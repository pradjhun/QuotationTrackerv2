import pandas as pd
import streamlit as st
import sqlite3
import os
from typing import Tuple, Dict, Any

class DatabaseManager:
    def __init__(self):
        """Initialize the database manager with persistent SQLite database."""
        self.db_path = "quotation_database.db"
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database and create table if it doesn't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create table with all columns
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sl_no REAL,
                    model TEXT,
                    body_color TEXT,
                    picture TEXT,
                    price TEXT,
                    watt TEXT,
                    size TEXT,
                    beam_angle TEXT,
                    cut_out TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error initializing database: {str(e)}")
    
    def _get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def import_data(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """
        Import data from DataFrame into the database.
        
        Args:
            df: DataFrame containing the data to import
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Clean the dataframe first
            cleaned_df = self._clean_dataframe(df)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert data into SQLite database
            for _, row in cleaned_df.iterrows():
                cursor.execute('''
                    INSERT INTO quotations (sl_no, model, body_color, picture, price, watt, size, beam_angle, cut_out)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('SL.NO'),
                    row.get('MODEL'),
                    row.get('BODY CLOLOR'),
                    row.get('PICTURE'),
                    row.get('PRICE'),
                    row.get('WATT'),
                    row.get('SIZE'),
                    row.get('BEAM ANGLE'),
                    row.get('CUT OUT')
                ))
            
            conn.commit()
            conn.close()
            
            return True, f"Successfully imported {len(cleaned_df)} records to persistent database"
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
        df = self.get_all_data()
        if df.empty:
            return pd.DataFrame()
        
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
        if 'quotation_database' not in st.session_state:
            st.session_state.quotation_database = pd.DataFrame()
        return st.session_state.quotation_database.copy()
    
    def get_total_records(self) -> int:
        """
        Get the total number of records in the database.
        
        Returns:
            Number of records
        """
        if 'quotation_database' not in st.session_state:
            st.session_state.quotation_database = pd.DataFrame()
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
