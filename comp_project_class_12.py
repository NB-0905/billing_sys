"""Restaurant billing system for a Class 12 Computer Science project.

Python standard-library modules are used for validation and money handling.
The only external Python dependency is mysql-connector-python.
"""

import getpass
import os
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import mysql.connector


# ---------------------------------------------------------
# CONFIGURATION AND CONSTANTS
# ---------------------------------------------------------

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
DEFAULT_TAX_RATE = Decimal("5.00")
MAX_PRICE = Decimal("99999999.99")


def connect_database():
    """Connect to MySQL. Return None if the connection cannot be made."""
    password = os.getenv("MYSQL_PASSWORD")
    if password is None:
        password = getpass.getpass(
            "Enter MySQL password (press Enter if there is no password): "
        )

    try:
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=password,
            database=os.getenv("MYSQL_DATABASE", "restaurant"),
        )
        print("\nConnected to the restaurant database successfully.")
        return connection
    except mysql.connector.Error as err:
        print("\nCould not connect to MySQL.")
        print("Check that MySQL is running and the database credentials are correct.")
        print("MySQL error:", err)
        return None


# ---------------------------------------------------------
# GENERAL HELPER FUNCTIONS
# ---------------------------------------------------------

def print_header(title):
    print("\n" + "=" * 68)
    print(title.center(68))
    print("=" * 68)


