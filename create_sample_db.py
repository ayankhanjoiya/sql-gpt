import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

def create_extended_sample_database():
    """Create a more comprehensive sample database with additional tables and data"""
    
    conn = sqlite3.connect('extended_sample_data.db')
    cursor = conn.cursor()
    
    # Create customers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY,
            company_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            registration_date DATE NOT NULL
        )
    ''')
    
    # Create products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL,
            units_in_stock INTEGER NOT NULL,
            supplier TEXT NOT NULL
        )
    ''')
    
    # Create orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER,
            employee_id INTEGER,
            order_date DATE NOT NULL,
            ship_date DATE,
            ship_city TEXT,
            ship_country TEXT,
            freight REAL NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    # Create order_details table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_details (
            order_id INTEGER,
            product_id INTEGER,
            unit_price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            discount REAL DEFAULT 0,
            PRIMARY KEY (order_id, product_id),
            FOREIGN KEY (order_id) REFERENCES orders (order_id),
            FOREIGN KEY (product_id) REFERENCES products (product_id)
        )
    ''')
    
    # Enhanced employees table (if not exists)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            salary REAL NOT NULL,
            hire_date DATE NOT NULL,
            age INTEGER NOT NULL,
            manager_id INTEGER,
            email TEXT,
            phone TEXT,
            FOREIGN KEY (manager_id) REFERENCES employees (id)
        )
    ''')
    
    # Sample data for customers
    customers_data = [
        (1, 'Tech Solutions Inc', 'John Anderson', 'j.anderson@techsol.com', '+1-555-0101', 'New York', 'USA', '2022-01-15'),
        (2, 'Global Enterprises', 'Sarah Johnson', 's.johnson@global.com', '+1-555-0102', 'Los Angeles', 'USA', '2022-02-20'),
        (3, 'Innovation Corp', 'Michael Brown', 'm.brown@innovation.com', '+1-555-0103', 'Chicago', 'USA', '2022-03-10'),
        (4, 'Future Systems', 'Emily Davis', 'e.davis@future.com', '+44-555-0104', 'London', 'UK', '2022-04-05'),
        (5, 'Digital Dynamics', 'Robert Wilson', 'r.wilson@digital.com', '+49-555-0105', 'Berlin', 'Germany', '2022-05-12'),
        (6, 'Smart Solutions', 'Lisa Garcia', 'l.garcia@smart.com', '+33-555-0106', 'Paris', 'France', '2022-06-18'),
        (7, 'Advanced Tech', 'David Miller', 'd.miller@advanced.com', '+1-555-0107', 'Toronto', 'Canada', '2022-07-22'),
        (8, 'NextGen Industries', 'Jennifer Taylor', 'j.taylor@nextgen.com', '+61-555-0108', 'Sydney', 'Australia', '2022-08-30')
    ]
    
    # Sample data for products
    products_data = [
        (1, 'Enterprise Software License', 'Software', 5000.00, 100, 'Microsoft Corp'),
        (2, 'Database Management System', 'Software', 3500.00, 50, 'Oracle Inc'),
        (3, 'Cloud Storage Service', 'Cloud Services', 1200.00, 200, 'Amazon Web Services'),
        (4, 'Security Consultation', 'Consulting', 8000.00, 25, 'CyberSec Solutions'),
        (5, 'Data Analytics Platform', 'Analytics', 6500.00, 75, 'Tableau Inc'),
        (6, 'Mobile App Development', 'Development', 15000.00, 30, 'AppDev Studios'),
        (7, 'Network Infrastructure', 'Hardware', 12000.00, 40, 'Cisco Systems'),
        (8, 'Training Program', 'Education', 2500.00, 150, 'TechEd Institute'),
        (9, 'Support & Maintenance', 'Support', 1800.00, 300, 'TechSupport Ltd'),
        (10, 'Business Intelligence Suite', 'Analytics', 7200.00, 60, 'PowerBI Corp')
    ]
    
    # Enhanced employees data
    employees_data = [
        (1, 'John Doe', 'Engineering', 75000, '2022-01-15', 28, None, 'j.doe@company.com', '+1-555-1001'),
        (2, 'Jane Smith', 'Marketing', 65000, '2021-03-20', 32, None, 'j.smith@company.com', '+1-555-1002'),
        (3, 'Bob Johnson', 'Sales', 55000, '2023-06-10', 25, 2, 'b.johnson@company.com', '+1-555-1003'),
        (4, 'Alice Brown', 'Engineering', 80000, '2020-11-05', 35, 1, 'a.brown@company.com', '+1-555-1004'),
        (5, 'Charlie Wilson', 'HR', 60000, '2022-08-12', 29, None, 'c.wilson@company.com', '+1-555-1005'),
        (6, 'Diana Davis', 'Sales', 58000, '2023-02-28', 27, 2, 'd.davis@company.com', '+1-555-1006'),
        (7, 'Eva Martinez', 'Marketing', 67000, '2021-09-15', 31, 2, 'e.martinez@company.com', '+1-555-1007'),
        (8, 'Frank Lee', 'Engineering', 72000, '2022-04-03', 26, 1, 'f.lee@company.com', '+1-555-1008'),
        (9, 'Grace Kim', 'Sales', 62000, '2023-01-12', 30, 2, 'g.kim@company.com', '+1-555-1009'),
        (10, 'Henry Adams', 'Engineering', 78000, '2021-12-20', 33, 1, 'h.adams@company.com', '+1-555-1010')
    ]
    
    # Generate sample orders data
    orders_data = []
    order_details_data = []
    order_id = 1
    
    # Generate orders for the past year
    start_date = datetime.now() - timedelta(days=365)
    
    for i in range(100):  # Generate 100 orders
        order_date = start_date + timedelta(days=random.randint(0, 365))
        ship_date = order_date + timedelta(days=random.randint(1, 7))
        customer_id = random.randint(1, 8)
        employee_id = random.choice([3, 6, 9])  # Sales employees
        
        freight = round(random.uniform(50, 500), 2)
        
        orders_data.append((
            order_id,
            customer_id,
            employee_id,
            order_date.strftime('%Y-%m-%d'),
            ship_date.strftime('%Y-%m-%d'),
            customers_data[customer_id-1][6],  # ship_city from customer data
            customers_data[customer_id-1][7],  # ship_country from customer data
            freight
        ))
        
        # Generate 1-5 order details per order
        num_products = random.randint(1, 5)
        selected_products = random.sample(range(1, 11), num_products)
        
        for product_id in selected_products:
            quantity = random.randint(1, 10)
            unit_price = products_data[product_id-1][3]  # Get unit price from products
            discount = round(random.choice([0, 0, 0, 0.05, 0.1, 0.15]), 2)  # Most orders have no discount
            
            order_details_data.append((
                order_id,
                product_id,
                unit_price,
                quantity,
                discount
            ))
        
        order_id += 1
    
    # Insert all data
    cursor.executemany('INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?, ?, ?, ?)', customers_data)
    cursor.executemany('INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?, ?)', products_data)
    cursor.executemany('INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', employees_data)
    cursor.executemany('INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)', orders_data)
    cursor.executemany('INSERT OR REPLACE INTO order_details VALUES (?, ?, ?, ?, ?)', order_details_data)
    
    conn.commit()
    conn.close()
    
    print("Extended sample database created successfully!")
    print("Tables created: customers, products, employees, orders, order_details")
    print(f"Data inserted: {len(customers_data)} customers, {len(products_data)} products, {len(employees_data)} employees, {len(orders_data)} orders")

if __name__ == "__main__":
    create_extended_sample_database()
