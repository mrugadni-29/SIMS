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


def get_categories(search=None):
    """
    Retrieves categories along with the count of products in each category.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = '''
            SELECT 
                c.category_id,
                c.category_name,
                c.description,
                COUNT(p.product_id) AS product_count
            FROM "Categories" c
            LEFT JOIN "Products" p ON c.category_id = p.category_id
        '''
        params = []

        if search and search.strip():
            query += " WHERE c.category_name ILIKE %s OR c.description ILIKE %s"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        query += " GROUP BY c.category_id, c.category_name, c.description ORDER BY c.category_id ASC"

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        categories = []
        for r in rows:
            categories.append({
                "category_id": r[0],
                "category_name": r[1],
                "description": r[2] or "",
                "product_count": int(r[3] or 0)
            })

        return categories, None
    except Error as e:
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def get_category_by_id(category_id):
    """
    Retrieves category details and its assigned products.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT category_id, category_name, description
            FROM "Categories"
            WHERE category_id = %s
        ''', (category_id,))
        row = cur.fetchone()

        if not row:
            return None, "Category not found"

        category = {
            "category_id": row[0],
            "category_name": row[1],
            "description": row[2] or "",
            "products": []
        }

        # Fetch products in this category
        cur.execute('''
            SELECT p.product_id, p.product_name, p.sku, p.selling_price, p.status, COALESCE(i.quantity_available, 0)
            FROM "Products" p
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE p.category_id = %s
            ORDER BY p.product_name ASC
        ''', (category_id,))

        for pr in cur.fetchall():
            category["products"].append({
                "product_id": pr[0],
                "product_name": pr[1],
                "sku": pr[2],
                "selling_price": float(pr[3] or 0),
                "status": pr[4],
                "quantity_available": int(pr[5])
            })

        return category, None
    except Error as e:
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def create_category(category_name, description=None, creator_id=None):
    """
    Creates a new category. Validates duplicate category name.
    """
    if not category_name or not category_name.strip():
        return None, "Category name is required"

    category_name = category_name.strip()
    description = description.strip() if description else ""

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Check duplicate
        cur.execute('SELECT category_id FROM "Categories" WHERE LOWER(category_name) = LOWER(%s)', (category_name,))
        if cur.fetchone():
            return None, "Category already exists"

        cur.execute('''
            INSERT INTO "Categories" (category_name, description)
            VALUES (%s, %s)
            RETURNING category_id, category_name, description
        ''', (category_name, description))
        row = cur.fetchone()

        log_audit(cur, creator_id or 1, "CREATE_CATEGORY", "Categories", row[0])

        conn.commit()

        return {
            "category_id": row[0],
            "category_name": row[1],
            "description": row[2] or "",
            "product_count": 0
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def update_category(category_id, category_name=None, description=None, modifier_id=None):
    """
    Updates an existing category.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT category_id, category_name, description FROM "Categories" WHERE category_id = %s', (category_id,))
        existing = cur.fetchone()
        if not existing:
            return None, "Category not found"

        updates = []
        params = []

        if category_name and category_name.strip():
            name = category_name.strip()
            cur.execute('SELECT category_id FROM "Categories" WHERE LOWER(category_name) = LOWER(%s) AND category_id != %s', (name, category_id))
            if cur.fetchone():
                return None, "Category name already exists"
            updates.append("category_name = %s")
            params.append(name)

        if description is not None:
            updates.append("description = %s")
            params.append(description.strip())

        if not updates:
            return None, "No fields to update"

        params.append(category_id)
        cur.execute(f'UPDATE "Categories" SET {", ".join(updates)} WHERE category_id = %s RETURNING category_id, category_name, description', tuple(params))
        row = cur.fetchone()

        log_audit(cur, modifier_id or 1, "UPDATE_CATEGORY", "Categories", category_id)

        conn.commit()

        return {
            "category_id": row[0],
            "category_name": row[1],
            "description": row[2] or ""
        }, None
    except Error as e:
        conn.rollback()
        return None, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)


def delete_category(category_id, modifier_id=None):
    """
    Deletes a category safely. Rejects if products are assigned.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('SELECT category_id FROM "Categories" WHERE category_id = %s', (category_id,))
        if not cur.fetchone():
            return False, "Category not found"

        # Check assigned products
        cur.execute('SELECT COUNT(*) FROM "Products" WHERE category_id = %s', (category_id,))
        prod_count = cur.fetchone()[0]
        if prod_count > 0:
            return False, f"Category cannot be deleted because {prod_count} product(s) are assigned to it"

        cur.execute('DELETE FROM "Categories" WHERE category_id = %s', (category_id,))

        log_audit(cur, modifier_id or 1, "DELETE_CATEGORY", "Categories", category_id)

        conn.commit()
        return True, None
    except Error as e:
        conn.rollback()
        return False, f"Database error: {str(e)}"
    finally:
        cur.close()
        release_db_connection(conn)
