/**
 * SMART INVENTORY MANAGEMENT SYSTEM - EMPLOYEE MANAGEMENT
 * Controller for employees.html (Team 2)
 */

import { EmployeeAPI } from './api.js';

let currentEmployees = [];

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function formatDate(dateString) {
  if (!dateString) return "N/A";
  const d = new Date(dateString);
  if (isNaN(d.getTime())) return dateString;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

window.closeModal = (modalId) => {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
};

window.openModal = (modalId) => {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("open");
};

async function loadEmployees() {
  const search = document.getElementById("employeeSearchInput")?.value || "";
  const status = document.getElementById("employeeStatusFilter")?.value || "";
  const tbody = document.getElementById("employeesTableBody");
  const countBadge = document.getElementById("employeeCountBadge");

  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8">
          <div class="state-container">
            <p>Fetching employees from Supabase...</p>
          </div>
        </td>
      </tr>
    `;
  }

  try {
    const res = await EmployeeAPI.list({ search, status });
    currentEmployees = res.data || [];

    if (countBadge) {
      countBadge.textContent = `${currentEmployees.length} Employee${currentEmployees.length === 1 ? '' : 's'}`;
    }

    if (!currentEmployees || currentEmployees.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8">
            <div class="state-container">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
              </svg>
              <h4>No Employees Found</h4>
              <p>No employee records matched your filter criteria.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    let html = "";
    currentEmployees.forEach(emp => {
      const isActive = emp.status === "Active";
      const statusBadge = isActive ? "badge-success" : "badge-danger";
      const toggleLabel = isActive ? "Deactivate" : "Activate";
      const nextStatus = isActive ? "Inactive" : "Active";

      html += `
        <tr>
          <td><strong>#${emp.user_id}</strong></td>
          <td>${emp.username}</td>
          <td>${emp.email}</td>
          <td><span class="badge badge-purple">${emp.role}</span></td>
          <td><span class="badge ${statusBadge}">${emp.status}</span></td>
          <td><strong>${emp.assigned_pos_count}</strong> POs</td>
          <td><strong>${emp.transactions_count}</strong> Tx</td>
          <td style="text-align: right;">
            <button class="btn-action-sm" onclick="viewEmployee(${emp.user_id})" title="View Details">View</button>
            <button class="btn-action-sm" onclick="editEmployee(${emp.user_id})" title="Edit Info">Edit</button>
            <button class="btn-action-sm" onclick="toggleEmployeeStatus(${emp.user_id}, '${nextStatus}')" style="color: ${isActive ? 'var(--danger)' : 'var(--success)'};">
              ${toggleLabel}
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;

  } catch (err) {
    console.error("Failed to load employees:", err);
    showToast("Unable to load employees from database.", "danger");
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="8">
            <div class="state-container">
              <h4>Error Loading Employees</h4>
              <p>${err.message}</p>
              <button class="btn-primary" onclick="window.reloadEmployees()">Retry</button>
            </div>
          </td>
        </tr>
      `;
    }
  }
}

window.reloadEmployees = loadEmployees;

window.viewEmployee = async (id) => {
  openModal("viewEmployeeModal");
  const body = document.getElementById("viewEmpBody");
  const title = document.getElementById("viewEmpTitle");
  body.innerHTML = "<p>Loading employee profile...</p>";

  try {
    const res = await EmployeeAPI.getById(id);
    const emp = res.data;
    title.textContent = `Employee #${emp.user_id}: ${emp.username}`;

    let poHtml = "";
    if (emp.assigned_purchase_orders && emp.assigned_purchase_orders.length > 0) {
      poHtml = `
        <table class="data-table" style="margin-top: 8px;">
          <thead>
            <tr><th>PO ID</th><th>Amount</th><th>Status</th><th>Date</th></tr>
          </thead>
          <tbody>
            ${emp.assigned_purchase_orders.map(po => `
              <tr>
                <td>#${po.purchase_order_id}</td>
                <td>₹${po.total_amount.toLocaleString()}</td>
                <td><span class="badge badge-info">${po.status}</span></td>
                <td>${formatDate(po.order_date)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    } else {
      poHtml = "<p style='font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;'>No purchase orders assigned to this employee.</p>";
    }

    let txHtml = "";
    if (emp.recent_transactions && emp.recent_transactions.length > 0) {
      txHtml = `
        <table class="data-table" style="margin-top: 8px;">
          <thead>
            <tr><th>Tx ID</th><th>Product</th><th>Type</th><th>Qty</th><th>Date</th></tr>
          </thead>
          <tbody>
            ${emp.recent_transactions.map(tx => `
              <tr>
                <td>#${tx.transaction_id}</td>
                <td>${tx.product_name}</td>
                <td><span class="badge badge-success">${tx.transaction_type}</span></td>
                <td>${tx.quantity}</td>
                <td>${formatDate(tx.transaction_date)}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;
    } else {
      txHtml = "<p style='font-size: 0.82rem; color: var(--text-muted); margin-top: 4px;'>No stock transactions recorded for this employee.</p>";
    }

    body.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px;">
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Username</span>
          <h4 style="margin-top: 2px;">${emp.username}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Email</span>
          <h4 style="margin-top: 2px;">${emp.email}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Role</span>
          <h4 style="margin-top: 2px;">${emp.role}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Account Status</span>
          <h4 style="margin-top: 2px; color: ${emp.status === 'Active' ? 'var(--success)' : 'var(--danger)'};">${emp.status}</h4>
        </div>
      </div>

      <div style="margin-top: 14px;">
        <h4 style="font-size: 0.88rem; font-weight: 700;">Assigned Purchase Orders</h4>
        ${poHtml}
      </div>

      <div style="margin-top: 16px;">
        <h4 style="font-size: 0.88rem; font-weight: 700;">Recent Stock Processing Activity</h4>
        ${txHtml}
      </div>
    `;

  } catch (err) {
    body.innerHTML = `<p style="color: var(--danger);">Failed to load details: ${err.message}</p>`;
  }
};

window.editEmployee = (id) => {
  const emp = currentEmployees.find(e => e.user_id === id);
  if (!emp) return;

  document.getElementById("editEmpId").value = emp.user_id;
  document.getElementById("editEmpUsername").value = emp.username;
  document.getElementById("editEmpEmail").value = emp.email;
  document.getElementById("editEmpStatus").value = emp.status;

  openModal("editEmployeeModal");
};

window.toggleEmployeeStatus = async (id, newStatus) => {
  if (!confirm(`Are you sure you want to set employee #${id} to ${newStatus}?`)) return;

  try {
    await EmployeeAPI.toggleStatus(id, newStatus);
    showToast(`Employee #${id} is now ${newStatus}`, "success");
    loadEmployees();
  } catch (err) {
    showToast(`Failed: ${err.message}`, "danger");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  loadEmployees();

  // Search input debounce
  let searchTimeout;
  document.getElementById("employeeSearchInput")?.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(loadEmployees, 300);
  });

  // Status filter dropdown
  document.getElementById("employeeStatusFilter")?.addEventListener("change", loadEmployees);

  // Refresh button
  document.getElementById("refreshEmployeesBtn")?.addEventListener("click", () => {
    loadEmployees();
    showToast("Refreshed employees from Supabase", "info");
  });

  // Open Add Modal
  document.getElementById("openAddEmployeeModalBtn")?.addEventListener("click", () => {
    document.getElementById("addEmployeeForm")?.reset();
    openModal("addEmployeeModal");
  });

  // Add Employee Form Submit
  document.getElementById("addEmployeeForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = document.getElementById("addEmpUsername").value.trim();
    const email = document.getElementById("addEmpEmail").value.trim();
    const password = document.getElementById("addEmpPassword").value;
    const status = document.getElementById("addEmpStatus").value;

    try {
      await EmployeeAPI.create({ username, email, password, status });
      showToast("Employee created successfully!", "success");
      closeModal("addEmployeeModal");
      loadEmployees();
    } catch (err) {
      showToast(`Error: ${err.message}`, "danger");
    }
  });

  // Edit Employee Form Submit
  document.getElementById("editEmployeeForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("editEmpId").value;
    const username = document.getElementById("editEmpUsername").value.trim();
    const email = document.getElementById("editEmpEmail").value.trim();
    const status = document.getElementById("editEmpStatus").value;

    try {
      await EmployeeAPI.update(id, { username, email, status });
      showToast("Employee updated successfully!", "success");
      closeModal("editEmployeeModal");
      loadEmployees();
    } catch (err) {
      showToast(`Error: ${err.message}`, "danger");
    }
  });
});
