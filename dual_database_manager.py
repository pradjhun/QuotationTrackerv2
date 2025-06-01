import sqlite3
import pandas as pd
import os
from typing import Tuple, Dict, Any, List
import json
from datetime import datetime


class DualDatabaseManager:
    def __init__(self):
        """Initialize dual database manager with separate product and quotation databases."""
        self.product_db_path = 'products_master.db'
        self.quotation_db_path = 'quotations.db'
        self._init_databases()
    
    def _init_databases(self):
        """Initialize both databases and create tables if they don't exist."""
        self._init_product_database()
        self._init_quotation_database()
    
    def _init_product_database(self):
        """Initialize the products master database."""
        conn = sqlite3.connect(self.product_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model TEXT NOT NULL,
                body_color TEXT,
                picture TEXT,
                price REAL NOT NULL,
                watt TEXT,
                size TEXT,
                beam_angle TEXT,
                cut_out TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _init_quotation_database(self):
        """Initialize the quotations database."""
        conn = sqlite3.connect(self.quotation_db_path)
        cursor = conn.cursor()
        
        # Quotations header table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                quotation_date DATE DEFAULT CURRENT_DATE,
                total_amount REAL NOT NULL,
                discount_total REAL DEFAULT 0,
                final_amount REAL NOT NULL,
                status TEXT DEFAULT 'DRAFT',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Quotation line items table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quotation_id TEXT NOT NULL,
                product_id INTEGER,
                model TEXT NOT NULL,
                body_color TEXT,
                light_color TEXT,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                discount REAL DEFAULT 0,
                item_total REAL NOT NULL,
                size TEXT,
                watt TEXT,
                beam_angle TEXT,
                cut_out TEXT,
                picture TEXT,
                FOREIGN KEY (quotation_id) REFERENCES quotations (quotation_id),
                FOREIGN KEY (product_id) REFERENCES products (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # Product Master Database Methods
    def add_product(self, model: str, body_color: str, picture: str, price: float, 
                   watt: str, size: str, beam_angle: str, cut_out: str) -> Tuple[bool, str]:
        """Add a new product to the master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO products (model, body_color, picture, price, watt, size, beam_angle, cut_out)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (model, body_color, picture, price, watt, size, beam_angle, cut_out))
            
            conn.commit()
            conn.close()
            return True, f"Product '{model}' added successfully"
            
        except Exception as e:
            return False, f"Error adding product: {str(e)}"
    
    def update_product(self, product_id: int, model: str, body_color: str, picture: str, 
                      price: float, watt: str, size: str, beam_angle: str, cut_out: str) -> Tuple[bool, str]:
        """Update an existing product in the master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE products 
                SET model=?, body_color=?, picture=?, price=?, watt=?, size=?, 
                    beam_angle=?, cut_out=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            ''', (model, body_color, picture, price, watt, size, beam_angle, cut_out, product_id))
            
            conn.commit()
            conn.close()
            return True, f"Product updated successfully"
            
        except Exception as e:
            return False, f"Error updating product: {str(e)}"
    
    def delete_product(self, product_id: int) -> Tuple[bool, str]:
        """Delete a product from the master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM products WHERE id=?', (product_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, "Product deleted successfully"
            else:
                conn.close()
                return False, "Product not found"
                
        except Exception as e:
            return False, f"Error deleting product: {str(e)}"
    
    def get_all_products(self) -> pd.DataFrame:
        """Get all products from the master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            df = pd.read_sql_query('SELECT * FROM products ORDER BY model', conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error getting products: {str(e)}")
            return pd.DataFrame()
    
    def search_products(self, search_term: str = "", filters: Dict[str, Any] = None) -> pd.DataFrame:
        """Search products in the master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            
            query = "SELECT * FROM products WHERE 1=1"
            params = []
            
            if search_term:
                query += " AND (model LIKE ? OR body_color LIKE ? OR watt LIKE ? OR size LIKE ?)"
                search_pattern = f"%{search_term}%"
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            
            if filters:
                for column, value in filters.items():
                    if value and value != 'All':
                        query += f" AND {column} = ?"
                        params.append(value)
            
            query += " ORDER BY model"
            
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
            
        except Exception as e:
            print(f"Error searching products: {str(e)}")
            return pd.DataFrame()
    
    def get_product_by_id(self, product_id: int) -> pd.Series:
        """Get a specific product by ID."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            df = pd.read_sql_query('SELECT * FROM products WHERE id=?', conn, params=[product_id])
            conn.close()
            
            if not df.empty:
                return df.iloc[0]
            else:
                return pd.Series()
                
        except Exception as e:
            print(f"Error getting product: {str(e)}")
            return pd.Series()
    
    # Quotation Database Methods
    def save_quotation(self, quotation_id: str, customer_name: str, items: List[Dict], 
                      total_amount: float, discount_total: float, final_amount: float) -> Tuple[bool, str]:
        """Save a quotation with its items to the quotation database."""
        try:
            conn = sqlite3.connect(self.quotation_db_path)
            cursor = conn.cursor()
            
            # Insert quotation header
            cursor.execute('''
                INSERT INTO quotations (quotation_id, customer_name, total_amount, discount_total, final_amount)
                VALUES (?, ?, ?, ?, ?)
            ''', (quotation_id, customer_name, total_amount, discount_total, final_amount))
            
            # Insert quotation items
            for item in items:
                cursor.execute('''
                    INSERT INTO quotation_items 
                    (quotation_id, model, body_color, light_color, price, quantity, discount, 
                     item_total, size, watt, beam_angle, cut_out, picture)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    quotation_id,
                    item.get('model', ''),
                    item.get('body_color', ''),
                    item.get('light_color', ''),
                    item.get('price', 0),
                    item.get('quantity', 1),
                    item.get('discount', 0),
                    item.get('item_total', 0),
                    item.get('size', ''),
                    item.get('watt', ''),
                    item.get('beam_angle', ''),
                    item.get('cut_out', ''),
                    item.get('picture', '')
                ))
            
            conn.commit()
            conn.close()
            return True, f"Quotation '{quotation_id}' saved successfully"
            
        except Exception as e:
            return False, f"Error saving quotation: {str(e)}"
    
    def get_all_quotations(self) -> pd.DataFrame:
        """Get all quotations from the quotation database."""
        try:
            conn = sqlite3.connect(self.quotation_db_path)
            df = pd.read_sql_query('''
                SELECT quotation_id, customer_name, quotation_date, total_amount, 
                       discount_total, final_amount, status
                FROM quotations 
                ORDER BY created_at DESC
            ''', conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error getting quotations: {str(e)}")
            return pd.DataFrame()
    
    def get_quotation_items(self, quotation_id: str) -> pd.DataFrame:
        """Get all items for a specific quotation."""
        try:
            conn = sqlite3.connect(self.quotation_db_path)
            df = pd.read_sql_query('''
                SELECT * FROM quotation_items 
                WHERE quotation_id = ? 
                ORDER BY id
            ''', conn, params=[quotation_id])
            conn.close()
            return df
        except Exception as e:
            print(f"Error getting quotation items: {str(e)}")
            return pd.DataFrame()
    
    def delete_quotation(self, quotation_id: str) -> Tuple[bool, str]:
        """Delete a quotation and its items."""
        try:
            conn = sqlite3.connect(self.quotation_db_path)
            cursor = conn.cursor()
            
            # Delete items first
            cursor.execute('DELETE FROM quotation_items WHERE quotation_id=?', (quotation_id,))
            
            # Delete quotation header
            cursor.execute('DELETE FROM quotations WHERE quotation_id=?', (quotation_id,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, "Quotation deleted successfully"
            else:
                conn.close()
                return False, "Quotation not found"
                
        except Exception as e:
            return False, f"Error deleting quotation: {str(e)}"
    
    # Data Migration Methods
    def import_products_from_excel(self, df: pd.DataFrame) -> Tuple[bool, str]:
        """Import products from Excel DataFrame to master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            
            # Clean and standardize column names
            df_clean = df.copy()
            column_mapping = {
                'S.NO': 'sno',
                'MODEL': 'model',
                'BODY CLOLOR': 'body_color',  # Note: keeping original typo for compatibility
                'BODY COLOUR': 'body_color',
                'PICTURE': 'picture',
                'PRICE': 'price',
                'WATT': 'watt',
                'SIZE': 'size',
                'BEAM ANGLE': 'beam_angle',
                'CUT OUT': 'cut_out'
            }
            
            # Rename columns
            for old_col, new_col in column_mapping.items():
                if old_col in df_clean.columns:
                    df_clean = df_clean.rename(columns={old_col: new_col})
            
            # Ensure required columns exist
            required_columns = ['model', 'price']
            for col in required_columns:
                if col not in df_clean.columns:
                    return False, f"Required column '{col}' not found in data"
            
            # Fill missing values
            df_clean = df_clean.fillna('')
            
            # Insert data
            for _, row in df_clean.iterrows():
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO products (model, body_color, picture, price, watt, size, beam_angle, cut_out)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    str(row.get('model', '')),
                    str(row.get('body_color', '')),
                    str(row.get('picture', '')),
                    float(row.get('price', 0)),
                    str(row.get('watt', '')),
                    str(row.get('size', '')),
                    str(row.get('beam_angle', '')),
                    str(row.get('cut_out', ''))
                ))
            
            conn.commit()
            conn.close()
            
            return True, f"Successfully imported {len(df_clean)} products"
            
        except Exception as e:
            return False, f"Error importing products: {str(e)}"
    
    def clear_products(self) -> Tuple[bool, str]:
        """Clear all products from master database."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM products')
            conn.commit()
            conn.close()
            return True, "All products cleared"
        except Exception as e:
            return False, f"Error clearing products: {str(e)}"
    
    def get_total_products(self) -> int:
        """Get total number of products."""
        try:
            conn = sqlite3.connect(self.product_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM products')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            return 0
    
    def get_total_quotations(self) -> int:
        """Get total number of quotations."""
        try:
            conn = sqlite3.connect(self.quotation_db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM quotations')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            return 0