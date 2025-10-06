#!/usr/bin/env python3
"""
Script to check what users are currently stored in the CS Gauntlet database
"""

import sqlite3
import os
from datetime import datetime

def check_database_users():
    # Database path
    db_path = os.path.join('instance', 'cs_gauntlet.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user';")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            print("User table does not exist in the database.")
            conn.close()
            return
        
        # Get all users
        cursor.execute("SELECT id, username, email, university, github_username, college_name, created_at FROM user;")
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
        else:
            print(f"Found {len(users)} user(s) in the database:")
            print("-" * 80)
            for user in users:
                user_id, username, email, university, github_username, college_name, created_at = user
                print(f"ID: {user_id}")
                print(f"Username: {username}")
                print(f"Email: {email}")
                print(f"University: {university}")
                print(f"GitHub Username: {github_username}")
                print(f"College Name: {college_name}")
                print(f"Created At: {created_at}")
                print("-" * 80)
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database_users()
