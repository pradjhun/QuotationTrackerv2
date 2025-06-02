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
            
            # Create quotations table for generated quotes
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS generated_quotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quotation_id TEXT UNIQUE,
                    customer_name TEXT,
                    customer_address TEXT,
                    quotation_date DATE,
                    total_amount REAL,
                    discount_total REAL,
                    final_amount REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create quotation items table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS quotation_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    quotation_id TEXT,
                    product_id INTEGER,
                    model TEXT,
                    body_color TEXT,
                    picture TEXT,
                    price REAL,
                    watt TEXT,
                    size TEXT,
                    beam_angle TEXT,
                    cut_out TEXT,
                    light_color TEXT,
                    quantity INTEGER,
                    discount REAL,
                    item_total REAL,
                    FOREIGN KEY (quotation_id) REFERENCES generated_quotations (quotation_id)
                )
            ''')
            
            # Check if customer_address column exists and add it if missing (migration)
            cursor.execute("PRAGMA table_info(generated_quotations)")
            columns = [column[1] for column in cursor.fetchall()]
            if 'customer_address' not in columns:
                cursor.execute('ALTER TABLE generated_quotations ADD COLUMN customer_address TEXT')
            if 'sales_person' not in columns:
                cursor.execute('ALTER TABLE generated_quotations ADD COLUMN sales_person TEXT')
            if 'sales_contact' not in columns:
                cursor.execute('ALTER TABLE generated_quotations ADD COLUMN sales_contact TEXT')
            
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
        try:
            conn = self._get_connection()
            df = pd.read_sql_query('''
                SELECT sl_no as "SL.NO", model as "MODEL", body_color as "BODY CLOLOR", 
                       picture as "PICTURE", price as "PRICE", watt as "WATT", 
                       size as "SIZE", beam_angle as "BEAM ANGLE", cut_out as "CUT OUT"
                FROM quotations ORDER BY id
            ''', conn)
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame()
    
    def get_total_records(self) -> int:
        """
        Get the total number of records in the database.
        
        Returns:
            Number of records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM quotations")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            return 0
    
    def clear_database(self) -> None:
        """Clear all data from the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM quotations")
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error clearing database: {str(e)}")
    
    def get_column_unique_values(self, column: str) -> list:
        """
        Get unique values for a specific column.
        
        Args:
            column: Column name
            
        Returns:
            List of unique values
        """
        df = self.get_all_data()
        if column in df.columns:
            return df[column].dropna().unique().tolist()
        return []
    
    def save_quotation(self, quotation_id: str, customer_name: str, customer_address: str, items: list, total_amount: float, discount_total: float, final_amount: float, sales_person: str = "", sales_contact: str = "") -> Tuple[bool, str]:
        """Save a quotation to the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Insert quotation header
            cursor.execute('''
                INSERT INTO generated_quotations 
                (quotation_id, customer_name, customer_address, quotation_date, total_amount, discount_total, final_amount, sales_person, sales_contact)
                VALUES (?, ?, ?, DATE('now'), ?, ?, ?, ?, ?)
            ''', (quotation_id, customer_name, customer_address, total_amount, discount_total, final_amount, sales_person, sales_contact))
            
            # Insert quotation items
            for item in items:
                cursor.execute('''
                    INSERT INTO quotation_items 
                    (quotation_id, product_id, model, body_color, picture, price, watt, size, 
                     beam_angle, cut_out, light_color, quantity, discount, item_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (quotation_id, item['product_id'], item['model'], item['body_color'], 
                      item['picture'], item['price'], item['watt'], item['size'],
                      item['beam_angle'], item['cut_out'], item['light_color'], 
                      item['quantity'], item['discount'], item['item_total']))
            
            conn.commit()
            conn.close()
            return True, f"Quotation {quotation_id} saved successfully"
            
        except Exception as e:
            return False, f"Error saving quotation: {str(e)}"
    
    def get_quotations(self) -> pd.DataFrame:
        """Get all saved quotations."""
        try:
            conn = self._get_connection()
            df = pd.read_sql_query('''
                SELECT quotation_id, customer_name, customer_address, quotation_date, 
                       total_amount, discount_total, final_amount, sales_person, sales_contact, created_at
                FROM generated_quotations 
                ORDER BY created_at DESC
            ''', conn)
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame()
    
    def get_quotation_items(self, quotation_id: str) -> pd.DataFrame:
        """Get items for a specific quotation."""
        try:
            conn = self._get_connection()
            df = pd.read_sql_query('''
                SELECT * FROM quotation_items 
                WHERE quotation_id = ?
                ORDER BY id
            ''', conn, params=(quotation_id,))
            conn.close()
            return df
        except Exception as e:
            return pd.DataFrame()
