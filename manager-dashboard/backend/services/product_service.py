from decimal import Decimal
from psycopg2 import Error
from extensions import get_db_connection, release_db_connection


def log_audit(cur, user_id, action, table_name, record_id, ip_address="127.0.0.1"):
    try:
        cur.execute('''
            INSERT INTO "AuditLogs" (user_id, action, table_name, record_id, action_time, ip_address)
            VALUES (%s, %s, %s, %s, NOW(), %s)
        ''', (user_id, action, table_name, record_id, ip_address))
    except Exception as e:
        print(f"[AuditLog Error] {e}")


def get_products(search=None, category_id=None, status=None, sort_by="name", sort_order="asc"):
    """
    Retrieves products joined with Categories and Inventory quantities.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = '''
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                p.category_id,
                COALESCE(c.category_name, 'Unassigned') AS category_name,
                p.selling_price,
                p.reorder_level,
                p.status,
                COALESCE(i.quantity_available, 0) AS quantity_available,
                i.last_updated
            FROM "Products" p
            LEFT JOIN "Categories" c ON p.category_id = c.category_id
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE 1=1
        '''
        params = []

        if category_id:
            query += " AND p.category_id = %s"
            params.append(category_id)

        if status:
            if status == "Low Stock":
                query += " AND COALESCE(i.quantity_available, 0) <= p.reorder_level"
            elif status in ["Active", "Inactive"]:
                query += " AND p.status = %s"
                params.append(status)

        if search and search.strip():
            query += " AND (p.product_name ILIKE %s OR p.sku ILIKE %s)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        # Sorting
        order_direction = "DESC" if sort_order and sort_order.lower() == "desc" else "ASC"
        if sort_by == "stock":
            query += f" ORDER BY quantity_available {order_direction}"
        elif sort_by == "reorder":
            query += f" ORDER BY p.reorder_level {order_direction}"
        elif sort_by == "price":
            query += f" ORDER BY p.selling_price {order_direction}"
        else:
            query += f" ORDER BY p.product_name {order_direction}"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        products = []
        for r in rows:
            qty = int(r[8])
            reorder = int(r[6])
            stock_status = "OUT OF STOCK" if qty == 0 else "LOW STOCK" if qty <= reorder else "IN STOCK"

            products.append({
                "product_id": r[0],
                "product_name": r[1],
                "sku": r[2],
                "category_id": r[3],
                "category_name": r[4],
                "selling_price": float(r[5] or 0),
                "reorder_level": reorder,
                "status": r[7],
                "quantity_available": qty,
                "stock_status": stock_status,
                "last_updated": r[9].isoformat() if r[9] else None
            })

        return products, None
    except Error as e:
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def get_product_by_id(product_id):
    """
    Retrieves full product details including category and inventory records.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT 
                p.product_id,
                p.product_name,
                p.sku,
                p.category_id,
                COALESCE(c.category_name, 'Unassigned') AS category_name,
                c.description AS category_description,
                p.selling_price,
                p.reorder_level,
                p.status,
                COALESCE(i.quantity_available, 0) AS quantity_available,
                i.last_updated
            FROM "Products" p
            LEFT JOIN "Categories" c ON p.category_id = c.category_id
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE p.product_id = %s
        ''', (product_id,))
        r = cur.fetchone()

        if not r:
            return None, "Product not found"

        qty = int(r[9])
        reorder = int(r[7])
        stock_status = "OUT OF STOCK" if qty == 0 else "LOW STOCK" if qty <= reorder else "IN STOCK"

        product = {
            "product_id": r[0],
            "product_name": r[1],
            "sku": r[2],
            "category_id": r[3],
            "category_name": r[4],
            "category_description": r[5] or "",
            "selling_price": float(r[6] or 0),
            "reorder_level": reorder,
            "status": r[8],
            "quantity_available": qty,
            "stock_status": stock_status,
            "last_updated": r[10].isoformat() if r[10] else None
        }

        return product, None
    except Error as e:
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def create_product(product_name, category_id, sku, selling_price, reorder_level=10, initial_stock=0, status="Active", creator_id=None):
    """
    Creates a new product and initializes its corresponding inventory record.
    """
    if not product_name or not product_name.strip():
        return None, "Product name is required"
    if not category_id:
        return None, "Category is required"
    if not sku or not sku.strip():
        return None, "SKU is required"

    try:
        selling_price = float(selling_price)
        if selling_price < 0:
            return None, "Selling price must be non-negative"
    except (ValueError, TypeError):
        return None, "Invalid selling price format"

    try:
        reorder_level = int(reorder_level)
        if reorder_level < 0:
            return None, "Reorder level must be non-negative"
    except (ValueError, TypeError):
        return None, "Invalid reorder level format"

    try:
        initial_stock = int(initial_stock or 0)
        if initial_stock < 0:
            return None, "Initial stock cannot be negative"
    except (ValueError, TypeError):
        return None, "Invalid initial stock quantity"

    product_name = product_name.strip()
    sku = sku.strip().upper()

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Verify category exists
        cur.execute('SELECT category_id, category_name FROM "Categories" WHERE category_id = %s', (category_id,))
        cat_row = cur.fetchone()
        if not cat_row:
            return None, "Selected category does not exist"

        # Verify SKU uniqueness
        cur.execute('SELECT product_id FROM "Products" WHERE LOWER(sku) = LOWER(%s)', (sku,))
        if cur.fetchone():
            return None, f"Product SKU '{sku}' already exists"

        # Insert product
        cur.execute('''
            INSERT INTO "Products" (product_name, category_id, sku, selling_price, reorder_level, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING product_id, product_name, sku, selling_price, reorder_level, status
        ''', (product_name, category_id, sku, selling_price, reorder_level, status))
        new_prod = cur.fetchone()
        product_id = new_prod[0]

        # Initialize corresponding Inventory record
        cur.execute('''
            INSERT INTO "Inventory" (product_id, quantity_available, last_updated)
            VALUES (%s, %s, NOW())
            RETURNING inventory_id, quantity_available
        ''', (product_id, initial_stock))
        inv_row = cur.fetchone()

        log_audit(cur, creator_id or 1, "CREATE_PRODUCT", "Products", product_id)

        conn.commit()

        stock_status = "OUT OF STOCK" if initial_stock == 0 else "LOW STOCK" if initial_stock <= reorder_level else "IN STOCK"

        return {
            "product_id": product_id,
            "product_name": new_prod[1],
            "category_id": category_id,
            "category_name": cat_row[1],
            "sku": new_prod[2],
            "selling_price": float(new_prod[3]),
            "reorder_level": int(new_prod[4]),
            "status": new_prod[5],
            "quantity_available": int(inv_row[1]),
            "stock_status": stock_status
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def update_product(product_id, product_name=None, category_id=None, sku=None, selling_price=None, reorder_level=None, status=None, modifier_id=None):
    """
    Updates product master data.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT product_id FROM "Products" WHERE product_id = %s', (product_id,))
        if not cur.fetchone():
            return None, "Product not found"

        updates = []
        params = []

        if product_name and product_name.strip():
            updates.append("product_name = %s")
            params.append(product_name.strip())

        if category_id:
            cur.execute('SELECT category_id FROM "Categories" WHERE category_id = %s', (category_id,))
            if not cur.fetchone():
                return None, "Selected category does not exist"
            updates.append("category_id = %s")
            params.append(category_id)

        if sku and sku.strip():
            clean_sku = sku.strip().upper()
            cur.execute('SELECT product_id FROM "Products" WHERE LOWER(sku) = LOWER(%s) AND product_id != %s', (clean_sku, product_id))
            if cur.fetchone():
                return None, f"SKU '{clean_sku}' is already assigned to another product"
            updates.append("sku = %s")
            params.append(clean_sku)

        if selling_price is not None:
            try:
                price = float(selling_price)
                if price < 0:
                    return None, "Selling price must be non-negative"
                updates.append("selling_price = %s")
                params.append(price)
            except ValueError:
                return None, "Invalid selling price format"

        if reorder_level is not None:
            try:
                r_level = int(reorder_level)
                if r_level < 0:
                    return None, "Reorder level must be non-negative"
                updates.append("reorder_level = %s")
                params.append(r_level)
            except ValueError:
                return None, "Invalid reorder level format"

        if status and status in ["Active", "Inactive"]:
            updates.append("status = %s")
            params.append(status)

        if not updates:
            return None, "No fields to update"

        params.append(product_id)
        query = f'UPDATE "Products" SET {", ".join(updates)} WHERE product_id = %s RETURNING product_id, product_name, sku, category_id, selling_price, reorder_level, status'
        cur.execute(query, tuple(params))
        row = cur.fetchone()

        log_audit(cur, modifier_id or 1, "UPDATE_PRODUCT", "Products", product_id)

        conn.commit()

        # Fetch category name
        cur.execute('SELECT category_name FROM "Categories" WHERE category_id = %s', (row[3],))
        cat_name = cur.fetchone()[0]

        # Fetch inventory
        cur.execute('SELECT quantity_available FROM "Inventory" WHERE product_id = %s', (product_id,))
        inv_row = cur.fetchone()
        qty = int(inv_row[0]) if inv_row else 0
        reorder = int(row[5])
        stock_status = "OUT OF STOCK" if qty == 0 else "LOW STOCK" if qty <= reorder else "IN STOCK"

        return {
            "product_id": row[0],
            "product_name": row[1],
            "sku": row[2],
            "category_id": row[3],
            "category_name": cat_name,
            "selling_price": float(row[4]),
            "reorder_level": reorder,
            "status": row[6],
            "quantity_available": qty,
            "stock_status": stock_status
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def update_product_status(product_id, status, modifier_id=None):
    """
    Toggles product active or inactive status.
    """
    if status not in ["Active", "Inactive"]:
        return None, "Status must be Active or Inactive"

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT product_id FROM "Products" WHERE product_id = %s', (product_id,))
        if not cur.fetchone():
            return None, "Product not found"

        cur.execute('UPDATE "Products" SET status = %s WHERE product_id = %s RETURNING product_id, product_name, status', (status, product_id))
        row = cur.fetchone()

        log_audit(cur, modifier_id or 1, f"PRODUCT_STATUS_{status.upper()}", "Products", product_id)

        conn.commit()

        return {
            "product_id": row[0],
            "product_name": row[1],
            "status": row[2]
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)
