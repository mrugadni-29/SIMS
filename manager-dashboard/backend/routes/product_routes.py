from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from middleware.auth_middleware import manager_required
import services.product_service as product_service

product_bp = Blueprint("manager_products", __name__, url_prefix="/api/manager/products")


def get_current_user_id():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None


@product_bp.route("/", methods=["GET"])
@manager_required()
def list_products():
    """List products with search, category, status filters and sorting."""
    search = request.args.get("search")
    category_id = request.args.get("category_id", type=int)
    status = request.args.get("status")
    sort_by = request.args.get("sort_by", "name")
    sort_order = request.args.get("sort_order", "asc")

    products, error = product_service.get_products(
        search=search,
        category_id=category_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order
    )

    if error:
        return jsonify({"success": False, "error": error}), 500

    return jsonify({"success": True, "data": products}), 200


@product_bp.route("/<int:product_id>", methods=["GET"])
@manager_required()
def get_product(product_id):
    """Get single product details with inventory and category information."""
    product, error = product_service.get_product_by_id(product_id)
    if error:
        status_code = 404 if error == "Product not found" else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({"success": True, "data": product}), 200


@product_bp.route("/", methods=["POST"])
@manager_required()
def add_product():
    """Add a new product and initialize its inventory."""
    data = request.get_json(silent=True) or {}

    name = data.get("product_name")
    category_id = data.get("category_id")
    sku = data.get("sku")
    selling_price = data.get("selling_price")
    reorder_level = data.get("reorder_level", 10)
    initial_stock = data.get("initial_stock", 0)
    status = data.get("status", "Active")

    creator_id = get_current_user_id()

    new_prod, error = product_service.create_product(
        product_name=name,
        category_id=category_id,
        sku=sku,
        selling_price=selling_price,
        reorder_level=reorder_level,
        initial_stock=initial_stock,
        status=status,
        creator_id=creator_id
    )

    if error:
        status_code = 400 if "required" in error.lower() or "invalid" in error.lower() or "exists" in error.lower() else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Product created successfully",
        "data": new_prod
    }), 201


@product_bp.route("/<int:product_id>", methods=["PUT"])
@manager_required()
def edit_product(product_id):
    """Update product master data."""
    data = request.get_json(silent=True) or {}

    name = data.get("product_name")
    category_id = data.get("category_id")
    sku = data.get("sku")
    selling_price = data.get("selling_price")
    reorder_level = data.get("reorder_level")
    status = data.get("status")

    modifier_id = get_current_user_id()

    updated, error = product_service.update_product(
        product_id=product_id,
        product_name=name,
        category_id=category_id,
        sku=sku,
        selling_price=selling_price,
        reorder_level=reorder_level,
        status=status,
        modifier_id=modifier_id
    )

    if error:
        status_code = 404 if error == "Product not found" else 400 if "already" in error or "valid" in error or "exist" in error else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Product updated successfully",
        "data": updated
    }), 200


@product_bp.route("/<int:product_id>/status", methods=["PATCH", "PUT"])
@manager_required()
def toggle_status(product_id):
    """Toggle product active/inactive status."""
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if not status:
        return jsonify({"success": False, "error": "Status is required (Active or Inactive)"}), 400

    modifier_id = get_current_user_id()

    updated, error = product_service.update_product_status(
        product_id=product_id,
        status=status,
        modifier_id=modifier_id
    )

    if error:
        status_code = 404 if error == "Product not found" else 400
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": f"Product status updated to {status}",
        "data": updated
    }), 200