def money(value):
    """Convert a value to a two-decimal Decimal for accurate currency maths."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_tax(subtotal, tax_rate):
    """Calculate tax and round the result to two decimal places."""
    tax = (Decimal(subtotal) * Decimal(tax_rate)) / Decimal("100")
    return money(tax)


def read_integer(prompt, minimum=None, maximum=None):
    """Read an integer and repeat until it satisfies the supplied limits."""
    while True:
        try:
            value = int(input(prompt).strip())
            if minimum is not None and value < minimum:
                print("Value must be at least", minimum)
                continue
            if maximum is not None and value > maximum:
                print("Value must not exceed", maximum)
                continue
            return value
        except ValueError:
            print("Please enter a whole number.")


def read_decimal(prompt, minimum=None, maximum=None):
    """Read a finite decimal number and round it to two decimal places."""
    while True:
        try:
            value = Decimal(input(prompt).strip())
            if not value.is_finite():
                print("Please enter a valid finite number.")
                continue
            if minimum is not None and value < minimum:
                print("Value must be at least", minimum)
                continue
            if maximum is not None and value > maximum:
                print("Value must not exceed", maximum)
                continue
            return money(value)
        except (InvalidOperation, ValueError):
            print("Please enter a valid number.")


def read_text(prompt, max_length):
    """Read non-empty text that fits the database column length."""
    while True:
        value = input(prompt).strip()
        if not value:
            print("This field cannot be empty.")
        elif len(value) > max_length:
            print("Please enter no more than", max_length, "characters.")
        else:
            return value


def read_yes_no(prompt):
    """Return True for yes and False for no."""
    while True:
        answer = input(prompt).strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("Please enter Y or N.")


def reset_order(session):
    """Clear the current unsaved order without changing its tax rate."""
    session["customer"] = ""
    session["table"] = 0
    session["items"] = []


def print_menu_records(records):
    if not records:
        print("No menu items found.")
        return

    print("\n{:<8} {:<30} {:<18} {:>10}".format(
        "Code", "Item Name", "Category", "Price"
    ))
    print("-" * 68)
    for item_id, item_name, category, price in records:
        print("{:<8} {:<30} {:<18} {:>10.2f}".format(
            item_id, item_name[:30], category[:18], price
        ))
    print("=" * 68)


# ---------------------------------------------------------
# 1. DISPLAY MENU
# ---------------------------------------------------------

def display_menu(cursor):
    print_header("RESTAURANT MENU")
    cursor.execute(
        "SELECT item_id, item_name, category, price "
        "FROM menu ORDER BY category, item_id"
    )
    print_menu_records(cursor.fetchall())


# ---------------------------------------------------------
# 2. SEARCH MENU
# ---------------------------------------------------------

def search_menu(cursor):
    print_header("SEARCH MENU")
    print("1. Search by item name")
    print("2. Search by category")
    print("3. Back")

    choice = input("Enter your choice: ").strip()

    if choice == "1":
        term = input("Enter item name to search: ").strip()
        cursor.execute(
            "SELECT item_id, item_name, category, price "
            "FROM menu WHERE item_name LIKE %s ORDER BY item_name",
            ("%" + term + "%",),
        )
    elif choice == "2":
        term = input("Enter category to search: ").strip()
        cursor.execute(
            "SELECT item_id, item_name, category, price "
            "FROM menu WHERE category LIKE %s ORDER BY item_name",
            ("%" + term + "%",),
        )
    elif choice == "3":
        return
    else:
        print("Invalid choice.")
        return

    records = cursor.fetchall()
    if not records:
        print("\nNo items matched your search.")
    else:
        print_menu_records(records)


# ---------------------------------------------------------
# 3. PLACE ORDER
# ---------------------------------------------------------

def place_order(cursor, session):
    print_header("PLACE ORDER")

    if not session["customer"]:
        session["customer"] = read_text("Enter customer name: ", 50)
        session["table"] = read_integer("Enter table number: ", minimum=1)

    print("Enter 0 as the item code when you have finished adding items.")

    while True:
        item_code = read_integer("\nEnter item code: ", minimum=0)

        if item_code == 0:
            if session["items"]:
                break
            print("The order is empty. Add at least one item.")
            continue

        cursor.execute(
            "SELECT item_name, price FROM menu WHERE item_id = %s",
            (item_code,),
        )
        item = cursor.fetchone()

        if item is None:
            print("Item code not found. Please check the menu.")
            continue

        quantity = read_integer("Enter quantity: ", minimum=1)
        item_name = item[0]
        price = money(item[1])
        amount = money(price * quantity)

        session["items"].append({
            "item_id": item_code,
            "name": item_name,
            "qty": quantity,
            "price": price,
            "amount": amount,
        })

        print(
            "{} x {} added. Amount: ₹{:.2f}".format(
                item_name, quantity, amount
            )
        )

        if not read_yes_no("Add another item? (Y/N): "):
            break

    if session["items"]:
        print("\nItems have been added to the current order.")
        print("Use option 4 to preview the bill or option 6 to save it.")


# ---------------------------------------------------------
# 4. CALCULATE BILL / PREVIEW
# ---------------------------------------------------------

def calculate_bill(session):
    if not session["items"]:
        print("\nThere are no items in the current order.")
        return None

    print_header("RESTAURANT BILL - PREVIEW")
    print("Customer : {}".format(session["customer"]))
    print("Table No : {}".format(session["table"]))
    print("Date     : {}".format(date.today()))
    print("-" * 68)
    print("{:<30} {:>6} {:>12} {:>14}".format(
        "Item Name", "Qty", "Price", "Amount"
    ))
    print("-" * 68)

    subtotal = ZERO
    for item in session["items"]:
        print("{:<30} {:>6} {:>12.2f} {:>14.2f}".format(
            item["name"][:30],
            item["qty"],
            item["price"],
            item["amount"],
        ))
        subtotal += item["amount"]

    subtotal = money(subtotal)
    tax_amount = calculate_tax(subtotal, session["tax_rate"])
    total = money(subtotal + tax_amount)

    print("-" * 68)
    print("{:<50} ₹{:>14.2f}".format("Subtotal", subtotal))
    print("{:<50} ₹{:>14.2f}".format(
        "Tax ({}%)".format(session["tax_rate"]), tax_amount
    ))
    print("-" * 68)
    print("{:<50} ₹{:>14.2f}".format("TOTAL", total))
    print("=" * 68)

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
    print("5. Custom rate (0% to 100%)")

    choice = input("Select tax bracket: ").strip()
    rates = {
        "1": Decimal("0.00"),
        "2": Decimal("5.00"),
        "3": Decimal("12.00"),
        "4": Decimal("18.00"),
    }

    if choice in rates:
        session["tax_rate"] = rates[choice]
    elif choice == "5":
        session["tax_rate"] = read_decimal(
            "Enter custom tax percentage: ",
            minimum=ZERO,
            maximum=Decimal("100.00"),
        )
    else:
        print("Invalid choice. The tax rate has not been changed.")
        return

    print("Tax rate set to {}%.".format(session["tax_rate"]))
    if session["items"]:
        print("The new rate will be used when this bill is calculated.")


# ---------------------------------------------------------
# 6. STORE BILL IN MYSQL
# ---------------------------------------------------------

def store_bill(conn, cursor, session):
    if not session["items"]:
        print("\nCannot save an empty order. Place an order first.")
        return

    subtotal = money(sum(
        (item["amount"] for item in session["items"]), ZERO
    ))
    tax_amount = calculate_tax(subtotal, session["tax_rate"])
    total = money(subtotal + tax_amount)

    try:
        # bill_id is generated by MySQL AUTO_INCREMENT.
        cursor.execute(
            """
            INSERT INTO bills
                (customer_name, table_no, bill_date, subtotal,
                 tax_rate, tax_amount, total, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["customer"],
                session["table"],
                date.today(),
                subtotal,
                session["tax_rate"],
                tax_amount,
                total,
                "PAID",
            ),
        )

        bill_id = cursor.lastrowid

        order_rows = [
            (
                bill_id,
                item["item_id"],
                item["name"],
                item["qty"],
                item["price"],
                item["amount"],
            )
            for item in session["items"]
        ]

        cursor.executemany(
            """
            INSERT INTO order_details
                (bill_id, item_id, item_name, quantity, price, amount)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            order_rows,
        )

        # Save the bill and all its items as one transaction.
        conn.commit()

        print_header("BILL SAVED SUCCESSFULLY")
        print("Bill ID  : {}".format(bill_id))
        print("Customer : {}".format(session["customer"]))
        print("Subtotal : ₹{:.2f}".format(subtotal))
        print("Tax      : ₹{:.2f}".format(tax_amount))
        print("Total    : ₹{:.2f}".format(total))
        print("\nThe bill and its items have been saved in MySQL.")

        reset_order(session)

    except mysql.connector.Error as err:
        conn.rollback()
        print("\nCould not save the bill. No partial bill was retained.")
        print("MySQL error:", err)


# ---------------------------------------------------------
# 7. VIEW PREVIOUS BILLS
# ---------------------------------------------------------

def view_previous_bills(cursor):
    print_header("PREVIOUS BILLS")
    cursor.execute(
        """
        SELECT bill_id, customer_name, bill_date, total, status
        FROM bills
        ORDER BY bill_id DESC
        """
    )
    records = cursor.fetchall()

    if not records:
        print("No bills are stored in the database.")
        return

    print("{:<10} {:<20} {:<14} {:>12}   {}".format(
        "Bill ID", "Customer", "Date", "Total", "Status"
    ))
    print("-" * 75)

    for row in records:
        print("{:<10} {:<20} {:<14} {:>12.2f}   {}".format(
            row[0], row[1][:20], str(row[2]), row[3], row[4]
        ))

    print("=" * 75)


# ---------------------------------------------------------
# 8. SEARCH BILL
# ---------------------------------------------------------

def search_bill(cursor):
    print_header("SEARCH BILL")
    bill_id = read_integer("Enter bill ID: ", minimum=1)

    cursor.execute(
        """
        SELECT bill_id, customer_name, table_no, bill_date,
               subtotal, tax_rate, tax_amount, total, status
        FROM bills
        WHERE bill_id = %s
        """,
        (bill_id,),
    )
    bill = cursor.fetchone()

    if bill is None:
        print("Bill not found.")
        return

    print_header("BILL DETAILS - {}".format(bill_id))
    print("Customer : {}".format(bill[1]))
    print("Table No : {}".format(bill[2]))
    print("Date     : {}".format(bill[3]))
    print("Status   : {}".format(bill[8]))
    print("-" * 68)
    print("{:<30} {:>6} {:>12} {:>14}".format(
        "Item Name", "Qty", "Price", "Amount"
    ))
    print("-" * 68)

    cursor.execute(
        """
        SELECT o.item_name, o.quantity, o.price, o.amount
        FROM order_details AS o
        WHERE o.bill_id = %s
        ORDER BY o.order_id
        """,
        (bill_id,),
    )

    for item in cursor.fetchall():
        print("{:<30} {:>6} {:>12.2f} {:>14.2f}".format(
            str(item[0])[:30], item[1], item[2], item[3]
        ))

    print("-" * 68)
    print("{:<50} ₹{:>14.2f}".format("Subtotal", bill[4]))
    print("{:<50} ₹{:>14.2f}".format(
        "Tax ({}%)".format(bill[5]), bill[6]
    ))
    print("-" * 68)
    print("{:<50} ₹{:>14.2f}".format("TOTAL", bill[7]))
    print("=" * 68)


# ---------------------------------------------------------
# 9. ADD MENU ITEM
# ---------------------------------------------------------

def add_menu_item(conn, cursor):
    print_header("ADD MENU ITEM")

    item_id = read_integer("Enter new item code: ", minimum=1)
    cursor.execute(
        "SELECT item_id FROM menu WHERE item_id = %s",
        (item_id,),
    )
    if cursor.fetchone():
        print("That item code already exists.")
        return

    item_name = read_text("Enter item name: ", 50)
    category = read_text("Enter category: ", 30)
    price = read_decimal(
        "Enter price: ",
        minimum=ZERO,
        maximum=MAX_PRICE,
    )

    try:
        cursor.execute(
            """
            INSERT INTO menu (item_id, item_name, category, price)
            VALUES (%s, %s, %s, %s)
            """,
            (item_id, item_name, category, price),
        )
        conn.commit()
        print("Menu item added successfully.")
    except mysql.connector.Error:
        conn.rollback()
        raise


# ---------------------------------------------------------
# 10. UPDATE MENU ITEM
# ---------------------------------------------------------

def update_menu_item(conn, cursor):
    print_header("UPDATE MENU ITEM")
    item_id = read_integer("Enter item code to update: ", minimum=1)

    cursor.execute(
        "SELECT item_name, category, price FROM menu WHERE item_id = %s",
        (item_id,),
    )
    current = cursor.fetchone()

    if current is None:
        print("Item code not found.")
        return

    print("\nCurrent details:")
    print("Name     :", current[0])
    print("Category :", current[1])
    print("Price    : ₹{:.2f}".format(current[2]))

    print("\n1. Update item name")
    print("2. Update category")
    print("3. Update price")
    print("4. Update all details")
    print("5. Back")

    choice = input("Select option: ").strip()

    if choice == "1":
        new_name = read_text("Enter new item name: ", 50)
        cursor.execute(
            "UPDATE menu SET item_name = %s WHERE item_id = %s",
            (new_name, item_id),
        )
    elif choice == "2":
        new_category = read_text("Enter new category: ", 30)
        cursor.execute(
            "UPDATE menu SET category = %s WHERE item_id = %s",
            (new_category, item_id),
        )
    elif choice == "3":
        new_price = read_decimal(
            "Enter new price: ",
            minimum=ZERO,
            maximum=MAX_PRICE,
        )
        cursor.execute(
            "UPDATE menu SET price = %s WHERE item_id = %s",
            (new_price, item_id),
        )
    elif choice == "4":
        new_name = read_text("Enter new item name: ", 50)
        new_category = read_text("Enter new category: ", 30)
        new_price = read_decimal(
            "Enter new price: ",
            minimum=ZERO,
            maximum=MAX_PRICE,
        )
        cursor.execute(
            """
            UPDATE menu
            SET item_name = %s, category = %s, price = %s
            WHERE item_id = %s
            """,
            (new_name, new_category, new_price, item_id),
        )
    elif choice == "5":
        return
    else:
        print("Invalid choice.")
        return

    try:
        conn.commit()
        print("Menu item updated successfully.")
    except mysql.connector.Error:
        conn.rollback()
        raise


# ---------------------------------------------------------
# 11. DELETE MENU ITEM
# ---------------------------------------------------------

def delete_menu_item(conn, cursor):
    print_header("DELETE MENU ITEM")
    item_id = read_integer("Enter item code to delete: ", minimum=1)

    cursor.execute(
        "SELECT item_name FROM menu WHERE item_id = %s",
        (item_id,),
    )
    item = cursor.fetchone()

    if item is None:
        print("Item code not found.")
        return

    print("Item found:", item[0])
    if not read_yes_no("Are you sure you want to delete it? (Y/N): "):
        print("Deletion cancelled.")
        return

    try:
        cursor.execute(
            "DELETE FROM menu WHERE item_id = %s",
            (item_id,),
        )
        conn.commit()
        print("Menu item deleted successfully.")
    except mysql.connector.IntegrityError:
        conn.rollback()
        print("\nThis item appears in an earlier bill and cannot be deleted.")
        print("Keeping it preserves the details of previous transactions.")
    except mysql.connector.Error:
        conn.rollback()
        raise


# ---------------------------------------------------------
# 12. VIEW TURNOVER
# ---------------------------------------------------------

def print_turnover(cursor, description, condition, values):
    cursor.execute(
        "SELECT COALESCE(SUM(total), 0) "
        "FROM bills WHERE status = 'PAID' AND " + condition,
        values,
    )
    total = money(cursor.fetchone()[0])
    print("\n{}: ₹{:.2f}".format(description, total))


def view_turnover(cursor):
    print_header("TURNOVER REPORT")
    print("1. Today's turnover")
    print("2. Monthly turnover")
    print("3. Turnover for a custom date")
    print("4. Back")

    choice = input("Select an option: ").strip()

    if choice == "1":
        today = date.today()
        print_turnover(
            cursor,
            "Turnover for {}".format(today),
            "bill_date = %s",
            (today,),
        )
    elif choice == "2":
        year = read_integer("Enter year (YYYY): ", minimum=1, maximum=9999)
        month = read_integer("Enter month (1-12): ", minimum=1, maximum=12)
        print_turnover(
            cursor,
            "Turnover for {:02d}/{}".format(month, year),
            "YEAR(bill_date) = %s AND MONTH(bill_date) = %s",
            (year, month),
        )
    elif choice == "3":
        entered_date = input("Enter date (YYYY-MM-DD): ").strip()
        try:
            selected_date = date.fromisoformat(entered_date)
        except ValueError:
            print("Invalid date. Use the YYYY-MM-DD format.")
            return

        print_turnover(
            cursor,
            "Turnover for {}".format(selected_date),
            "bill_date = %s",
            (selected_date,),
        )
    elif choice == "4":
        return
    else:
        print("Invalid choice.")


# ---------------------------------------------------------
# 13. CANCEL BILL OR CURRENT ORDER
# ---------------------------------------------------------

def cancel_bill(conn, cursor, session):
    print_header("CANCEL BILL / ORDER")
    print("1. Cancel a saved bill")
    print("2. Discard the current unsaved order")
    print("3. Back")

    choice = input("Select an option: ").strip()

    if choice == "2":
        if not session["items"]:
            print("There is no current order to discard.")
            return

        print(
            "Current order: {} item line(s) for {}".format(
                len(session["items"]), session["customer"]
            )
        )
        if read_yes_no("Discard this unsaved order? (Y/N): "):
            reset_order(session)
            print("Current order discarded.")
        else:
            print("Order was not changed.")
        return

    if choice == "3":
        return
    if choice != "1":
        print("Invalid choice.")
        return

    bill_id = read_integer("Enter bill ID to cancel: ", minimum=1)
    cursor.execute(
        "SELECT customer_name, total, status FROM bills WHERE bill_id = %s",
        (bill_id,),
    )
    bill = cursor.fetchone()

    if bill is None:
        print("Bill not found.")
        return

    if bill[2] == "CANCELLED":
        print("This bill has already been cancelled.")
        return

    print("\nBill ID  :", bill_id)
    print("Customer :", bill[0])
    print("Total    : ₹{:.2f}".format(bill[1]))
    print("Status   :", bill[2])

    if not read_yes_no("\nCancel this saved bill? (Y/N): "):
        print("Cancellation aborted.")
        return

    try:
        cursor.execute(
            "UPDATE bills SET status = 'CANCELLED' "
            "WHERE bill_id = %s AND status <> 'CANCELLED'",
            (bill_id,),
        )
        conn.commit()
        print("Bill {} has been cancelled.".format(bill_id))
        print("Cancelled bills are excluded from turnover reports.")
    except mysql.connector.Error:
        conn.rollback()
        raise


# ---------------------------------------------------------
# MAIN MENU
# ---------------------------------------------------------

def main():
    conn = connect_database()
    if conn is None:
        return

    cursor = None
    session_state = {
        "customer": "",
        "table": 0,
        "items": [],
        "tax_rate": DEFAULT_TAX_RATE,
    }

    try:
        cursor = conn.cursor()

        while True:
            print("\n" + "=" * 52)
            print("RESTAURANT BILLING SYSTEM".center(52))
            print("=" * 52)
            print("1.  Display Menu")
            print("2.  Search Menu")
            print("3.  Place Order")
            print("4.  Calculate Bill / Preview")
            print("5.  GST / Tax Calculation")
            print("6.  Store Bill in MySQL")
            print("7.  View Previous Bills")
            print("8.  Search Bill")
            print("9.  Add Menu Item")
            print("10. Update Menu Item")
            print("11. Delete Menu Item")
            print("12. View Turnover")
            print("13. Cancel Bill / Order")
            print("14. Exit")
            print("=" * 52)

            choice = input("Enter your choice: ").strip()

            try:
                if choice == "1":
                    display_menu(cursor)
                elif choice == "2":
                    search_menu(cursor)
                elif choice == "3":
                    place_order(cursor, session_state)
                elif choice == "4":
                    calculate_bill(session_state)
                elif choice == "5":
                    select_tax(session_state)
                elif choice == "6":
                    store_bill(conn, cursor, session_state)
                elif choice == "7":
                    view_previous_bills(cursor)
                elif choice == "8":
                    search_bill(cursor)
                elif choice == "9":
                    add_menu_item(conn, cursor)
                elif choice == "10":
                    update_menu_item(conn, cursor)
                elif choice == "11":
                    delete_menu_item(conn, cursor)
                elif choice == "12":
                    view_turnover(cursor)
                elif choice == "13":
                    cancel_bill(conn, cursor, session_state)
                elif choice == "14":
                    print("\nThank you for using the Restaurant Billing System.")
                    break
                else:
                    print("Invalid choice. Select a number from 1 to 14.")

            except mysql.connector.Error as err:
                conn.rollback()
                print("\nA database operation could not be completed.")
                print("MySQL error:", err)

    except (KeyboardInterrupt, EOFError):
        print("\nProgram interrupted. Closing the application.")
    except mysql.connector.Error as err:
        print("\nA database error occurred:", err)
    finally:
        if cursor is not None:
            cursor.close()
        if conn.is_connected():
            conn.close()
        print("Database connection closed.")


if __name__ == "__main__":
    main()
