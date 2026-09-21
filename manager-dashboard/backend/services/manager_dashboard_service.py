from extensions import get_db_connection, release_db_connection, table_exists
import psycopg2
from psycopg2.extras import RealDictCursor


# =============================================================================
# CURSOR-LEVEL QUERY WORKERS (USED FOR BOTH INDIVIDUAL AND CONSOLIDATED QUERIES)
# =============================================================================

def _get_summary_with_cur(cur):
    """Calculates all 8 summary metrics in a single optimized query."""
    cur.execute('''
        SELECT
            (SELECT COUNT(*) FROM "Products") AS total_products,
            (SELECT COUNT(*) FROM "Products" p JOIN "Inventory" i ON p.product_id = i.product_id WHERE i.quantity_available <= p.reorder_level AND i.quantity_available > 0) AS low_stock_products,
            (SELECT COUNT(*) FROM "Inventory" WHERE quantity_available = 0) AS out_of_stock_products,
            0 AS pending_stock_requests,
            (SELECT COUNT(*) FROM "SupplierQuotations" WHERE status ILIKE 'Pending') AS pending_quotations,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE 'Pending') AS pending_purchase_orders,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE ANY (ARRAY['Shipped', 'In Transit', 'Accepted'])) AS orders_in_transit,
            (SELECT COUNT(*) FROM "Users" u JOIN "Roles" r ON u.role_id = r.role_id WHERE r.role_name = 'Employee' AND u.status = 'Active') AS total_employees;
    ''')
    row = cur.fetchone()
    return {
        "total_products": int(row[0] or 0),
        "low_stock_products": int(row[1] or 0),
        "out_of_stock_products": int(row[2] or 0),
        "pending_stock_requests": int(row[3] or 0),
        "pending_quotations": int(row[4] or 0),
        "pending_purchase_orders": int(row[5] or 0),
        "orders_in_transit": int(row[6] or 0),
        "total_employees": int(row[7] or 0)
    }


def _get_inventory_with_cur(cur):
    """Calculates inventory status breakdown and top categories."""
    cur.execute('''
        SELECT 
            COUNT(*) FILTER (WHERE i.quantity_available > p.reorder_level) AS in_stock,
            COUNT(*) FILTER (WHERE i.quantity_available <= p.reorder_level AND i.quantity_available > 0) AS low_stock,
            COUNT(*) FILTER (WHERE i.quantity_available = 0) AS out_of_stock,
            COALESCE(SUM(i.quantity_available), 0) AS total_units
        FROM "Products" p
        LEFT JOIN "Inventory" i ON p.product_id = i.product_id
    ''')
    row = cur.fetchone()
    in_stock = int(row[0] or 0)
    low_stock = int(row[1] or 0)
    out_of_stock = int(row[2] or 0)
    total_units = int(row[3] or 0)

    category_breakdown = []
    try:
        cur.execute('''
            SELECT 
                c.category_id,
                c.category_name,
                COUNT(p.product_id) AS product_count,
                COALESCE(SUM(i.quantity_available), 0) AS total_stock
            FROM "Categories" c
            LEFT JOIN "Products" p ON c.category_id = p.category_id
            LEFT JOIN "Inventory" i ON p.product_id = i.product_id
            GROUP BY c.category_id, c.category_name
            ORDER BY product_count DESC
            LIMIT 5
        ''')
        for r in cur.fetchall():
            category_breakdown.append({
                "category_id": r[0],
                "category_name": r[1],
                "product_count": r[2],
                "total_stock": int(r[3] or 0)
            })
    except Exception:
        pass

    return {
        "status_breakdown": {
            "in_stock": in_stock,
            "low_stock": low_stock,
            "out_of_stock": out_of_stock,
            "total_units": total_units
        },
        "category_breakdown": category_breakdown
    }


