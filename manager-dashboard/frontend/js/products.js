/**
 * SMART INVENTORY MANAGEMENT SYSTEM - PRODUCT MANAGEMENT
 * Controller for products.html (Team 2)
 */

import { ProductAPI, CategoryAPI } from './api.js';

let currentProducts = [];
let availableCategories = [];

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
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

window.closeModal = (modalId) => {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
};

window.openModal = (modalId) => {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("open");
};

/**
 * Load categories to populate dropdown filters and modal select inputs
 */
async function loadCategoriesList() {
  try {
    const res = await CategoryAPI.list();
    availableCategories = res.data || [];

    const filterSelect = document.getElementById("productCategoryFilter");
    const addSelect = document.getElementById("addProdCategory");
    const editSelect = document.getElementById("editProdCategory");

    // Populate filter dropdown
    if (filterSelect) {
      let filterOpts = '<option value="">All Categories</option>';
      availableCategories.forEach(cat => {
        filterOpts += `<option value="${cat.category_id}">${cat.category_name}</option>`;
      });
      filterSelect.innerHTML = filterOpts;
    }

    // Populate Add modal dropdown
    if (addSelect) {
      let addOpts = '<option value="">Select Category...</option>';
      availableCategories.forEach(cat => {
        addOpts += `<option value="${cat.category_id}">${cat.category_name}</option>`;
      });
      addSelect.innerHTML = addOpts;
    }

    // Populate Edit modal dropdown
    if (editSelect) {
      let editOpts = '<option value="">Select Category...</option>';
      availableCategories.forEach(cat => {
        editOpts += `<option value="${cat.category_id}">${cat.category_name}</option>`;
      });
      editSelect.innerHTML = editOpts;
    }

  } catch (err) {
    console.error("Failed to load categories for dropdowns:", err);
  }
}

/**
 * Fetch and render products with filters and sorting
 */
