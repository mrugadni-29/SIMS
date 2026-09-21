import re
from werkzeug.security import generate_password_hash
from psycopg2 import Error
from extensions import get_db_connection, release_db_connection, table_exists


def log_audit(cur, user_id, action, table_name, record_id, ip_address="127.0.0.1"):
    """Helper to record audit trail in public.AuditLogs if table exists."""
    try:
        cur.execute('''
            INSERT INTO "AuditLogs" (user_id, action, table_name, record_id, action_time, ip_address)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        ''', (user_id, action, table_name, record_id, ip_address))
    except Exception as e:
        print(f"[AuditLog Error] {e}")


def get_employees(search=None, status=None):
    """
    Retrieves all Employees with their assigned PO counts and stock transaction counts.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = '''
            SELECT 
                u.user_id,
                u.username,
                u.email,
                r.role_name,
                u.status,
                (
                    SELECT COUNT(*) 
                    FROM "PurchaseOrders" po 
                    WHERE po.ordered_by = u.user_id
                ) AS assigned_pos_count,
                (
                    SELECT COUNT(*) 
                    FROM "StockTransactions" st 
                    WHERE st.user_id = u.user_id
                ) AS transactions_count
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE r.role_name = 'Employee'
        '''
        params = []

        if status and status in ["Active", "Inactive"]:
            query += " AND u.status = %s"
            params.append(status)

        if search and search.strip():
            query += " AND (u.username ILIKE %s OR u.email ILIKE %s)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " ORDER BY u.user_id ASC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        employees = []
        for r in rows:
            employees.append({
                "user_id": r[0],
                "username": r[1],
                "email": r[2],
                "role": r[3],
                "status": r[4],
                "assigned_pos_count": int(r[5] or 0),
                "transactions_count": int(r[6] or 0)
            })

        return employees, None
    except Error as e:
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def get_employee_by_id(user_id):
    """
    Retrieves full employee details, assigned purchase orders, and stock activity.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT u.user_id, u.username, u.email, r.role_name, u.status
            FROM "Users" u
            JOIN "Roles" r ON u.role_id = r.role_id
            WHERE u.user_id = %s AND r.role_name = 'Employee'
        ''', (user_id,))
        user_row = cur.fetchone()

        if not user_row:
            return None, "Employee not found"

        employee = {
            "user_id": user_row[0],
            "username": user_row[1],
            "email": user_row[2],
            "role": user_row[3],
            "status": user_row[4],
            "assigned_purchase_orders": [],
            "recent_transactions": []
        }

        # Fetch assigned purchase orders
        try:
            cur.execute('''
                SELECT po.purchase_order_id, po.supplier_id, po.total_amount, po.status, po.order_date
                FROM "PurchaseOrders" po
                WHERE po.ordered_by = %s
                ORDER BY po.purchase_order_id DESC
                LIMIT 10
            ''', (user_id,))
            for r in cur.fetchall():
                employee["assigned_purchase_orders"].append({
                    "purchase_order_id": r[0],
                    "supplier_id": r[1],
                    "total_amount": float(r[2] or 0),
                    "status": r[3],
                    "order_date": r[4].isoformat() if r[4] else None
                })
        except Exception:
            pass

        # Fetch stock transactions processed
        try:
            cur.execute('''
                SELECT st.transaction_id, p.product_name, st.transaction_type, st.quantity, st.transaction_date
                FROM "StockTransactions" st
                LEFT JOIN "Products" p ON st.product_id = p.product_id
                WHERE st.user_id = %s
                ORDER BY st.transaction_id DESC
                LIMIT 10
            ''', (user_id,))
            for r in cur.fetchall():
                employee["recent_transactions"].append({
                    "transaction_id": r[0],
                    "product_name": r[1] or f"Product #{r[0]}",
                    "transaction_type": r[2],
                    "quantity": r[3],
                    "transaction_date": r[4].isoformat() if r[4] else None
                })
        except Exception:
            pass

        return employee, None
    except Error as e:
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def create_employee(username, email, password, status="Active", creator_id=None):
    """
    Creates a new Employee. Strictly enforces role='Employee' on backend.
    """
    # Validation
    if not username or not username.strip():
        return None, "Username is required"
    if not email or not email.strip():
        return None, "Email is required"
    
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email.strip()):
        return None, "Invalid email address format"

    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters long"

    username = username.strip()
    email = email.strip().lower()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check duplicate username
        cur.execute('SELECT user_id FROM "Users" WHERE LOWER(username) = LOWER(%s)', (username,))
        if cur.fetchone():
            return None, "Username already exists"

        # Check duplicate email
        cur.execute('SELECT user_id FROM "Users" WHERE LOWER(email) = LOWER(%s)', (email,))
        if cur.fetchone():
            return None, "Email already exists"

        # Get role_id for 'Employee'
        cur.execute('SELECT role_id FROM "Roles" WHERE role_name = %s', ('Employee',))
        role_row = cur.fetchone()
        if not role_row:
            return None, "Employee role not configured in database"
        employee_role_id = role_row[0]

        # Hash password
        password_hash = generate_password_hash(password)

        # Insert user
        cur.execute('''
            INSERT INTO "Users" (username, email, password_hash, role_id, status)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING user_id, username, email, status
        ''', (username, email, password_hash, employee_role_id, status))
        new_user = cur.fetchone()

        # Audit log
        log_audit(cur, creator_id or new_user[0], "CREATE_EMPLOYEE", "Users", new_user[0])

        conn.commit()

        return {
            "user_id": new_user[0],
            "username": new_user[1],
            "email": new_user[2],
            "role": "Employee",
            "status": new_user[3]
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def update_employee(user_id, username=None, email=None, status=None, modifier_id=None):
    """
    Updates an employee's username, email, and/or status.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Ensure user exists and is an Employee
        cur.execute('''
            SELECT u.user_id, r.role_name 
            FROM "Users" u 
            JOIN "Roles" r ON u.role_id = r.role_id 
            WHERE u.user_id = %s
        ''', (user_id,))
        existing = cur.fetchone()
        if not existing:
            return None, "Employee not found"
        if existing[1] != "Employee":
            return None, "Cannot modify non-employee account via employee management"

        updates = []
        params = []

        if username and username.strip():
            username = username.strip()
            cur.execute('SELECT user_id FROM "Users" WHERE LOWER(username) = LOWER(%s) AND user_id != %s', (username, user_id))
            if cur.fetchone():
                return None, "Username already taken by another account"
            updates.append("username = %s")
            params.append(username)

        if email and email.strip():
            email = email.strip().lower()
            email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(email_regex, email):
                return None, "Invalid email address format"
            cur.execute('SELECT user_id FROM "Users" WHERE LOWER(email) = LOWER(%s) AND user_id != %s', (email, user_id))
            if cur.fetchone():
                return None, "Email already taken by another account"
            updates.append("email = %s")
            params.append(email)

        if status and status in ["Active", "Inactive"]:
            updates.append("status = %s")
            params.append(status)

        if not updates:
            return None, "No valid fields provided for update"

        params.append(user_id)
        query = f'UPDATE "Users" SET {", ".join(updates)} WHERE user_id = %s RETURNING user_id, username, email, status'
        cur.execute(query, tuple(params))
        updated = cur.fetchone()

        log_audit(cur, modifier_id or user_id, "UPDATE_EMPLOYEE", "Users", user_id)

        conn.commit()
        return {
            "user_id": updated[0],
            "username": updated[1],
            "email": updated[2],
            "role": "Employee",
            "status": updated[3]
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def update_employee_status(user_id, status, modifier_id=None):
    """
    Activates or deactivates an employee.
    """
    if status not in ["Active", "Inactive"]:
        return None, "Status must be either Active or Inactive"

    if modifier_id and str(modifier_id) == str(user_id):
        return None, "You cannot change your own account status"

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT u.user_id, r.role_name 
            FROM "Users" u 
            JOIN "Roles" r ON u.role_id = r.role_id 
            WHERE u.user_id = %s
        ''', (user_id,))
        existing = cur.fetchone()
        if not existing:
            return None, "Employee not found"
        if existing[1] != "Employee":
            return None, "Can only update status of Employee accounts"

        cur.execute('''
            UPDATE "Users" 
            SET status = %s 
            WHERE user_id = %s 
            RETURNING user_id, username, email, status
        ''', (status, user_id))
        updated = cur.fetchone()

        log_audit(cur, modifier_id or user_id, f"EMPLOYEE_STATUS_{status.upper()}", "Users", user_id)

        conn.commit()
        return {
            "user_id": updated[0],
            "username": updated[1],
            "email": updated[2],
            "role": "Employee",
            "status": updated[3]
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)