def _get_procurement_with_cur(cur):
    """Calculates procurement funnel metrics."""
    cur.execute('''
        SELECT
            (SELECT COUNT(*) FROM "SupplierQuotations") AS total_quo,
            (SELECT COUNT(*) FROM "SupplierQuotations" WHERE status ILIKE 'Pending') AS pending_quo,
            (SELECT COUNT(*) FROM "SupplierQuotations" WHERE status ILIKE 'Approved') AS approved_quo,
            (SELECT COUNT(*) FROM "PurchaseOrders") AS total_pos,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE 'Pending') AS pending_pos,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE 'Accepted') AS accepted_pos,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE ANY (ARRAY['Shipped', 'In Transit'])) AS shipped_pos,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE ANY (ARRAY['Delivered', 'Received'])) AS delivered_pos,
            (SELECT COUNT(*) FROM "PurchaseOrders" WHERE status ILIKE 'Completed') AS completed_pos;
    ''')
    row = cur.fetchone()
    return {
        "stock_requests": {
            "total": 0,
            "pending": 0
        },
        "quotations": {
            "total": int(row[0] or 0),
            "pending": int(row[1] or 0),
            "approved": int(row[2] or 0)
        },
        "purchase_orders": {
            "total": int(row[3] or 0),
            "pending": int(row[4] or 0),
            "accepted": int(row[5] or 0),
            "shipped": int(row[6] or 0),
            "delivered": int(row[7] or 0),
            "completed": int(row[8] or 0)
        }
    }


def _get_pending_actions_with_cur(cur):
    """Gathers actionable items requiring attention."""
    actions = []
    # 1. Low stock alerts
    try:
        cur.execute('''
            SELECT p.product_id, p.product_name, i.quantity_available, p.reorder_level
            FROM "Products" p
            JOIN "Inventory" i ON p.product_id = i.product_id
            WHERE i.quantity_available <= p.reorder_level
            ORDER BY i.quantity_available ASC
            LIMIT 5
        ''')
        for r in cur.fetchall():
            actions.append({
                "type": "LOW_STOCK",
                "severity": "high" if r[2] == 0 else "medium",
                "title": f"Stock Alert: {r[1]}",
                "description": f"Current stock is {r[2]} (Reorder level: {r[3]}). Reorder required.",
                "reference_id": r[0],
                "action_label": "Create Stock Request",
                "action_target": "stock-requests"
            })
    except Exception:
        pass

    # 2. Pending quotations
    try:
        cur.execute('''
            SELECT quotation_id, supplier_id, (quoted_price * quantity) AS total_amount, quotation_date
            FROM "SupplierQuotations"
            WHERE status ILIKE 'Pending'
            ORDER BY quotation_id DESC
            LIMIT 5
        ''')
        for r in cur.fetchall():
            actions.append({
                "type": "PENDING_QUOTATION",
                "severity": "medium",
                "title": f"Quotation #{r[0]} Awaiting Approval",
                "description": f"Supplier #{r[1]} submitted quotation for INR {float(r[2] or 0):,.2f}.",
                "reference_id": r[0],
                "action_label": "Review Quotation",
                "action_target": "quotations"
            })
    except Exception:
        pass

    # 3. Pending Purchase Orders
    try:
        cur.execute('''
            SELECT purchase_order_id, supplier_id, total_amount, status
            FROM "PurchaseOrders"
            WHERE status ILIKE 'Pending'
            ORDER BY purchase_order_id DESC
            LIMIT 5
        ''')
        for r in cur.fetchall():
            actions.append({
                "type": "PENDING_PO",
                "severity": "high",
                "title": f"Purchase Order #{r[0]} Pending",
                "description": f"PO of INR {float(r[2] or 0):,.2f} needs approval or dispatch.",
                "reference_id": r[0],
                "action_label": "Manage PO",
                "action_target": "purchase-orders"
            })
    except Exception:
        pass

    return actions


