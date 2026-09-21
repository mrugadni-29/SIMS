from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from middleware.auth_middleware import manager_required
import services.employee_service as employee_service

employee_bp = Blueprint("manager_employees", __name__, url_prefix="/api/manager/employees")


def get_current_user_id():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity()
    except Exception:
        return None


@employee_bp.route("/", methods=["GET"])
@manager_required()
def list_employees():
    """List employees with optional search and status filters."""
    search = request.args.get("search")
    status = request.args.get("status")

    employees, error = employee_service.get_employees(search=search, status=status)
    if error:
        return jsonify({"success": False, "error": error}), 500

    return jsonify({"success": True, "data": employees}), 200


@employee_bp.route("/<int:user_id>", methods=["GET"])
@manager_required()
def get_employee(user_id):
    """Get single employee profile with assigned POs and stock transactions."""
    employee, error = employee_service.get_employee_by_id(user_id)
    if error:
        status_code = 404 if error == "Employee not found" else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({"success": True, "data": employee}), 200


@employee_bp.route("/", methods=["POST"])
@manager_required()
def add_employee():
    """Create a new employee account (strictly role=Employee)."""
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    status = data.get("status", "Active")

    creator_id = get_current_user_id()

    new_emp, error = employee_service.create_employee(
        username=username,
        email=email,
        password=password,
        status=status,
        creator_id=creator_id
    )

    if error:
        status_code = 400 if "required" in error.lower() or "invalid" in error.lower() or "exists" in error.lower() else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Employee created successfully",
        "data": new_emp
    }), 201


@employee_bp.route("/<int:user_id>", methods=["PUT"])
@manager_required()
def edit_employee(user_id):
    """Update employee details."""
    data = request.get_json(silent=True) or {}

    username = data.get("username")
    email = data.get("email")
    status = data.get("status")

    modifier_id = get_current_user_id()

    updated, error = employee_service.update_employee(
        user_id=user_id,
        username=username,
        email=email,
        status=status,
        modifier_id=modifier_id
    )

    if error:
        status_code = 404 if error == "Employee not found" else 400 if "already" in error or "valid" in error else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": "Employee updated successfully",
        "data": updated
    }), 200


@employee_bp.route("/<int:user_id>/status", methods=["PATCH", "PUT"])
@manager_required()
def toggle_status(user_id):
    """Toggle employee active/inactive status."""
    data = request.get_json(silent=True) or {}
    status = data.get("status")

    if not status:
        return jsonify({"success": False, "error": "Status is required (Active or Inactive)"}), 400

    modifier_id = get_current_user_id()

    updated, error = employee_service.update_employee_status(
        user_id=user_id,
        status=status,
        modifier_id=modifier_id
    )

    if error:
        status_code = 404 if error == "Employee not found" else 400 if "cannot" in error.lower() else 500
        return jsonify({"success": False, "error": error}), status_code

    return jsonify({
        "success": True,
        "message": f"Employee status set to {status}",
        "data": updated
    }), 200
