import sqlite3
import pandas as pd
import os
from typing import Tuple, Dict, Any


class DatabaseManager:
    def __init__(self):
        """Initialize the database manager with persistent SQLite database."""
        self.db_path = 'quotation_database.db'
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database and create table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create main data table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sno TEXT,
                model TEXT,
                body_color TEXT,
                picture TEXT,
                price TEXT,
                watt TEXT,
                size TEXT,
                beam_angle TEXT,
                cut_out TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create quotations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id TEXT UNIQUE,
                customer_name TEXT,
                quotation_date DATE DEFAULT CURRENT_DATE,
                items TEXT,
                total_amount REAL,
                discount_total REAL,
                final_amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
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
            # Clean and prepare the dataframe
            df_clean = self._clean_dataframe(df)
            
            conn = self._get_connection()
            
            # Insert data into the database
            for _, row in df_clean.iterrows():
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO product_data (sno, model, body_color, picture, price, watt, size, beam_angle, cut_out)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(row.get('S.NO', '')),
                    str(row.get('MODEL', '')),
                    str(row.get('BODY CLOLOR', '')),
                    str(row.get('PICTURE', '')),
                    str(row.get('PRICE', '')),
                    str(row.get('WATT', '')),
                    str(row.get('SIZE', '')),
                    str(row.get('BEAM ANGLE', '')),
                    str(row.get('CUT OUT', ''))
                ))
            
            conn.commit()
            conn.close()
            
            return True, f"Successfully imported {len(df_clean)} records"
            
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
        # Create a copy to avoid modifying the original
        df_clean = df.copy()
        
        # Standardize column names (handle variations)
        column_mapping = {
            'S.NO': 'S.NO',
            'Sr. No.': 'S.NO',
            'Sr.No.': 'S.NO',
            'MODEL': 'MODEL',
            'Model': 'MODEL',
            'BODY CLOLOR': 'BODY CLOLOR',
            'BODY COLOUR': 'BODY CLOLOR',
            'Body Color': 'BODY CLOLOR',
            'Body Colour': 'BODY CLOLOR',
            'PICTURE': 'PICTURE',
            'Picture': 'PICTURE',
            'PRICE': 'PRICE',
            'Price': 'PRICE',
            'WATT': 'WATT',
            'Watt': 'WATT',
            'SIZE': 'SIZE',
            'Size': 'SIZE',
            'BEAM ANGLE': 'BEAM ANGLE',
            'Beam Angle': 'BEAM ANGLE',
            'CUT OUT': 'CUT OUT',
            'Cut Out': 'CUT OUT'
        }
        
        # Rename columns based on mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df_clean.columns:
                df_clean = df_clean.rename(columns={old_col: new_col})
        
        # Fill missing values with empty strings
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
        try:
            conn = self._get_connection()
            
            # Base query
            query = "SELECT * FROM product_data WHERE 1=1"
            params = []
            
            # Add search term filter
            if search_term:
                search_conditions = []
                search_columns = ['model', 'body_color', 'watt', 'size', 'beam_angle']
                
                for column in search_columns:
                    search_conditions.append(f"{column} LIKE ?")
                    params.append(f"%{search_term}%")
                
                query += f" AND ({' OR '.join(search_conditions)})"
            
            # Add specific filters
            if filters:
                for column, value in filters.items():
                    if value and value != 'All':
                        # Map display column names to database column names
                        db_column_map = {
                            'BODY CLOLOR': 'body_color',
                            'WATT': 'watt',
                            'SIZE': 'size'
                        }
                        db_column = db_column_map.get(column, column.lower())
                        query += f" AND {db_column} = ?"
                        params.append(value)
            
            query += " ORDER BY model"
            
            # Execute query and create DataFrame
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            
            # Convert database column names back to display format
            column_rename_map = {
                'sno': 'Sr. No.',
                'model': 'MODEL',
                'body_color': 'BODY CLOLOR',
                'picture': 'PICTURE',
                'price': 'PRICE',
                'watt': 'WATT',
                'size': 'SIZE',
                'beam_angle': 'BEAM ANGLE',
                'cut_out': 'CUT OUT'
            }
            
            df = df.rename(columns=column_rename_map)
            
            return df
            
        except Exception as e:
            print(f"Error searching data: {str(e)}")
            return pd.DataFrame()
    
    def get_all_data(self) -> pd.DataFrame:
        """
        Get all data from the database.
        
        Returns:
            Complete DataFrame
        """
        try:
            conn = self._get_connection()
            df = pd.read_sql_query("SELECT * FROM product_data ORDER BY model", conn)
            conn.close()
            
            # Convert database column names back to display format
            column_rename_map = {
                'sno': 'Sr. No.',
                'model': 'MODEL',
                'body_color': 'BODY CLOLOR',
                'picture': 'PICTURE',
                'price': 'PRICE',
                'watt': 'WATT',
                'size': 'SIZE',
                'beam_angle': 'BEAM ANGLE',
                'cut_out': 'CUT OUT'
            }
            
            df = df.rename(columns=column_rename_map)
            
            return df
            
        except Exception as e:
            print(f"Error getting data: {str(e)}")
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
            cursor.execute("SELECT COUNT(*) FROM product_data")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"Error getting record count: {str(e)}")
            return 0
    
    def clear_database(self) -> None:
        """Clear all data from the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM product_data")
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error clearing database: {str(e)}")
    
    def get_column_unique_values(self, column: str) -> list:
        """
        Get unique values for a specific column.
        
        Args:
            column: Column name
            
        Returns:
            List of unique values
        """
        try:
            # Map display column names to database column names
            db_column_map = {
                'BODY CLOLOR': 'body_color',
                'WATT': 'watt',
                'SIZE': 'size',
                'BEAM ANGLE': 'beam_angle',
                'CUT OUT': 'cut_out'
            }
            
            db_column = db_column_map.get(column, column.lower())
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(f"SELECT DISTINCT {db_column} FROM product_data WHERE {db_column} != '' ORDER BY {db_column}")
            values = [row[0] for row in cursor.fetchall()]
            conn.close()
            return values
        except Exception as e:
            print(f"Error getting unique values: {str(e)}")
            return []
    
    def save_quotation(self, quotation_id: str, customer_name: str, items: list, total_amount: float, discount_total: float, final_amount: float) -> Tuple[bool, str]:
        """Save a quotation to the database."""
        try:
            import json
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Convert items list to JSON string
            items_json = json.dumps(items)
            
            cursor.execute('''
                INSERT INTO quotations (quotation_id, customer_name, items, total_amount, discount_total, final_amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (quotation_id, customer_name, items_json, total_amount, discount_total, final_amount))
            
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
                SELECT quotation_id, customer_name, quotation_date, total_amount, discount_total, final_amount
                FROM quotations 
                ORDER BY created_at DESC
            ''', conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error getting quotations: {str(e)}")
            return pd.DataFrame()
    
    def get_quotation_items(self, quotation_id: str) -> pd.DataFrame:
        """Get items for a specific quotation."""
        try:
            import json
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT items FROM quotations WHERE quotation_id = ?', (quotation_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                items_data = json.loads(result[0])
                df = pd.DataFrame(items_data)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"Error getting quotation items: {str(e)}")
            return pd.DataFrame()