def _get_low_stock_with_cur(cur):
    """Returns products where quantity_available <= reorder_level."""
    cur.execute('''
        SELECT 
            p.product_id,
            p.product_name,
            p.sku,
            COALESCE(c.category_name, 'Unassigned') AS category_name,
            i.quantity_available,
            p.reorder_level,
            p.status,
            i.last_updated
        FROM "Products" p
        JOIN "Inventory" i ON p.product_id = i.product_id
        LEFT JOIN "Categories" c ON p.category_id = c.category_id
        WHERE i.quantity_available <= p.reorder_level
        ORDER BY i.quantity_available ASC, p.product_name ASC
    ''')
    rows = cur.fetchall()
    items = []
    for r in rows:
        qty = r[4]
        reorder = r[5]
        stock_status = "OUT OF STOCK" if qty == 0 else "CRITICAL LOW" if qty <= (reorder / 2) else "LOW STOCK"
        items.append({
            "product_id": r[0],
            "product_name": r[1],
            "sku": r[2],
            "category_name": r[3],
            "quantity_available": qty,
            "reorder_level": reorder,
            "product_status": r[6],
            "stock_status": stock_status,
            "last_updated": r[7].isoformat() if r[7] else None
        })
    return items


def _get_recent_pos_with_cur(cur, limit=8):
    """Returns latest purchase orders."""
    cur.execute('''
        SELECT 
            po.purchase_order_id,
            COALESCE(s.supplier_name, 'Supplier #' || po.supplier_id::text) AS supplier_name,
            po.total_amount,
            po.status,
            po.order_date
        FROM "PurchaseOrders" po
        LEFT JOIN "Suppliers" s ON po.supplier_id = s.supplier_id
        ORDER BY po.purchase_order_id DESC
        LIMIT %s
    ''', (limit,))
    rows = cur.fetchall()
    results = []
    for r in rows:
        results.append({
            "po_id": r[0],
            "supplier_name": r[1],
            "total_amount": float(r[2] or 0),
            "status": r[3],
            "created_at": r[4].isoformat() if r[4] else None
        })
    return results


def _get_recent_txs_with_cur(cur, limit=8):
    """Returns latest stock transactions."""
    cur.execute('''
        SELECT 
            st.transaction_id,
            COALESCE(p.product_name, 'Product #' || st.product_id::text) AS product_name,
            st.transaction_type,
            st.quantity,
            COALESCE(u.username, 'System') AS user_name,
            st.transaction_date
        FROM "StockTransactions" st
        LEFT JOIN "Products" p ON st.product_id = p.product_id
        LEFT JOIN "Users" u ON st.user_id = u.user_id
        ORDER BY st.transaction_id DESC
        LIMIT %s
    ''', (limit,))
    rows = cur.fetchall()
    results = []
    for r in rows:
        results.append({
            "transaction_id": r[0],
            "product_name": r[1],
            "transaction_type": r[2],
            "quantity": r[3],
            "performed_by": r[4],
            "transaction_date": r[5].isoformat() if r[5] else None
        })
    return results


def _get_employees_with_cur(cur):
    """Returns employee summary and roster."""
    cur.execute('''
        SELECT 
            COUNT(*) AS total_employees,
            COUNT(*) FILTER (WHERE u.status = 'Active') AS active_employees
        FROM "Users" u
        JOIN "Roles" r ON u.role_id = r.role_id
        WHERE r.role_name = 'Employee'
    ''')
    row = cur.fetchone()
    total = row[0] or 0
    active = row[1] or 0

    cur.execute('''
        SELECT u.user_id, u.username, u.email, u.status
        FROM "Users" u
        JOIN "Roles" r ON u.role_id = r.role_id
        WHERE r.role_name = 'Employee'
        ORDER BY u.user_id ASC
        LIMIT 10
    ''')
    roster = []
    for r in cur.fetchall():
        roster.append({
            "user_id": r[0],
            "username": r[1],
            "email": r[2],
            "status": r[3]
        })

    return {
        "total_employees": total,
        "active_employees": active,
        "employees": roster
    }


