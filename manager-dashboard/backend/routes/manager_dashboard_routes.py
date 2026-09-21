from flask import Blueprint, jsonify, request
from middleware.auth_middleware import manager_required
import services.manager_dashboard_service as service
from extensions import test_db_connection


manager_dashboard_bp = Blueprint(
    "manager_dashboard",
    __name__,
    url_prefix="/api/manager/dashboard"
)


@manager_dashboard_bp.route("/health", methods=["GET"])
def health_check():
    """Health check verifying API and DB connectivity."""
    db_connected, db_message = test_db_connection()
    return jsonify({
        "success": True,
        "service": "Manager Dashboard API",
        "status": "online",
        "database": {
            "connected": db_connected,
            "message": db_message
        }
    }), 200 if db_connected else 503


@manager_dashboard_bp.route("/overview", methods=["GET"])
@manager_required()
def get_dashboard_overview():
    """Endpoint: Complete consolidated dashboard state in a single DB query batch."""
    try:
        data = service.get_full_dashboard_data()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve dashboard overview: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/summary", methods=["GET"])
@manager_required()
def get_summary():
    """Endpoint: Summary counts and metrics."""
    try:
        data = service.get_dashboard_summary()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve summary metrics: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/inventory-overview", methods=["GET"])
@manager_required()
def get_inventory_overview():
    """Endpoint: Inventory breakdown (In Stock, Low Stock, Out of Stock, Category)."""
    try:
        data = service.get_inventory_overview()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve inventory overview: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/procurement-overview", methods=["GET"])
@manager_required()
def get_procurement_overview():
    """Endpoint: Procurement pipeline counts (Requests -> Quotations -> POs -> Delivered)."""
    try:
        data = service.get_procurement_overview()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve procurement overview: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/pending-actions", methods=["GET"])
@manager_required()
def get_pending_actions():
    """Endpoint: Urgent items requiring Manager attention."""
    try:
        data = service.get_pending_actions()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve pending actions: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/low-stock", methods=["GET"])
@manager_required()
def get_low_stock():
    """Endpoint: Products at or below reorder level."""
    try:
        data = service.get_low_stock_products()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve low-stock products: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/recent-purchase-orders", methods=["GET"])
@manager_required()
def get_recent_purchase_orders():
    """Endpoint: Recent Purchase Orders list."""
    try:
        limit = request.args.get("limit", default=10, type=int)
        data = service.get_recent_purchase_orders(limit=limit)
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve recent purchase orders: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/recent-transactions", methods=["GET"])
@manager_required()
def get_recent_transactions():
    """Endpoint: Recent Stock Movements / Transactions."""
    try:
        limit = request.args.get("limit", default=10, type=int)
        data = service.get_recent_stock_transactions(limit=limit)
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve recent transactions: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/employees", methods=["GET"])
@manager_required()
def get_employees():
    """Endpoint: Employees overview and active roster."""
    try:
        data = service.get_employee_overview()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve employee overview: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/suppliers", methods=["GET"])
@manager_required()
def get_suppliers():
    """Endpoint: Suppliers overview and directory."""
    try:
        data = service.get_supplier_overview()
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve supplier overview: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/notifications", methods=["GET"])
@manager_required()
def get_notifications():
    """Endpoint: Manager alerts and notifications."""
    try:
        limit = request.args.get("limit", default=10, type=int)
        data = service.get_manager_notifications(limit=limit)
        return jsonify({
            "success": True,
            "data": data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": f"Failed to retrieve notifications: {str(e)}"
        }), 500


@manager_dashboard_bp.route("/notifications/<int:notification_id>/read", methods=["PATCH"])
@manager_required()
def mark_notification_as_read(notification_id):
    """Endpoint: Mark a specific notification as read."""
    try:
        success, error = service.mark_notification_read(notification_id)
        if error:
            return jsonify({
                "success": False,
                "error": error
            }), 404
        return jsonify({
            "success": True,
            "message": f"Notification #{notification_id} marked as read"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Database error",
            "message": str(e)
        }), 500
