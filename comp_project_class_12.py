import mysql.connector
from datetime import date
import sys

# ---------------------------------------------------------
# DATABASE CONNECTION
# ---------------------------------------------------------
def connect_database():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="YOUR_PASSWORD",  # <--- ENTER YOUR MYSQL PASSWORD HERE
            database="restaurant"
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        sys.exit()

# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------
def calculate_tax(subtotal, tax_rate):
    """Reusable function to calculate tax amount."""
    return (subtotal * tax_rate) / 100

def print_header(title):
    print("\n" + "=" * 60)
    print(title.center(60))
    print("=" * 60)

# ---------------------------------------------------------
# 1. DISPLAY MENU
# ---------------------------------------------------------
def display_menu(cursor):
    print_header("RESTAURANT MENU")
    cursor.execute("SELECT item_id, item_name, category, price FROM menu ORDER BY category, item_id")
    records = cursor.fetchall()
    
    if not records:
        print("Menu is currently empty.")
        return

    print(f"{'Code':<8} {'Item Name':<25} {'Category':<15} {'Price':>8}")
    print("-" * 60)
    for row in records:
        print(f"{row[0]:<8} {row[1]:<25} {row[2]:<15} {row[3]:>8.2f}")
    print("=" * 60)

# ---------------------------------------------------------
# 2. SEARCH MENU
# ---------------------------------------------------------
def search_menu(cursor):
    print_header("SEARCH MENU")
    print("1. Search by Item Name")
    print("2. Search by Category")
    print("3. Back")
    
    choice = input("Enter your choice: ")
    query = ""
    param = ()
    
    if choice == '1':
        name = input("Enter item name to search: ")
        query = "SELECT * FROM menu WHERE item_name LIKE %s"
        param = (f"%{name}%",)
    elif choice == '2':
        cat = input("Enter category to search: ")
        query = "SELECT * FROM menu WHERE category LIKE %s"
        param = (f"%{cat}%",)
    elif choice == '3':
        return
    else:
        print("Invalid choice!")
        return

    cursor.execute(query, param)
    records = cursor.fetchall()
    
    if not records:
        print("No items found matching your search.")
    else:
        print("\nSearch Results:")
        print(f"{'Code':<8} {'Item Name':<25} {'Category':<15} {'Price':>8}")
        print("-" * 60)
        for row in records:
            print(f"{row[0]:<8} {row[1]:<25} {row[2]:<15} {row[3]:>8.2f}")

# ---------------------------------------------------------
# 3. PLACE ORDER
# ---------------------------------------------------------
def place_order(cursor, session):
    print_header("PLACE ORDER")
    
    # Get basic details if starting a new order
    if not session['customer']:
        session['customer'] = input("Enter Customer Name: ").strip()
        while not session['customer']:
            print("Customer name cannot be empty.")
            session['customer'] = input("Enter Customer Name: ").strip()
            
        while True:
            try:
                session['table'] = int(input("Enter Table Number: "))
                if session['table'] <= 0:
                    print("Table number must be positive.")
                    continue
                break
            except ValueError:
                print("Invalid input. Please enter a valid table number.")

    # Order loop
    while True:
        try:
            item_code = int(input("\nEnter Item Code: "))
            
            # Check if item exists
            cursor.execute("SELECT item_name, price FROM menu WHERE item_id = %s", (item_code,))
            item = cursor.fetchone()
            
            if not item:
                print("Invalid Item Code! Please check the menu.")
                continue
                
            qty = int(input("Enter Quantity: "))
            if qty <= 0:
                print("Quantity must be greater than zero.")
                continue
                
            item_name = item[0]
            price = float(item[1])
            amount = price * qty
            
            # Save to temporary session
            order_item = {
                'item_id': item_code,
                'name': item_name,
                'qty': qty,
                'price': price,
                'amount': amount
            }
            session['items'].append(order_item)
            
            print(f">>> {item_name} x {qty} = {amount:.2f} added to order.")
            
            more = input("\nAdd another item? (Y/N): ").upper()
            if more != 'Y':
                break
                
        except ValueError:
            print("Invalid input! Please enter numeric values for Code and Quantity.")

