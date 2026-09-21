/**
 * SMART INVENTORY MANAGEMENT SYSTEM - MANAGER DASHBOARD
 * Main Dashboard Controller (Team 2)
 * Manages UI rendering, state transitions, empty states, and auto-refresh.
 */

import { DashboardAPI } from './api.js';

// Application State
const state = {
  summary: null,
  inventory: null,
  procurement: null,
  pendingActions: [],
  lowStock: [],
  purchaseOrders: [],
  transactions: [],
  employees: null,
  suppliers: null,
  notifications: [],
  unreadNotifications: 0,
  isRefreshing: false,
  autoRefreshInterval: null
};

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Format currency
function formatCurrency(amount) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0
  }).format(amount || 0);
}

// Format relative date
function formatDate(dateString) {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return dateString;
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

/**
 * 1. Render Summary Metric Cards
 */
function renderSummary(data) {
  if (!data) return;

  const mapping = [
    { id: "metric-total-products", val: data.total_products },
    { id: "metric-low-stock", val: data.low_stock_products },
    { id: "metric-out-stock", val: data.out_of_stock_products },
    { id: "metric-pending-requests", val: data.pending_stock_requests },
    { id: "metric-pending-quotations", val: data.pending_quotations },
    { id: "metric-pending-pos", val: data.pending_purchase_orders },
    { id: "metric-in-transit", val: data.orders_in_transit },
    { id: "metric-total-employees", val: data.total_employees }
  ];

  mapping.forEach(m => {
    const el = document.getElementById(m.id);
    if (el) {
      el.textContent = Number(m.val || 0).toLocaleString();
    }
  });
}

/**
 * 2. Render Inventory Status Overview (SVG Donut + Category bars)
 */
function renderInventory(data) {
  if (!data || !data.status_breakdown) return;

  const { in_stock, low_stock, out_of_stock, total_units } = data.status_breakdown;
  const total = (in_stock + low_stock + out_of_stock) || 0;

  // Update center total
  const centerEl = document.getElementById("donutTotalNum");
  if (centerEl) centerEl.textContent = total;

  // Calculate SVG stroke dashes for a radius of 45 (circumference ~ 283)
  const circumference = 2 * Math.PI * 45;
  const inStockPct = total > 0 ? in_stock / total : 0;
  const lowStockPct = total > 0 ? low_stock / total : 0;
  const outStockPct = total > 0 ? out_of_stock / total : 0;

  const s1 = document.getElementById("donutSegmentInStock");
  const s2 = document.getElementById("donutSegmentLowStock");
  const s3 = document.getElementById("donutSegmentOutStock");

  if (s1 && s2 && s3) {
    const d1 = inStockPct * circumference;
    const d2 = lowStockPct * circumference;
    const d3 = outStockPct * circumference;

    s1.style.strokeDasharray = `${d1} ${circumference}`;
    s1.style.strokeDashoffset = "0";

    s2.style.strokeDasharray = `${d2} ${circumference}`;
    s2.style.strokeDashoffset = `-${d1}`;

    s3.style.strokeDasharray = `${d3} ${circumference}`;
    s3.style.strokeDashoffset = `-${d1 + d2}`;
  }

  // Update legend values
  document.getElementById("legendInStockVal").textContent = in_stock;
  document.getElementById("legendLowStockVal").textContent = low_stock;
  document.getElementById("legendOutStockVal").textContent = out_of_stock;

  // Render category breakdown
  const catContainer = document.getElementById("categoryBarsContainer");
  if (!catContainer) return;

  if (!data.category_breakdown || data.category_breakdown.length === 0) {
    catContainer.innerHTML = `
      <div class="state-container" style="padding: 16px;">
        <p>No category breakdown available</p>
      </div>
    `;
    return;
  }

  let html = "";
  const maxProducts = Math.max(...data.category_breakdown.map(c => c.product_count), 1);

  data.category_breakdown.slice(0, 5).forEach(cat => {
    const pct = Math.round((cat.product_count / maxProducts) * 100);
    html += `
      <div class="category-bar-item">
        <div class="bar-meta">
          <span>${cat.category_name}</span>
          <span><strong>${cat.product_count}</strong> products (${cat.total_stock} units)</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" style="width: ${pct}%; background: linear-gradient(90deg, #6366f1, #818cf8);"></div>
        </div>
      </div>
    `;
  });

  catContainer.innerHTML = html;
}

/**
 * 3. Render Procurement Funnel
 */
function renderProcurement(data) {
  if (!data) return;

  const sr = data.stock_requests || {};
  const q = data.quotations || {};
  const po = data.purchase_orders || {};

  document.getElementById("funnelStockRequests").textContent = sr.pending ?? 0;
  document.getElementById("funnelQuotations").textContent = q.pending ?? 0;
  document.getElementById("funnelPOPending").textContent = po.pending ?? 0;
  document.getElementById("funnelPOAccepted").textContent = po.accepted ?? 0;
  document.getElementById("funnelPOShipped").textContent = po.shipped ?? 0;
  document.getElementById("funnelPODelivered").textContent = (po.delivered || po.completed) ?? 0;
}

/**
 * 4. Render Pending Actions Priority Center
 */
function renderPendingActions(actions) {
  const container = document.getElementById("pendingActionsContainer");
  if (!container) return;

  if (!actions || actions.length === 0) {
    container.innerHTML = `
      <div class="state-container" style="padding: 24px;">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
          <polyline points="22 4 12 14.01 9 11.01"></polyline>
        </svg>
        <h4>All Clear!</h4>
        <p>No urgent actions requiring Manager intervention at this time.</p>
      </div>
    `;
    return;
  }

  let html = "";
  actions.forEach(act => {
    html += `
      <div class="pending-action-card severity-${act.severity}">
        <div class="action-info">
          <h4>${act.title}</h4>
          <p>${act.description}</p>
        </div>
        <button class="btn-action-sm" onclick="handleActionClick('${act.action_target}', ${act.reference_id})">
          ${act.action_label}
        </button>
      </div>
    `;
  });

  container.innerHTML = html;
}

/**
 * 5. Render Low Stock Table
 */
function renderLowStock(products) {
  const tbody = document.getElementById("lowStockTableBody");
  if (!tbody) return;

  if (!products || products.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7">
          <div class="state-container">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
            <h4>No Low-Stock Products</h4>
            <p>All inventory levels are currently above reorder thresholds.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  let html = "";
  products.forEach(p => {
    const isOut = p.quantity_available === 0;
    const badgeClass = isOut ? "badge-danger" : "badge-warning";
    const fillWidth = Math.min(100, Math.round((p.quantity_available / Math.max(p.reorder_level, 1)) * 100));

    html += `
      <tr>
        <td><strong>${p.product_name}</strong></td>
        <td><code>${p.sku || 'N/A'}</code></td>
        <td>${p.category_name}</td>
        <td>
          <span style="font-weight: 700; color: ${isOut ? 'var(--danger)' : 'var(--warning)'};">
            ${p.quantity_available}
          </span>
        </td>
        <td>${p.reorder_level}</td>
        <td>
          <div class="progress-track" style="width: 80px;">
            <div class="progress-fill" style="width: ${fillWidth}%; background-color: ${isOut ? 'var(--danger)' : 'var(--warning)'};"></div>
          </div>
        </td>
        <td>
          <span class="badge ${badgeClass}">${p.stock_status}</span>
        </td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

/**
 * 6. Render Recent Purchase Orders Table
 */
function renderPurchaseOrders(orders) {
  const tbody = document.getElementById("recentPOTableBody");
  if (!tbody) return;

  if (!orders || orders.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="state-container">
            <h4>No Purchase Orders Found</h4>
            <p>No purchase order records exist in the database.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  let html = "";
  orders.forEach(po => {
    let badgeClass = "badge-info";
    const st = (po.status || "").toLowerCase();
    if (st.includes("pending")) badgeClass = "badge-warning";
    else if (st.includes("delivered") || st.includes("completed")) badgeClass = "badge-success";
    else if (st.includes("shipped")) badgeClass = "badge-purple";

    html += `
      <tr>
        <td><strong>#${po.po_id}</strong></td>
        <td>${po.supplier_name}</td>
        <td><strong>${formatCurrency(po.total_amount)}</strong></td>
        <td><span class="badge ${badgeClass}">${po.status}</span></td>
        <td>${formatDate(po.created_at)}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

/**
 * 7. Render Recent Stock Transactions Table
 */
function renderTransactions(transactions) {
  const tbody = document.getElementById("recentTxTableBody");
  if (!tbody) return;

  if (!transactions || transactions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="state-container">
            <h4>No Transactions Recorded</h4>
            <p>No stock movement records found in the database.</p>
          </div>
        </td>
      </tr>
    `;
    return;
  }

  let html = "";
  transactions.forEach(tx => {
    const isStockIn = (tx.transaction_type || "").toUpperCase().includes("IN");
    const badgeClass = isStockIn ? "badge-success" : "badge-info";

    html += `
      <tr>
        <td><strong>#${tx.transaction_id}</strong></td>
        <td>${tx.product_name}</td>
        <td><span class="badge ${badgeClass}">${tx.transaction_type}</span></td>
        <td><strong>${isStockIn ? '+' : '-'}${tx.quantity}</strong></td>
        <td>${formatDate(tx.transaction_date)}</td>
      </tr>
    `;
  });

  tbody.innerHTML = html;
}

/**
 * 8. Render Employee & Supplier Overviews
 */
function renderDirectory(employees, suppliers) {
  if (employees) {
    const activeEl = document.getElementById("employeeActiveCount");
    const totalEl = document.getElementById("employeeTotalCount");
    if (activeEl) activeEl.textContent = employees.active_employees ?? 0;
    if (totalEl) totalEl.textContent = employees.total_employees ?? 0;
  }

  if (suppliers) {
    const activeEl = document.getElementById("supplierActiveCount");
    const totalEl = document.getElementById("supplierTotalCount");
    if (activeEl) activeEl.textContent = suppliers.active_suppliers ?? 0;
    if (totalEl) totalEl.textContent = suppliers.total_suppliers ?? 0;
  }
}

/**
 * 9. Render Notifications
 */
function renderNotifications(data) {
  if (!data) return;

  const countBadge = document.getElementById("notifBadgeCounter");
  if (countBadge) {
    countBadge.textContent = data.unread_count || 0;
    countBadge.style.display = (data.unread_count > 0) ? "inline-block" : "none";
  }

  const listContainer = document.getElementById("notificationList");
  if (!listContainer) return;

  if (!data.notifications || data.notifications.length === 0) {
    listContainer.innerHTML = `
      <div class="state-container" style="padding: 24px;">
        <p>No notifications at this time.</p>
      </div>
    `;
    return;
  }

  let html = "";
  data.notifications.forEach(n => {
    html += `
      <div class="pending-action-card ${n.is_read ? '' : 'severity-high'}" style="flex-direction: column; align-items: flex-start;">
        <div style="display: flex; justify-content: space-between; width: 100%;">
          <strong>${n.title}</strong>
          <span style="font-size: 0.72rem; color: var(--text-muted);">${formatDate(n.created_at)}</span>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 4px;">${n.message}</p>
        ${!n.is_read ? `
          <button class="btn-action-sm" style="margin-top: 8px;" onclick="handleMarkRead(${n.notification_id})">
            Mark Read
          </button>
        ` : ''}
      </div>
    `;
  });

  listContainer.innerHTML = html;
}

/**
 * Universal Dashboard Fetch Coordinator
 */
async function loadAllDashboardData() {
  if (state.isRefreshing) return;
  state.isRefreshing = true;

  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) refreshBtn.classList.add("spinning");

  try {
    // 1. Try ultra-fast consolidated overview API (single DB connection)
    const overviewRes = await DashboardAPI.getOverview();
    if (overviewRes && overviewRes.success && overviewRes.data) {
      const data = overviewRes.data;

      if (data.summary) {
        state.summary = data.summary;
        try { renderSummary(data.summary); } catch (e) { console.error("renderSummary error:", e); }
      }
      if (data.inventory) {
        state.inventory = data.inventory;
        try { renderInventory(data.inventory); } catch (e) { console.error("renderInventory error:", e); }
      }
      if (data.procurement) {
        state.procurement = data.procurement;
        try { renderProcurement(data.procurement); } catch (e) { console.error("renderProcurement error:", e); }
      }
      if (data.pending_actions) {
        state.pendingActions = data.pending_actions;
        try { renderPendingActions(data.pending_actions); } catch (e) { console.error("renderPendingActions error:", e); }
      }
      if (data.low_stock) {
        state.lowStock = data.low_stock;
        try { renderLowStock(data.low_stock); } catch (e) { console.error("renderLowStock error:", e); }
      }
      if (data.purchase_orders) {
        state.purchaseOrders = data.purchase_orders;
        try { renderPurchaseOrders(data.purchase_orders); } catch (e) { console.error("renderPurchaseOrders error:", e); }
      }
      if (data.transactions) {
        state.transactions = data.transactions;
        try { renderTransactions(data.transactions); } catch (e) { console.error("renderTransactions error:", e); }
      }
      if (data.employees || data.suppliers) {
        state.employees = data.employees;
        state.suppliers = data.suppliers;
        try { renderDirectory(data.employees, data.suppliers); } catch (e) { console.error("renderDirectory error:", e); }
      }
      if (data.notifications) {
        state.notifications = data.notifications;
        try { renderNotifications(data.notifications); } catch (e) { console.error("renderNotifications error:", e); }
      }

      // Update timestamp
      const syncEl = document.getElementById("lastSyncTime");
      if (syncEl) {
        syncEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
      }
      return;
    }
  } catch (overviewErr) {
    console.warn("Consolidated overview fetch failed, falling back to modular endpoints:", overviewErr);
  }

  try {
    // Fallback: Individual endpoints
    const [
      summaryRes,
      inventoryRes,
      procurementRes,
      actionsRes,
      lowStockRes,
      posRes,
      txRes,
      empRes,
      supRes,
      notifRes
    ] = await Promise.allSettled([
      DashboardAPI.getSummary(),
      DashboardAPI.getInventoryOverview(),
      DashboardAPI.getProcurementOverview(),
      DashboardAPI.getPendingActions(),
      DashboardAPI.getLowStock(),
      DashboardAPI.getRecentPurchaseOrders(),
      DashboardAPI.getRecentTransactions(),
      DashboardAPI.getEmployees(),
      DashboardAPI.getSuppliers(),
      DashboardAPI.getNotifications()
    ]);

    if (summaryRes.status === "fulfilled" && summaryRes.value?.success) {
      state.summary = summaryRes.value.data;
      try { renderSummary(state.summary); } catch (e) {}
    }
    if (inventoryRes.status === "fulfilled" && inventoryRes.value?.success) {
      state.inventory = inventoryRes.value.data;
      try { renderInventory(state.inventory); } catch (e) {}
    }
    if (procurementRes.status === "fulfilled" && procurementRes.value?.success) {
      state.procurement = procurementRes.value.data;
      try { renderProcurement(state.procurement); } catch (e) {}
    }
    if (actionsRes.status === "fulfilled" && actionsRes.value?.success) {
      state.pendingActions = actionsRes.value.data;
      try { renderPendingActions(state.pendingActions); } catch (e) {}
    }
    if (lowStockRes.status === "fulfilled" && lowStockRes.value?.success) {
      state.lowStock = lowStockRes.value.data;
      try { renderLowStock(state.lowStock); } catch (e) {}
    }
    if (posRes.status === "fulfilled" && posRes.value?.success) {
      state.purchaseOrders = posRes.value.data;
      try { renderPurchaseOrders(state.purchaseOrders); } catch (e) {}
    }
    if (txRes.status === "fulfilled" && txRes.value?.success) {
      state.transactions = txRes.value.data;
      try { renderTransactions(state.transactions); } catch (e) {}
    }
    if (empRes.status === "fulfilled" && empRes.value?.success) {
      state.employees = empRes.value.data;
    }
    if (supRes.status === "fulfilled" && supRes.value?.success) {
      state.suppliers = supRes.value.data;
    }
    try { renderDirectory(state.employees, state.suppliers); } catch (e) {}

    if (notifRes.status === "fulfilled" && notifRes.value?.success) {
      try { renderNotifications(notifRes.value.data); } catch (e) {}
    }

    const syncEl = document.getElementById("lastSyncTime");
    if (syncEl) {
      syncEl.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    }

  } catch (error) {
    console.error("Dashboard refresh error:", error);
    showToast("Failed to refresh some dashboard components.", "danger");
  } finally {
    state.isRefreshing = false;
    if (refreshBtn) refreshBtn.classList.remove("spinning");
  }
}

// Global window event bindings
window.handleActionClick = (target, refId) => {
  showToast(`Navigating to ${target} (ID: ${refId}). Integration ready.`);
};

window.handleMarkRead = async (id) => {
  try {
    await DashboardAPI.markNotificationRead(id);
    showToast("Notification marked as read", "success");
    const notifData = await DashboardAPI.getNotifications();
    renderNotifications(notifData.data);
  } catch (e) {
    showToast("Failed to update notification", "danger");
  }
};

window.toggleNotificationModal = () => {
  const modal = document.getElementById("notificationModal");
  if (modal) {
    modal.classList.toggle("open");
  }
};

window.handleQuickAction = (actionName) => {
  showToast(`Action triggered: ${actionName}. Ready for module link.`, "info");
};

// Initialize Dashboard on DOM Load
document.addEventListener("DOMContentLoaded", () => {
  // Initial load
  loadAllDashboardData();

  // Bind Manual Refresh
  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loadAllDashboardData();
      showToast("Syncing with live database...", "info");
    });
  }

  // Setup auto-refresh every 30 seconds
  state.autoRefreshInterval = setInterval(() => {
    loadAllDashboardData();
  }, 30000);
});
