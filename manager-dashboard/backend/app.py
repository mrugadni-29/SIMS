from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import JWT_SECRET_KEY, PORT, DEBUG
from routes.manager_dashboard_routes import manager_dashboard_bp
from routes.employee_routes import employee_bp
from routes.category_routes import category_bp
from routes.product_routes import product_bp


def create_dashboard_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY

    # Allow CORS from all standard frontend local origins
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5500",
                    "http://127.0.0.1:5500",
                    "http://localhost:8000",
                    "http://127.0.0.1:8000",
                    "http://localhost:8080",
                    "http://127.0.0.1:8080",
                    "http://localhost:3000",
                    "http://127.0.0.1:3000",
                    "http://localhost:5173",
                    "http://127.0.0.1:5173",
                    "http://localhost:5001",
                    "http://127.0.0.1:5001"
                ],
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"]
            }
        }
    )

    JWTManager(app)

    # Register blueprints
    app.register_blueprint(manager_dashboard_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(product_bp)

    @app.route("/")
    def index():
        return jsonify({
            "name": "Smart Inventory Management System - Manager Dashboard Backend API",
            "team": "Team 2",
            "version": "1.0.0",
            "status": "active",
            "api_documentation": "/api/manager/dashboard/health",
            "endpoints": [
                "/api/manager/dashboard/summary",
                "/api/manager/dashboard/inventory-overview",
                "/api/manager/dashboard/procurement-overview",
                "/api/manager/dashboard/pending-actions",
                "/api/manager/dashboard/low-stock",
                "/api/manager/dashboard/recent-purchase-orders",
                "/api/manager/dashboard/recent-transactions",
                "/api/manager/dashboard/employees",
                "/api/manager/dashboard/suppliers",
                "/api/manager/dashboard/notifications"
            ]
        }), 200

    return app


app = create_dashboard_app()

if __name__ == "__main__":
    print(f"\n=======================================================")
    print(f">> SMART INVENTORY MANAGEMENT SYSTEM - MANAGER DASHBOARD")
    print(f"Developed by Team 2 (Standalone Module)")
    print(f"Backend running on: http://127.0.0.1:{PORT}")
    print(f"Health check: http://127.0.0.1:{PORT}/api/manager/dashboard/health")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG)