# ---------------------------------------------------------
# 4. CALCULATE BILL (Preview)
# ---------------------------------------------------------
def calculate_bill(session):
    if not session['items']:
        print("\nNo items in the current order! Please place an order first.")
        return False
        
    print_header("RESTAURANT BILL (PREVIEW)")
    print(f"Customer: {session['customer']}")
    print(f"Table No: {session['table']}")
    print(f"Date    : {date.today()}")
    print("-" * 60)
    print(f"{'Item Name':<25} {'Qty':<5} {'Price':>8} {'Amount':>10}")
    print("-" * 60)
    
    subtotal = 0.0
    for item in session['items']:
        print(f"{item['name']:<25} {item['qty']:<5} {item['price']:>8.2f} {item['amount']:>10.2f}")
        subtotal += item['amount']
        
    tax_amount = calculate_tax(subtotal, session['tax_rate'])
    total = subtotal + tax_amount
    
    print("-" * 60)
    print(f"{'Subtotal':<40} {subtotal:>10.2f}")
    print(f"Tax ({session['tax_rate']}%) {'':<30} {tax_amount:>10.2f}")
    print("-" * 60)
    print(f"{'TOTAL':<40} {total:>10.2f}")
    print("=" * 60)
    
    return subtotal, tax_amount, total

# ---------------------------------------------------------
# 5. GST / TAX CALCULATION
# ---------------------------------------------------------
def select_tax(session):
    print_header("SELECT TAX RATE")
    print("1. 0%")
    print("2. 5%")
    print("3. 12%")
    print("4. 18%")
    print("5. Custom Tax")
    
    choice = input("Select tax bracket: ")
    
    try:
        if choice == '1': session['tax_rate'] = 0.0
        elif choice == '2': session['tax_rate'] = 5.0
        elif choice == '3': session['tax_rate'] = 12.0
        elif choice == '4': session['tax_rate'] = 18.0
        elif choice == '5':
            rate = float(input("Enter custom tax percentage (e.g., 7.5): "))
            if rate < 0:
                print("Tax cannot be negative.")
                return
            session['tax_rate'] = rate
        else:
            print("Invalid choice. Tax rate unchanged.")
            return
            
        print(f"\nTax rate successfully updated to {session['tax_rate']}%.")
    except ValueError:
        print("Invalid input! Tax rate unchanged.")