async function loadProducts() {
  const search = document.getElementById("productSearchInput")?.value || "";
  const category_id = document.getElementById("productCategoryFilter")?.value || "";
  const status = document.getElementById("productStatusFilter")?.value || "";
  const sortVal = document.getElementById("productSortFilter")?.value || "product_name_asc";

  let sort_by = "product_name";
  let sort_order = "asc";

  if (sortVal === "product_name_desc") {
    sort_by = "product_name";
    sort_order = "desc";
  } else if (sortVal === "price_asc") {
    sort_by = "selling_price";
    sort_order = "asc";
  } else if (sortVal === "price_desc") {
    sort_by = "selling_price";
    sort_order = "desc";
  } else if (sortVal === "stock_asc") {
    sort_by = "stock";
    sort_order = "asc";
  }

  const tbody = document.getElementById("productsTableBody");
  const countBadge = document.getElementById("productCountBadge");

  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="9">
          <div class="state-container">
            <p>Fetching products from Supabase...</p>
          </div>
        </td>
      </tr>
    `;
  }

  try {
    const res = await ProductAPI.list({
      search,
      category_id,
      status,
      sort_by,
      sort_order
    });

    currentProducts = res.data || [];

    if (countBadge) {
      countBadge.textContent = `${currentProducts.length} Product${currentProducts.length === 1 ? '' : 's'}`;
    }

    if (!currentProducts || currentProducts.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="state-container">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <path d="M16 10a4 4 0 0 1-8 0"></path>
              </svg>
              <h4>No Products Found</h4>
              <p>No products matched your search or filter criteria.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    let html = "";
    currentProducts.forEach(prod => {
      const isLowStock = (prod.stock <= prod.reorder_level);
      const isActive = (prod.status === "Active");
      const statusBadge = isActive ? "badge-success" : "badge-danger";
      const nextStatus = isActive ? "Inactive" : "Active";
      const toggleLabel = isActive ? "Deactivate" : "Activate";

      html += `
        <tr>
          <td><strong>#${prod.product_id}</strong></td>
          <td style="font-weight: 600; color: #fff;">${prod.product_name}</td>
          <td><span style="font-family: monospace; background: rgba(255,255,255,0.06); padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; border: 1px solid var(--border-subtle);">${prod.sku}</span></td>
          <td><span class="badge badge-purple">${prod.category_name}</span></td>
          <td style="font-weight: 600; color: var(--accent-cyan);">₹${Number(prod.selling_price).toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
          <td>
            ${isLowStock ? 
              `<span class="badge badge-warning" style="font-weight: 700;">⚠️ ${prod.stock}</span>` : 
              `<strong style="color: var(--success);">${prod.stock}</strong>`
            }
          </td>
          <td style="color: var(--text-muted);">${prod.reorder_level}</td>
          <td><span class="badge ${statusBadge}">${prod.status}</span></td>
          <td style="text-align: right;">
            <button class="btn-action-sm" onclick="viewProduct(${prod.product_id})" title="View Details">View</button>
            <button class="btn-action-sm" onclick="editProduct(${prod.product_id})" title="Edit Product">Edit</button>
            <button class="btn-action-sm" onclick="toggleProductStatus(${prod.product_id}, '${nextStatus}')" style="color: ${isActive ? 'var(--danger)' : 'var(--success)'};">
              ${toggleLabel}
            </button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;

  } catch (err) {
    console.error("Failed to load products:", err);
    showToast("Unable to load products from database.", "danger");
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9">
            <div class="state-container">
              <h4>Error Loading Products</h4>
              <p>${err.message}</p>
              <button class="btn-primary" onclick="window.reloadProducts()">Retry</button>
            </div>
          </td>
        </tr>
      `;
    }
  }
}

window.reloadProducts = loadProducts;

/**
 * View Product full details in modal
 */
window.viewProduct = async (id) => {
  openModal("viewProductModal");
  const body = document.getElementById("viewProdBody");
  const title = document.getElementById("viewProdTitle");
  body.innerHTML = "<p>Loading product profile...</p>";

  try {
    const res = await ProductAPI.getById(id);
    const prod = res.data;
    title.textContent = `Product #${prod.product_id}: ${prod.product_name}`;

    const isLowStock = prod.stock <= prod.reorder_level;

    body.innerHTML = `
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Product Name</span>
          <h4 style="margin-top: 2px;">${prod.product_name}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">SKU Code</span>
          <h4 style="margin-top: 2px; font-family: monospace;">${prod.sku}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Category</span>
          <h4 style="margin-top: 2px;">${prod.category_name}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Selling Price</span>
          <h4 style="margin-top: 2px; color: var(--accent-cyan);">₹${Number(prod.selling_price).toLocaleString(undefined, { minimumFractionDigits: 2 })}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Current Stock In Hand</span>
          <h4 style="margin-top: 2px; color: ${isLowStock ? 'var(--warning)' : 'var(--success)'};">${prod.stock} Units ${isLowStock ? '(Low Stock Alert)' : ''}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Reorder Level Threshold</span>
          <h4 style="margin-top: 2px;">${prod.reorder_level} Units</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Status</span>
          <h4 style="margin-top: 2px; color: ${prod.status === 'Active' ? 'var(--success)' : 'var(--danger)'};">${prod.status}</h4>
        </div>
        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm);">
          <span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase;">Inventory Last Updated</span>
          <h4 style="margin-top: 2px; font-size: 0.85rem;">${formatDate(prod.last_updated)}</h4>
        </div>
      </div>

      <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 16px; margin-top: 10px;">
        <h4 style="font-size: 0.88rem; font-weight: 600; margin-bottom: 8px;">Inventory Health Status</h4>
        <div style="width: 100%; height: 8px; background: rgba(255,255,255,0.08); border-radius: 4px; overflow: hidden; margin-bottom: 8px;">
          <div style="width: ${Math.min(100, Math.max(10, (prod.stock / (prod.reorder_level * 2 || 20)) * 100))}%; height: 100%; background: ${isLowStock ? 'var(--warning)' : 'var(--success)'}; transition: width 0.4s ease;"></div>
        </div>
        <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-muted);">
          <span>Stock: <strong>${prod.stock}</strong></span>
          <span>Threshold: <strong>${prod.reorder_level}</strong></span>
          <span>Status: <strong style="color: ${isLowStock ? 'var(--warning)' : 'var(--success)'};">${isLowStock ? 'Reorder Needed' : 'Healthy'}</strong></span>
        </div>
      </div>
    `;

  } catch (err) {
    body.innerHTML = `<p style="color: var(--danger);">Failed to load product details: ${err.message}</p>`;
  }
};

/**
 * Open Edit Product Modal
 */
