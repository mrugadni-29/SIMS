from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from middleware.auth_middleware import manager_required
import services.category_service as category_service

category_bp = Blueprint("manager_categories", __name__, url_prefix="/api/manager/categories")


def get_current_user_id():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None


@category_bp.route("/", methods=["GET"])
@manager_required()
def list_categories():
    """List all categories with live product count."""
    search = request.args.get("search")
    categories, error = category_service.get_categories(search=search)
    if error:
        return jsonify({"success": False, "error": error}), 500

    return jsonify({"success": True, "data": categories}), 200


@category_bp.route("/<int:category_id>", methods=["GET"])
@manager_required()
def get_category(category_id):
    """Get single category with its assigned products."""
    category, error = category_service.get_category_by_id(category_id)
    if error:
        status_code = 404 if error == "Category not found" else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({"success": True, "data": category}), 200


@category_bp.route("/", methods=["POST"])
@manager_required()
def add_category():
    """Create a new category."""
    data = request.get_json(silent=True) or {}
    name = data.get("category_name")
    desc = data.get("description")

    creator_id = get_current_user_id()

    category, error = category_service.create_category(
        category_name=name,
        description=desc,
        creator_id=creator_id
    )

    if error:
        status_code = 400 if "required" in error.lower() else 409 if "exists" in error.lower() else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Category created successfully",
        "data": category
    }), 201


@category_bp.route("/<int:category_id>", methods=["PUT"])
@manager_required()
def edit_category(category_id):
    """Update an existing category."""
    data = request.get_json(silent=True) or {}
    name = data.get("category_name")
    desc = data.get("description")

    modifier_id = get_current_user_id()

    updated, error = category_service.update_category(
        category_id=category_id,
        category_name=name,
        description=desc,
        modifier_id=modifier_id
    )

    if error:
        status_code = 404 if error == "Category not found" else 409 if "exists" in error.lower() else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Category updated successfully",
        "data": updated
    }), 200


@category_bp.route("/<int:category_id>", methods=["DELETE"])
@manager_required()
def remove_category(category_id):
    """Delete a category if no products are assigned."""
    modifier_id = get_current_user_id()

    success, error = category_service.delete_category(category_id, modifier_id=modifier_id)

    if error:
        status_code = 404 if error == "Category not found" else 409 if "assigned" in error.lower() else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Category deleted successfully"
    }), 200
