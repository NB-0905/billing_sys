import mysql.connector
def connect():
    mydb = mysql.connector.connect(host="localhost", user="wsl", password="wsl", database='restaurant')
    return mydb
mydb = connect()
command="""INSERT INTO menu (item_id, item_name, category, price) VALUES 
(101, 'Chicken Biriyani', 'Main Course', 180.00),
(102, 'Veg Biriyani', 'Main Course', 130.00),
(103, 'Fried Rice', 'Main Course', 140.00),
(104, 'Chicken 65', 'Starter', 160.00),
(105, 'Gobi Manchurian', 'Starter', 120.00),
(106, 'French Fries', 'Snacks', 90.00),
(107, 'Lime Juice', 'Beverages', 40.00),
(108, 'Fresh Lime Soda', 'Beverages', 50.00),
(109, 'Ice Cream', 'Dessert', 70.00),
(110, 'Chocolate Cake', 'Dessert', 90.00);"""
mycursor = mydb.cursor()
mycursor.execute(command)
mydb.commit()
for i in mycursor:
    print(i)