# ---------------------------------------------------------
# 6. STORE BILL IN MYSQL
# ---------------------------------------------------------
def store_bill(conn, cursor, session):
    if not session['items']:
        print("\nCannot store an empty order. Please place an order first.")
        return

    # Calculate final amounts
    subtotal = sum(item['amount'] for item in session['items'])
    tax_amount = calculate_tax(subtotal, session['tax_rate'])
    total = subtotal + tax_amount
    
    try:
        # Generate new unique Bill ID
        cursor.execute("SELECT MAX(bill_id) FROM bills")
        result = cursor.fetchone()
        new_bill_id = 1001 if result[0] is None else result[0] + 1
        
        # 1. Insert into bills table
        insert_bill = """INSERT INTO bills 
                         (bill_id, customer_name, table_no, bill_date, subtotal, tax_rate, tax_amount, total, status) 
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        bill_values = (new_bill_id, session['customer'], session['table'], date.today(), 
                       subtotal, session['tax_rate'], tax_amount, total, 'PAID')
        cursor.execute(insert_bill, bill_values)
        
        # 2. Insert each item into order_details table
        insert_order = """INSERT INTO order_details 
                          (bill_id, item_id, quantity, price, amount) 
                          VALUES (%s, %s, %s, %s, %s)"""
        for item in session['items']:
            cursor.execute(insert_order, (new_bill_id, item['item_id'], item['qty'], item['price'], item['amount']))
            
        # Commit the transaction
        conn.commit()
        
        print(f"\n✅ Bill stored successfully in database! Your Bill ID is: {new_bill_id}")
        
        # Clear the temporary session after successful save
        session['customer'] = ""
        session['table'] = 0
        session['items'] = []
        # We retain the tax_rate for the next customer
        
    except mysql.connector.Error as err:
        conn.rollback() # Cancel database changes if any error occurs
        print(f"\n❌ Failed to store bill due to database error: {err}")

# ---------------------------------------------------------
# 7. VIEW PREVIOUS BILLS
# ---------------------------------------------------------
def view_previous_bills(cursor):
    print_header("PREVIOUS BILLS")
    cursor.execute("SELECT bill_id, customer_name, bill_date, total, status FROM bills ORDER BY bill_id DESC")
    records = cursor.fetchall()
    
    if not records:
        print("No bills found in the database.")
        return
        
    print(f"{'Bill ID':<10} {'Customer':<20} {'Date':<15} {'Total':>10}   {'Status'}")
    print("-" * 75)
    for row in records:
        print(f"{row[0]:<10} {row[1]:<20} {str(row[2]):<15} {row[3]:>10.2f}   {row[4]}")
    print("=" * 75)

# ---------------------------------------------------------
# 8. SEARCH BILL
# ---------------------------------------------------------
def search_bill(cursor):
    try:
        search_id = int(input("\nEnter Bill ID to search: "))
        
        # Fetch bill details
        cursor.execute("SELECT * FROM bills WHERE bill_id = %s", (search_id,))
        bill = cursor.fetchone()
        
        if not bill:
            print("Bill not found!")
            return
            
        print_header(f"BILL DETAILS - {search_id}")
        print(f"Customer: {bill[1]}")
        print(f"Table No: {bill[2]}")
        print(f"Date    : {bill[3]}")
        print(f"Status  : {bill[8]}")
        print("-" * 60)
        print(f"{'Item Name':<25} {'Qty':<5} {'Price':>8} {'Amount':>10}")
        print("-" * 60)
        
        # Fetch ordered items using JOIN
        query = """SELECT m.item_name, o.quantity, o.price, o.amount 
                   FROM order_details o 
                   JOIN menu m ON o.item_id = m.item_id 
                   WHERE o.bill_id = %s"""
        cursor.execute(query, (search_id,))
        items = cursor.fetchall()
        
        for item in items:
            print(f"{item[0]:<25} {item[1]:<5} {item[2]:>8.2f} {item[3]:>10.2f}")
            
        print("-" * 60)
        print(f"{'Subtotal':<40} {bill[4]:>10.2f}")
        print(f"Tax ({bill[5]}%) {'':<30} {bill[6]:>10.2f}")
        print("-" * 60)
        print(f"{'TOTAL':<40} {bill[7]:>10.2f}")
        print("=" * 60)
        
    except ValueError:
        print("Invalid Bill ID! Please enter a number.")

# ---------------------------------------------------------
# 9. ADD MENU ITEM
# ---------------------------------------------------------
def add_menu_item(conn, cursor):
    print_header("ADD MENU ITEM")
    try:
        i_code = int(input("Enter New Item Code: "))
        
        # Check for duplicates
        cursor.execute("SELECT item_id FROM menu WHERE item_id = %s", (i_code,))
        if cursor.fetchone():
            print("Error: Item code already exists!")
            return
            
        i_name = input("Enter Item Name: ").strip()
        i_cat = input("Enter Category: ").strip()
        if not i_name or not i_cat:
            print("Name and Category cannot be empty.")
            return
            
        i_price = float(input("Enter Price: "))
        if i_price < 0:
            print("Price cannot be negative.")
            return
            
        cursor.execute("INSERT INTO menu (item_id, item_name, category, price) VALUES (%s, %s, %s, %s)", 
                       (i_code, i_name, i_cat, i_price))
        conn.commit()
        print("✅ Item added successfully!")
    except ValueError:
        print("Invalid input! Code and Price must be numeric.")

# ---------------------------------------------------------
# 10. UPDATE MENU ITEM
# ---------------------------------------------------------
def update_menu_item(conn, cursor):
    print_header("UPDATE MENU ITEM")
    try:
        i_code = int(input("Enter Item Code to update: "))
        cursor.execute("SELECT * FROM menu WHERE item_id = %s", (i_code,))
        if not cursor.fetchone():
            print("Item code not found!")
            return
            
        print("1. Update Item Name")
        print("2. Update Category")
        print("3. Update Price")
        print("4. Update All")
        print("5. Back")
        
        choice = input("Select option: ")
        
        if choice == '1':
            new_name = input("Enter new name: ")
            cursor.execute("UPDATE menu SET item_name = %s WHERE item_id = %s", (new_name, i_code))
        elif choice == '2':
            new_cat = input("Enter new category: ")
            cursor.execute("UPDATE menu SET category = %s WHERE item_id = %s", (new_cat, i_code))
        elif choice == '3':
            new_price = float(input("Enter new price: "))
            cursor.execute("UPDATE menu SET price = %s WHERE item_id = %s", (new_price, i_code))
        elif choice == '4':
            new_name = input("Enter new name: ")
            new_cat = input("Enter new category: ")
            new_price = float(input("Enter new price: "))
            cursor.execute("UPDATE menu SET item_name=%s, category=%s, price=%s WHERE item_id=%s", 
                           (new_name, new_cat, new_price, i_code))
        elif choice == '5':
            return
        else:
            print("Invalid Choice.")
            return
            
        conn.commit()
        print("✅ Menu item updated successfully!")
    except ValueError:
        print("Invalid input! Please enter correct data types.")

# ---------------------------------------------------------
# 11. DELETE MENU ITEM
# ---------------------------------------------------------
def delete_menu_item(conn, cursor):
    print_header("DELETE MENU ITEM")
    try:
        i_code = int(input("Enter Item Code to delete: "))
        cursor.execute("SELECT item_name FROM menu WHERE item_id = %s", (i_code,))
        item = cursor.fetchone()
        
        if not item:
            print("Item code not found!")
            return
            
        print(f"Item found: {item[0]}")
        confirm = input("Are you sure you want to delete this item? (Y/N): ").upper()
        
        if confirm == 'Y':
            try:
                cursor.execute("DELETE FROM menu WHERE item_id = %s", (i_code,))
                conn.commit()
                print("✅ Item deleted successfully.")
            except mysql.connector.errors.IntegrityError:
                # Catch foreign key constraint error
                print("\n❌ CANNOT DELETE ITEM.")
                print("This item has been ordered in the past and is stored in previous bills.")
                print("Deleting it would destroy historical billing data.")
        else:
            print("Deletion cancelled.")
    except ValueError:
        print("Invalid input! Enter a valid Item Code.")

# ---------------------------------------------------------
# 12. VIEW TURNOVER
# ---------------------------------------------------------
def view_turnover(cursor):
    print_header("TURNOVER REPORT")
    print("1. Today's Turnover")
    print("2. Monthly Turnover")
    print("3. Custom Date")
    print("4. Back")
    
    choice = input("Select an option: ")
    query = "SELECT SUM(total) FROM bills WHERE status = 'PAID' AND "
    
    try:
        if choice == '1':
            cursor.execute(query + "bill_date = %s", (date.today(),))
            total = cursor.fetchone()[0]
            val = total if total else 0.0
            print(f"\nToday's Turnover ({date.today()}): ₹{val:.2f}")
            
        elif choice == '2':
            yr = input("Enter Year (YYYY): ")
            mn = input("Enter Month (MM): ")
            cursor.execute(query + "YEAR(bill_date) = %s AND MONTH(bill_date) = %s", (yr, mn))
            total = cursor.fetchone()[0]
            val = total if total else 0.0
            print(f"\nTurnover for {mn}/{yr}: ₹{val:.2f}")
            
        elif choice == '3':
            c_date = input("Enter Date (YYYY-MM-DD): ")
            cursor.execute(query + "bill_date = %s", (c_date,))
            total = cursor.fetchone()[0]
            val = total if total else 0.0
            print(f"\nTurnover for {c_date}: ₹{val:.2f}")
            
        elif choice == '4':
            return
        else:
            print("Invalid choice!")
    except mysql.connector.Error:
        print("Invalid date format or database error.")

# ---------------------------------------------------------
# 13. CANCEL BILL
# ---------------------------------------------------------
def cancel_bill(conn, cursor):
    print_header("CANCEL BILL")
    try:
        b_id = int(input("Enter Bill ID to cancel: "))
        cursor.execute("SELECT customer_name, total, status FROM bills WHERE bill_id = %s", (b_id,))
        bill = cursor.fetchone()
        
        if not bill:
            print("Bill not found!")
            return
            
        if bill[2] == 'CANCELLED':
            print("This bill is already cancelled.")
            return
            
        print(f"\nBill ID: {b_id}")
        print(f"Customer: {bill[0]}")
        print(f"Total: ₹{bill[1]}")
        print(f"Status: {bill[2]}")
        
        confirm = input("\nAre you sure you want to cancel this bill? (Y/N): ").upper()
        if confirm == 'Y':
            # We UPDATE the status instead of DELETING to preserve history
            cursor.execute("UPDATE bills SET status = 'CANCELLED' WHERE bill_id = %s", (b_id,))
            conn.commit()
            print(f"✅ Bill {b_id} has been cancelled successfully.")
        else:
            print("Action aborted.")
    except ValueError:
        print("Invalid Bill ID.")

# ---------------------------------------------------------
# MAIN MENU LOOP
# ---------------------------------------------------------
def main():
    conn = connect_database()
    cursor = conn.cursor()
    
    # Session state dictionary to hold temporary order data before saving to MySQL
    session_state = {
        'customer': '',
        'table': 0,
        'items': [],
        'tax_rate': 5.0  # Default tax rate
    }
    
    while True:
        print("\n" + "="*50)
        print("            RESTAURANT BILLING SYSTEM")
        print("="*50)
        print("1.  Display Menu")
        print("2.  Search Menu")
        print("3.  Place Order")
        print("4.  Calculate Bill")
        print("5.  GST/Tax Calculation")
        print("6.  Store Bill in MySQL")
        print("7.  View Previous Bills")
        print("8.  Search Bill")
        print("9.  Add Menu Item")
        print("10. Update Menu Item")
        print("11. Delete Menu Item")
        print("12. View Turnover")
        print("13. Cancel Bill/Order")
        print("14. Exit")
        print("="*50)
        
        choice = input("Enter your choice: ")
        
        if choice == '1': display_menu(cursor)
        elif choice == '2': search_menu(cursor)
        elif choice == '3': place_order(cursor, session_state)
        elif choice == '4': calculate_bill(session_state)
        elif choice == '5': select_tax(session_state)
        elif choice == '6': store_bill(conn, cursor, session_state)
        elif choice == '7': view_previous_bills(cursor)
        elif choice == '8': search_bill(cursor)
        elif choice == '9': add_menu_item(conn, cursor)
        elif choice == '10': update_menu_item(conn, cursor)
        elif choice == '11': delete_menu_item(conn, cursor)
        elif choice == '12': view_turnover(cursor)
        elif choice == '13': cancel_bill(conn, cursor)
        elif choice == '14':
            print("\nThank you for using the Restaurant Billing System! Exiting...")
            cursor.close()
            conn.close()
            break
        else:
            print("Invalid choice! Please select between 1 and 14.")

# Program Execution Start Point
if __name__ == "__main__":
    main()