window.editProduct = (id) => {
  const prod = currentProducts.find(p => p.product_id === id);
  if (!prod) return;

  document.getElementById("editProdId").value = prod.product_id;
  document.getElementById("editProdName").value = prod.product_name;
  document.getElementById("editProdCategory").value = prod.category_id;
  document.getElementById("editProdSku").value = prod.sku;
  document.getElementById("editProdPrice").value = prod.selling_price;
  document.getElementById("editProdReorder").value = prod.reorder_level;
  document.getElementById("editProdStatus").value = prod.status;

  openModal("editProductModal");
};

/**
 * Toggle Product Status (Active / Inactive)
 */
window.toggleProductStatus = async (id, newStatus) => {
  if (!confirm(`Are you sure you want to change status of Product #${id} to ${newStatus}?`)) {
    return;
  }

  try {
    await ProductAPI.toggleStatus(id, newStatus);
    showToast(`Product #${id} marked as ${newStatus}`, "success");
    loadProducts();
  } catch (err) {
    showToast(`Failed to update status: ${err.message}`, "danger");
  }
};

document.addEventListener("DOMContentLoaded", async () => {
  // Load categories first so dropdowns are available
  await loadCategoriesList();
  // Then load products
  await loadProducts();

  // Search input with debounce
  const searchInput = document.getElementById("productSearchInput");
  let debounceTimer;
  searchInput?.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadProducts();
    }, 300);
  });

  // Filter change listeners
  document.getElementById("productCategoryFilter")?.addEventListener("change", loadProducts);
  document.getElementById("productStatusFilter")?.addEventListener("change", loadProducts);
  document.getElementById("productSortFilter")?.addEventListener("change", loadProducts);

  // Refresh button
  document.getElementById("refreshProductsBtn")?.addEventListener("click", () => {
    loadProducts();
    showToast("Products refreshed", "info");
  });

  // Open Add Product Modal
  document.getElementById("openAddProductModalBtn")?.addEventListener("click", () => {
    document.getElementById("addProductForm").reset();
    document.getElementById("addProdReorder").value = "10";
    document.getElementById("addProdStock").value = "0";
    document.getElementById("addProdStatus").value = "Active";
    openModal("addProductModal");
  });

  // Add Product Form submit
  document.getElementById("addProductForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const product_name = document.getElementById("addProdName").value.trim();
    const category_id = document.getElementById("addProdCategory").value;
    const sku = document.getElementById("addProdSku").value.trim();
    const selling_price = parseFloat(document.getElementById("addProdPrice").value);
    const reorder_level = parseInt(document.getElementById("addProdReorder").value, 10) || 10;
    const initial_stock = parseInt(document.getElementById("addProdStock").value, 10) || 0;
    const status = document.getElementById("addProdStatus").value;

    if (!product_name || !category_id || !sku || isNaN(selling_price)) {
      showToast("Please fill all required fields correctly", "warning");
      return;
    }

    try {
      await ProductAPI.create({
        product_name,
        category_id: parseInt(category_id, 10),
        sku,
        selling_price,
        reorder_level,
        initial_stock,
        status
      });

      showToast(`Product "${product_name}" created successfully`, "success");
      closeModal("addProductModal");
      document.getElementById("addProductForm").reset();
      loadProducts();
    } catch (err) {
      showToast(`Failed to create product: ${err.message}`, "danger");
    }
  });

  // Edit Product Form submit
  document.getElementById("editProductForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("editProdId").value;
    const product_name = document.getElementById("editProdName").value.trim();
    const category_id = document.getElementById("editProdCategory").value;
    const sku = document.getElementById("editProdSku").value.trim();
    const selling_price = parseFloat(document.getElementById("editProdPrice").value);
    const reorder_level = parseInt(document.getElementById("editProdReorder").value, 10) || 10;
    const status = document.getElementById("editProdStatus").value;

    if (!product_name || !category_id || !sku || isNaN(selling_price)) {
      showToast("Please fill all required fields correctly", "warning");
      return;
    }

    try {
      await ProductAPI.update(id, {
        product_name,
        category_id: parseInt(category_id, 10),
        sku,
        selling_price,
        reorder_level,
        status
      });

      showToast(`Product #${id} updated successfully`, "success");
      closeModal("editProductModal");
      loadProducts();
    } catch (err) {
      showToast(`Failed to update product: ${err.message}`, "danger");
    }
  });
});
