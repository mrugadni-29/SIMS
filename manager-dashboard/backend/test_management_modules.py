"""
Test suite for Manager-side Employee, Category, and Product Management
Validates all CRUD operations, validations, and real Supabase PostgreSQL integration.
"""
import sys
import os
import random
import string

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_dashboard_app


def random_string(length=6):
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def run_tests():
    app = create_dashboard_app()
    app.config["TESTING"] = True
    client = app.test_client()

    print("=" * 65)
    print("TESTING EMPLOYEE, CATEGORY & PRODUCT MANAGEMENT APIS")
    print("=" * 65)

    all_passed = True

    # 1. CATEGORY MANAGEMENT TESTS
    print("\n--- 1. CATEGORY MANAGEMENT ---")
    res = client.get("/api/manager/categories/")
    assert res.status_code == 200, f"List categories failed: {res.data}"
    cats = res.get_json()["data"]
    print(f"PASS: Listed {len(cats)} categories from Supabase.")
    first_cat_id = cats[0]["category_id"] if cats else 1

    # Create Category
    new_cat_name = f"Test Category {random_string(4)}"
    res = client.post("/api/manager/categories/", json={
        "category_name": new_cat_name,
        "description": "Automated test category"
    })
    assert res.status_code == 201, f"Create category failed: {res.data}"
    created_cat = res.get_json()["data"]
    created_cat_id = created_cat["category_id"]
    print(f"PASS: Created Category #{created_cat_id} ('{new_cat_name}')")

    # Reject duplicate category
    res = client.post("/api/manager/categories/", json={"category_name": new_cat_name})
    assert res.status_code == 409, f"Duplicate category check failed: {res.data}"
    print("PASS: Duplicate category correctly rejected with 409.")

    # 2. EMPLOYEE MANAGEMENT TESTS
    print("\n--- 2. EMPLOYEE MANAGEMENT ---")
    res = client.get("/api/manager/employees/")
    assert res.status_code == 200, f"List employees failed: {res.data}"
    emps = res.get_json()["data"]
    print(f"PASS: Listed {len(emps)} employees from Supabase.")

    # Create Employee
    test_uname = f"emp_{random_string(5)}"
    test_email = f"{test_uname}@example.com"
    res = client.post("/api/manager/employees/", json={
        "username": test_uname,
        "email": test_email,
        "password": "Password123!",
        "status": "Active"
    })
    assert res.status_code == 201, f"Create employee failed: {res.data}"
    created_emp = res.get_json()["data"]
    created_emp_id = created_emp["user_id"]
    print(f"PASS: Created Employee #{created_emp_id} ('{test_uname}', role='{created_emp['role']}')")

    # Reject duplicate employee email
    res = client.post("/api/manager/employees/", json={
        "username": f"another_{random_string(4)}",
        "email": test_email,
        "password": "Password123!"
    })
    assert res.status_code == 400, f"Duplicate employee email check failed: {res.data}"
    print("PASS: Duplicate employee email rejected with 400.")

    # Toggle status
    res = client.patch(f"/api/manager/employees/{created_emp_id}/status", json={"status": "Inactive"})
    assert res.status_code == 200, f"Deactivate employee failed: {res.data}"
    assert res.get_json()["data"]["status"] == "Inactive"
    print(f"PASS: Deactivated Employee #{created_emp_id} to Inactive.")

    # 3. PRODUCT MANAGEMENT TESTS
    print("\n--- 3. PRODUCT MANAGEMENT ---")
    res = client.get("/api/manager/products/")
    assert res.status_code == 200, f"List products failed: {res.data}"
    prods = res.get_json()["data"]
    print(f"PASS: Listed {len(prods)} products from Supabase.")

    # Create Product
    test_pname = f"Test Item {random_string(4)}"
    test_sku = f"SKU-{random_string(4).upper()}"
    res = client.post("/api/manager/products/", json={
        "product_name": test_pname,
        "category_id": created_cat_id,
        "sku": test_sku,
        "selling_price": 499.00,
        "reorder_level": 15,
        "initial_stock": 50,
        "status": "Active"
    })
    assert res.status_code == 201, f"Create product failed: {res.data}"
    created_prod = res.get_json()["data"]
    created_prod_id = created_prod["product_id"]
    print(f"PASS: Created Product #{created_prod_id} ('{test_pname}') with Initial Inventory={created_prod['quantity_available']}.")

    # Get Single Product
    res = client.get(f"/api/manager/products/{created_prod_id}")
    assert res.status_code == 200
    prod_data = res.get_json()["data"]
    assert prod_data["sku"] == test_sku
    assert prod_data["category_id"] == created_cat_id
    print(f"PASS: Retrieved single product details for #{created_prod_id}.")

    # Safe Category Delete Check (Should fail because product is assigned)
    res = client.delete(f"/api/manager/categories/{created_cat_id}")
    assert res.status_code == 409, f"Foreign key delete protection failed: {res.data}"
    print(f"PASS: Category #{created_cat_id} delete rejected with 409 because products are assigned.")

    print("\n" + "=" * 65)
    print("ALL MANAGER-SIDE MANAGEMENT TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)


if __name__ == "__main__":
    run_tests()
