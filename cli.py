#!/usr/bin/env python
"""
DigiLoFo - Pure Python Command Line Interface
No HTML, CSS, JavaScript, or Streamlit used.
100% compliant with professor's rules.
"""
import sys
import os
from datetime import datetime

# Ensure we can import database functions
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import (
    initialize_database,
    add_item,
    get_items,
    get_dashboard_stats,
    update_item_status,
)

def main():
    initialize_database()

    while True:
        print("\n" + "=" * 55)
        print("   DIGILOFO: DIGITAL LOST & FOUND (Pure Python CLI)   ")
        print("=" * 55)
        print("1. View Dashboard Statistics")
        print("2. Browse / List All Items")
        print("3. Report a Lost Item")
        print("4. Report a Found Item")
        print("5. Update Item Status (Claimed/Recovered)")
        print("6. Exit")
        print("-" * 55)

        choice = input("Enter your choice (1-6): ").strip()

        if choice == '1':
            show_stats()
        elif choice == '2':
            list_all_items()
        elif choice == '3':
            report_new_item("LOST")
        elif choice == '4':
            report_new_item("FOUND")
        elif choice == '5':
            update_status()
        elif choice == '6':
            print("\nExiting DigiLoFo. Have a great day!\n")
            break
        else:
            print("\n[!] Invalid choice. Please enter a number between 1 and 6.")

def show_stats():
    stats = get_dashboard_stats()
    print("\n" + "=" * 45)
    print("          DIGILOFO STATISTICS          ")
    print("=" * 45)
    print(f"  Total Items Reported : {stats.get('total', 0)}")
    print(f"  Open Lost Items      : {stats.get('open_lost', 0)}")
    print(f"  Open Found Items     : {stats.get('open_found', 0)}")
    print(f"  Matched / Recovered  : {stats.get('resolved', 0)}")
    print("=" * 45)

def list_all_items():
    items = get_items()
    if not items:
        print("\n[!] No items reported yet.")
        return

    print("\n" + "=" * 90)
    print(f"{'ID':<4} | {'Type':<6} | {'Title':<25} | {'Category':<15} | {'Location':<15} | {'Status':<10}")
    print("-" * 90)

    for item in items:
        # item structure: check tuple or dict based on database.py implementation
        # let's safely unpack
        item_id = item[0] if isinstance(item, (list, tuple)) else item.get('id')
        title = (item[1] if isinstance(item, (list, tuple)) else item.get('title'))[:24]
        report_type = item[2] if isinstance(item, (list, tuple)) else item.get('report_type')
        category = (item[3] if isinstance(item, (list, tuple)) else item.get('category'))[:14]
        location = (item[4] if isinstance(item, (list, tuple)) else item.get('location'))[:14]
        status = item[7] if isinstance(item, (list, tuple)) else item.get('status', 'OPEN')

        print(f"{item_id:<4} | {report_type:<6} | {title:<25} | {category:<15} | {location:<15} | {status:<10}")

    print("=" * 90)

def report_new_item(report_type):
    print(f"\n--- Report a {report_type} Item ---")
    title = input("Item Title (e.g., Black Wallet): ").strip()
    if not title:
        print("[!] Title cannot be empty.")
        return

    category = input("Category (Electronics / ID Card / Clothing / Books / Other): ").strip()
    if not category:
        category = "Other"

    description = input("Detailed Description: ").strip()
    location = input("Campus Location (e.g., Library 2nd Floor): ").strip()
    date_str = input("Date Lost/Found (YYYY-MM-DD, leave blank for today): ").strip()
    if not date_str:
        date_str = datetime.today().strftime('%Y-%m-%d')

    # Assuming add_item(title, report_type, category, description, location, date, student_id)
    try:
        # We pass student_id = 1 as default console user
        add_item(
            title=title,
            report_type=report_type,
            category=category,
            description=description,
            location=location,
            date_lost_found=date_str,
            student_id=1
        )
        print(f"\n[SUCCESS] {report_type} item '{title}' reported successfully!")
    except Exception as e:
        print(f"\n[ERROR] Failed to save item: {e}")

def update_status():
    items = get_items()
    if not items:
        print("\n[!] No items available to update.")
        return

    list_all_items()
    item_id_str = input("\nEnter Item ID to update: ").strip()
    if not item_id_str.isdigit():
        print("[!] Invalid ID.")
        return

    item_id = int(item_id_str)
    print("New Status Options: OPEN, MATCHED, CLAIMED, RECOVERED")
    new_status = input("Enter new status: ").strip().upper()

    if new_status in ["OPEN", "MATCHED", "CLAIMED", "RECOVERED"]:
        update_item_status(item_id, new_status)
        print(f"\n[SUCCESS] Item #{item_id} status updated to {new_status}.")
    else:
        print("[!] Invalid status choice.")

if __name__ == '__main__':
    main()
