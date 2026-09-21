/**
 * SMART INVENTORY MANAGEMENT SYSTEM - MANAGER CONSOLE
 * Universal API Client Module (Team 2)
 * Connects frontend directly to the standalone Flask REST APIs.
 */

const SERVER_ORIGIN = window.location.port === "5001" 
  ? "" 
  : "http://127.0.0.1:5001";

/**
 * Universal authenticated fetch wrapper
 */
async function apiFetch(endpoint, options = {}) {
  const token = localStorage.getItem("sims_access_token") || sessionStorage.getItem("sims_access_token");
  
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers
  };

  try {
    const url = `${SERVER_ORIGIN}${endpoint}`;
    const response = await fetch(url, config);
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || result.error || `HTTP error ${response.status}`);
    }

    return result;
  } catch (err) {
    console.error(`[API Error] ${endpoint}:`, err);
    throw err;
  }
}

// 1. Dashboard Overview APIs
export const DashboardAPI = {
  getOverview: () => apiFetch("/api/manager/dashboard/overview"),
  getHealth: () => apiFetch("/api/manager/dashboard/health"),
  getSummary: () => apiFetch("/api/manager/dashboard/summary"),
  getInventoryOverview: () => apiFetch("/api/manager/dashboard/inventory-overview"),
  getProcurementOverview: () => apiFetch("/api/manager/dashboard/procurement-overview"),
  getPendingActions: () => apiFetch("/api/manager/dashboard/pending-actions"),
  getLowStock: () => apiFetch("/api/manager/dashboard/low-stock"),
  getRecentPurchaseOrders: (limit = 8) => apiFetch(`/api/manager/dashboard/recent-purchase-orders?limit=${limit}`),
  getRecentTransactions: (limit = 8) => apiFetch(`/api/manager/dashboard/recent-transactions?limit=${limit}`),
  getEmployees: () => apiFetch("/api/manager/dashboard/employees"),
  getEmployeesOverview: () => apiFetch("/api/manager/dashboard/employees"),
  getSuppliers: () => apiFetch("/api/manager/dashboard/suppliers"),
  getSuppliersOverview: () => apiFetch("/api/manager/dashboard/suppliers"),
  getNotifications: (limit = 10) => apiFetch(`/api/manager/dashboard/notifications?limit=${limit}`),
  markNotificationRead: (id) => apiFetch(`/api/manager/dashboard/notifications/${id}/read`, { method: "PATCH" })
};

// 2. Employee Management APIs
export const EmployeeAPI = {
  list: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append("search", params.search);
    if (params.status) query.append("status", params.status);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiFetch(`/api/manager/employees/${qs}`);
  },
  getById: (id) => apiFetch(`/api/manager/employees/${id}`),
  create: (data) => apiFetch("/api/manager/employees/", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  update: (id, data) => apiFetch(`/api/manager/employees/${id}`, {
    method: "PUT",
    body: JSON.stringify(data)
  }),
  toggleStatus: (id, status) => apiFetch(`/api/manager/employees/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  })
};

// 3. Category Management APIs
export const CategoryAPI = {
  list: (params = "") => {
    const search = typeof params === "string" ? params : (params?.search || "");
    const qs = search ? `?search=${encodeURIComponent(search)}` : "";
    return apiFetch(`/api/manager/categories/${qs}`);
  },
  getById: (id) => apiFetch(`/api/manager/categories/${id}`),
  create: (data) => apiFetch("/api/manager/categories/", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  update: (id, data) => apiFetch(`/api/manager/categories/${id}`, {
    method: "PUT",
    body: JSON.stringify(data)
  }),
  delete: (id) => apiFetch(`/api/manager/categories/${id}`, {
    method: "DELETE"
  })
};

// 4. Product Management APIs
export const ProductAPI = {
  list: (params = {}) => {
    const query = new URLSearchParams();
    if (params.search) query.append("search", params.search);
    if (params.category_id) query.append("category_id", params.category_id);
    if (params.status) query.append("status", params.status);
    if (params.sort_by) query.append("sort_by", params.sort_by);
    if (params.sort_order) query.append("sort_order", params.sort_order);
    const qs = query.toString() ? `?${query.toString()}` : "";
    return apiFetch(`/api/manager/products/${qs}`);
  },
  getById: (id) => apiFetch(`/api/manager/products/${id}`),
  create: (data) => apiFetch("/api/manager/products/", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  update: (id, data) => apiFetch(`/api/manager/products/${id}`, {
    method: "PUT",
    body: JSON.stringify(data)
  }),
  toggleStatus: (id, status) => apiFetch(`/api/manager/products/${id}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status })
  })
};