def _get_suppliers_with_cur(cur):
    """Returns supplier summary and roster."""
    cur.execute('''
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status ILIKE 'Active') AS active
        FROM "Suppliers"
    ''')
    row = cur.fetchone()
    total = row[0] or 0
    active = row[1] or 0

    cur.execute('''
        SELECT supplier_id, supplier_name, status, COALESCE(phone, email, contact_person) AS contact_info
        FROM "Suppliers"
        ORDER BY supplier_id ASC
        LIMIT 10
    ''')
    suppliers = []
    for r in cur.fetchall():
        suppliers.append({
            "supplier_id": r[0],
            "supplier_name": r[1],
            "status": r[2],
            "contact_info": r[3]
        })

    return {
        "total_suppliers": total,
        "active_suppliers": active,
        "suppliers": suppliers
    }


def _get_notifications_with_cur(cur, limit=10):
    """Returns system notifications and unread count."""
    cur.execute('''
        SELECT COUNT(*)
        FROM "Notifications"
        WHERE is_read = FALSE
    ''')
    unread_count = cur.fetchone()[0] or 0

    cur.execute('''
        SELECT 
            notification_id,
            title,
            message,
            notification_type,
            is_read,
            created_at
        FROM "Notifications"
        ORDER BY notification_id DESC
        LIMIT %s
    ''', (limit,))
    notifications = []
    for r in cur.fetchall():
        notifications.append({
            "notification_id": r[0],
            "title": r[1],
            "message": r[2],
            "notification_type": r[3],
            "is_read": r[4],
            "created_at": r[5].isoformat() if r[5] else None
        })

    return {
        "unread_count": unread_count,
        "notifications": notifications
    }


# =============================================================================
# CONSOLIDATED DASHBOARD DATA SERVICE (SINGLE CONNECTION, MAXIMUM SPEED)
# =============================================================================

def get_full_dashboard_data():
    """
    Retrieves all dashboard components in a single database connection.
    Prevents connection pool starvation and eliminates concurrency timeouts.
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return {
            "summary": _get_summary_with_cur(cur),
            "inventory": _get_inventory_with_cur(cur),
            "procurement": _get_procurement_with_cur(cur),
            "pending_actions": _get_pending_actions_with_cur(cur),
            "low_stock": _get_low_stock_with_cur(cur),
            "purchase_orders": _get_recent_pos_with_cur(cur, limit=8),
            "transactions": _get_recent_txs_with_cur(cur, limit=8),
            "employees": _get_employees_with_cur(cur),
            "suppliers": _get_suppliers_with_cur(cur),
            "notifications": _get_notifications_with_cur(cur, limit=10)
        }
    finally:
        cur.close()
        release_db_connection(conn)


# =============================================================================
# INDIVIDUAL ENDPOINT WRAPPERS (FOR MODULAR ACCESS & BACKWARD COMPATIBILITY)
# =============================================================================

def get_dashboard_summary():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_summary_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_inventory_overview():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_inventory_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_procurement_overview():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_procurement_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_pending_actions():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_pending_actions_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_low_stock_products():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_low_stock_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_recent_purchase_orders(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_recent_pos_with_cur(cur, limit=limit)
    finally:
        cur.close()
        release_db_connection(conn)


def get_recent_stock_transactions(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_recent_txs_with_cur(cur, limit=limit)
    finally:
        cur.close()
        release_db_connection(conn)


def get_employee_overview():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_employees_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_supplier_overview():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_suppliers_with_cur(cur)
    finally:
        cur.close()
        release_db_connection(conn)


def get_manager_notifications(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        return _get_notifications_with_cur(cur, limit=limit)
    finally:
        cur.close()
        release_db_connection(conn)


def mark_notification_read(notification_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            UPDATE "Notifications"
            SET is_read = TRUE
            WHERE notification_id = %s
            RETURNING notification_id, is_read
        ''', (notification_id,))
        row = cur.fetchone()
        conn.commit()
        if not row:
            return False, "Notification not found"
        return True, None
    finally:
        cur.close()
        release_db_connection(conn)
