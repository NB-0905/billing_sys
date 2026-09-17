import mysql.connector

# Connect to MySQL
mycon = mysql.connector.connect(
    host="localhost",
    user="root",
    password="your_password",
    database="goldbank"
)

cursor = mycon.cursor()


# Add a new gold loan
def add_loan():
    loan_id = int(input("Enter Loan ID: "))
    name = input("Enter Customer Name: ")
    phone = input("Enter Phone Number: ")
    weight = float(input("Enter Gold Weight (grams): "))
    value = float(input("Enter Gold Value: "))
    amount = float(input("Enter Loan Amount: "))
    rate = float(input("Enter Interest Rate (%): "))
    period = int(input("Enter Loan Period (months): "))

    query = """INSERT INTO gold_loan
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""

    data = (loan_id, name, phone, weight, value,
            amount, rate, period)

    cursor.execute(query, data)
    mycon.commit()

    print("Gold loan record added successfully.")


# Display all loans
def display_loans():
    cursor.execute("SELECT * FROM gold_loan")
    records = cursor.fetchall()

    print("\n--- GOLD LOAN RECORDS ---")

    for row in records:
        print("Loan ID       :", row[0])
        print("Customer Name :", row[1])
        print("Phone         :", row[2])
        print("Gold Weight   :", row[3], "grams")
        print("Gold Value    :", row[4])
        print("Loan Amount   :", row[5])
        print("Interest Rate :", row[6], "%")
        print("Loan Period   :", row[7], "months")
        print("-----------------------------")


# Search for a loan
def search_loan():
    loan_id = int(input("Enter Loan ID to search: "))

    query = "SELECT * FROM gold_loan WHERE loan_id = %s"
    cursor.execute(query, (loan_id,))

    row = cursor.fetchone()

    if row:
        print("\nLoan ID       :", row[0])
        print("Customer Name :", row[1])
        print("Phone         :", row[2])
        print("Gold Weight   :", row[3], "grams")
        print("Gold Value    :", row[4])
        print("Loan Amount   :", row[5])
        print("Interest Rate :", row[6], "%")
        print("Loan Period   :", row[7], "months")
    else:
        print("Loan record not found.")


# Calculate interest
def calculate_interest():
    loan_id = int(input("Enter Loan ID: "))

    query = """SELECT loan_amount, interest_rate, loan_period
               FROM gold_loan
               WHERE loan_id = %s"""

    cursor.execute(query, (loan_id,))
    row = cursor.fetchone()

    if row:
        amount = row[0]
        rate = row[1]
        months = row[2]

        interest = amount * rate * months / (12 * 100)
        total = amount + interest

        print("\nLoan Amount :", amount)
        print("Interest    :", round(interest, 2))
        print("Total Amount to be Paid :", round(total, 2))
    else:
        print("Loan record not found.")


# Update loan amount
def update_loan():
    loan_id = int(input("Enter Loan ID: "))
    new_amount = float(input("Enter New Loan Amount: "))

    query = """UPDATE gold_loan
               SET loan_amount = %s
               WHERE loan_id = %s"""

    cursor.execute(query, (new_amount, loan_id))
    mycon.commit()

    if cursor.rowcount > 0:
        print("Loan amount updated successfully.")
    else:
        print("Loan record not found.")


# Delete a loan record
def delete_loan():
    loan_id = int(input("Enter Loan ID to delete: "))

    query = "DELETE FROM gold_loan WHERE loan_id = %s"
    cursor.execute(query, (loan_id,))
    mycon.commit()

    if cursor.rowcount > 0:
        print("Loan record deleted successfully.")
    else:
        print("Loan record not found.")


# Main menu
while True:
    print("\n========== GOLD LOAN MANAGEMENT ==========")
    print("1. Add Gold Loan")
    print("2. Display All Loans")
    print("3. Search Loan")
    print("4. Calculate Interest")
    print("5. Update Loan")
    print("6. Delete Loan")
    print("7. Exit")
    print("==========================================")

    choice = int(input("Enter your choice: "))

    if choice == 1:
        add_loan()

    elif choice == 2:
        display_loans()

    elif choice == 3:
        search_loan()

    elif choice == 4:
        calculate_interest()

    elif choice == 5:
        update_loan()

    elif choice == 6:
        delete_loan()

    elif choice == 7:
        print("Thank you for using Gold Loan Management System.")
        break

    else:
        print("Invalid choice.")


cursor.close()
mycon.close()
