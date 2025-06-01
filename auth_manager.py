import sqlite3
import hashlib
import secrets
from typing import Tuple, Optional, Dict, List
from datetime import datetime, timedelta


class AuthManager:
    def __init__(self):
        """Initialize authentication manager with user database."""
        self.db_path = 'users.db'
        self._init_database()
        self._create_default_admin()
    
    def _init_database(self):
        """Initialize the user authentication database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                created_by TEXT
            )
        ''')
        
        # Create sessions table for session management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (username) REFERENCES users (username)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _create_default_admin(self):
        """Create default admin user if no users exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        
        if user_count == 0:
            # Create default admin user: admin/admin123
            salt = secrets.token_hex(16)
            password_hash = self._hash_password('admin123', salt)
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, role, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', ('admin', password_hash, salt, 'admin', 'system'))
            
            conn.commit()
        
        conn.close()
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt using SHA-256."""
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def authenticate(self, username: str, password: str) -> Tuple[bool, Optional[Dict]]:
        """
        Authenticate user credentials.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Tuple of (success, user_info)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, password_hash, salt, role, is_active 
                FROM users 
                WHERE username = ?
            ''', (username,))
            
            result = cursor.fetchone()
            
            if result:
                stored_username, stored_hash, salt, role, is_active = result
                
                if not is_active:
                    conn.close()
                    return False, None
                
                # Verify password
                password_hash = self._hash_password(password, salt)
                
                if password_hash == stored_hash:
                    # Update last login
                    cursor.execute('''
                        UPDATE users SET last_login = CURRENT_TIMESTAMP 
                        WHERE username = ?
                    ''', (username,))
                    conn.commit()
                    
                    user_info = {
                        'username': stored_username,
                        'role': role,
                        'is_active': is_active
                    }
                    
                    conn.close()
                    return True, user_info
            
            conn.close()
            return False, None
            
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            return False, None
    
    def create_session(self, username: str) -> str:
        """Create a new session for authenticated user."""
        try:
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now() + timedelta(hours=24)  # 24-hour session
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Clean expired sessions
            cursor.execute('DELETE FROM user_sessions WHERE expires_at < CURRENT_TIMESTAMP')
            
            # Create new session
            cursor.execute('''
                INSERT INTO user_sessions (username, session_token, expires_at)
                VALUES (?, ?, ?)
            ''', (username, session_token, expires_at))
            
            conn.commit()
            conn.close()
            
            return session_token
            
        except Exception as e:
            print(f"Session creation error: {str(e)}")
            return ""
    
    def validate_session(self, session_token: str) -> Tuple[bool, Optional[Dict]]:
        """Validate session token and return user info."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.username, u.role, u.is_active
                FROM user_sessions s
                JOIN users u ON s.username = u.username
                WHERE s.session_token = ? AND s.expires_at > CURRENT_TIMESTAMP
            ''', (session_token,))
            
            result = cursor.fetchone()
            
            if result:
                username, role, is_active = result
                
                if is_active:
                    user_info = {
                        'username': username,
                        'role': role,
                        'is_active': is_active
                    }
                    conn.close()
                    return True, user_info
            
            conn.close()
            return False, None
            
        except Exception as e:
            print(f"Session validation error: {str(e)}")
            return False, None
    
    def logout(self, session_token: str) -> bool:
        """Logout user by removing session."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM user_sessions WHERE session_token = ?', (session_token,))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"Logout error: {str(e)}")
            return False
    
    def create_user(self, username: str, password: str, role: str, created_by: str) -> Tuple[bool, str]:
        """
        Create a new user (admin only).
        
        Args:
            username: New username
            password: New password
            role: User role ('admin' or 'user')
            created_by: Username of admin creating this user
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if role not in ['admin', 'user']:
                return False, "Invalid role. Must be 'admin' or 'user'"
            
            if len(username) < 3:
                return False, "Username must be at least 3 characters"
            
            if len(password) < 6:
                return False, "Password must be at least 6 characters"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if username already exists
            cursor.execute('SELECT username FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                conn.close()
                return False, "Username already exists"
            
            # Create new user
            salt = secrets.token_hex(16)
            password_hash = self._hash_password(password, salt)
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, salt, role, created_by)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, salt, role, created_by))
            
            conn.commit()
            conn.close()
            
            return True, f"User '{username}' created successfully with role '{role}'"
            
        except Exception as e:
            return False, f"Error creating user: {str(e)}"
    
    def get_all_users(self) -> List[Dict]:
        """Get list of all users (admin only)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT username, role, is_active, created_at, last_login, created_by
                FROM users
                ORDER BY created_at DESC
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'username': row[0],
                    'role': row[1],
                    'is_active': bool(row[2]),
                    'created_at': row[3],
                    'last_login': row[4],
                    'created_by': row[5]
                })
            
            conn.close()
            return users
            
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            return []
    
    def update_user_status(self, username: str, is_active: bool) -> Tuple[bool, str]:
        """Update user active status (admin only)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET is_active = ? WHERE username = ?
            ''', (is_active, username))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                status = "activated" if is_active else "deactivated"
                return True, f"User '{username}' {status} successfully"
            else:
                conn.close()
                return False, "User not found"
                
        except Exception as e:
            return False, f"Error updating user status: {str(e)}"
    
    def change_user_role(self, username: str, new_role: str) -> Tuple[bool, str]:
        """Change user role (admin only)."""
        try:
            if new_role not in ['admin', 'user']:
                return False, "Invalid role. Must be 'admin' or 'user'"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE users SET role = ? WHERE username = ?
            ''', (new_role, username))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, f"User '{username}' role changed to '{new_role}'"
            else:
                conn.close()
                return False, "User not found"
                
        except Exception as e:
            return False, f"Error changing user role: {str(e)}"
    
    def delete_user(self, username: str) -> Tuple[bool, str]:
        """Delete user (admin only)."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Cannot delete the last admin
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = "admin" AND is_active = 1')
            admin_count = cursor.fetchone()[0]
            
            cursor.execute('SELECT role FROM users WHERE username = ?', (username,))
            user_result = cursor.fetchone()
            
            if user_result and user_result[0] == 'admin' and admin_count <= 1:
                conn.close()
                return False, "Cannot delete the last active admin user"
            
            # Delete user sessions first
            cursor.execute('DELETE FROM user_sessions WHERE username = ?', (username,))
            
            # Delete user
            cursor.execute('DELETE FROM users WHERE username = ?', (username,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return True, f"User '{username}' deleted successfully"
            else:
                conn.close()
                return False, "User not found"
                
        except Exception as e:
            return False, f"Error deleting user: {str(e)}"
    
    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password."""
        try:
            if len(new_password) < 6:
                return False, "New password must be at least 6 characters"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verify old password
            cursor.execute('SELECT password_hash, salt FROM users WHERE username = ?', (username,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return False, "User not found"
            
            stored_hash, salt = result
            old_password_hash = self._hash_password(old_password, salt)
            
            if old_password_hash != stored_hash:
                conn.close()
                return False, "Current password is incorrect"
            
            # Update password
            new_salt = secrets.token_hex(16)
            new_password_hash = self._hash_password(new_password, new_salt)
            
            cursor.execute('''
                UPDATE users SET password_hash = ?, salt = ? WHERE username = ?
            ''', (new_password_hash, new_salt, username))
            
            conn.commit()
            conn.close()
            
            return True, "Password changed successfully"
            
        except Exception as e:
            return False, f"Error changing password: {str(e)}"