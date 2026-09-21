/**
 * SMART INVENTORY MANAGEMENT SYSTEM - CATEGORY MANAGEMENT
 * Controller for categories.html (Team 2)
 */

import { CategoryAPI } from './api.js';

let currentCategories = [];

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

window.closeModal = (modalId) => {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
};

window.openModal = (modalId) => {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("open");
};

async function loadCategories() {
  const search = document.getElementById("categorySearchInput")?.value || "";
  const tbody = document.getElementById("categoriesTableBody");
  const countBadge = document.getElementById("categoryCountBadge");

  if (tbody) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5">
          <div class="state-container">
            <p>Fetching categories from Supabase...</p>
          </div>
        </td>
      </tr>
    `;
  }

  try {
    const res = await CategoryAPI.list({ search });
    currentCategories = res.data || [];

    if (countBadge) {
      countBadge.textContent = `${currentCategories.length} Categor${currentCategories.length === 1 ? 'y' : 'ies'}`;
    }

    if (!currentCategories || currentCategories.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5">
            <div class="state-container">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
              <h4>No Categories Found</h4>
              <p>No product categories matched your search criteria.</p>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    let html = "";
    currentCategories.forEach(cat => {
      html += `
        <tr>
          <td><strong>#${cat.category_id}</strong></td>
          <td style="font-weight: 600; color: #fff;">${cat.category_name}</td>
          <td style="color: var(--text-muted); max-width: 350px;">${cat.description || '<span style="font-style: italic; opacity: 0.6;">No description provided</span>'}</td>
          <td>
            <span class="badge ${cat.product_count > 0 ? 'badge-purple' : 'badge-neutral'}">
              ${cat.product_count} Product${cat.product_count === 1 ? '' : 's'}
            </span>
          </td>
          <td style="text-align: right;">
            <button class="btn-action-sm" onclick="editCategory(${cat.category_id})" title="Edit Category">Edit</button>
            <button class="btn-action-sm" onclick="deleteCategory(${cat.category_id}, ${cat.product_count})" style="color: var(--danger);" title="Delete Category">Delete</button>
          </td>
        </tr>
      `;
    });

    tbody.innerHTML = html;

  } catch (err) {
    console.error("Failed to load categories:", err);
    showToast("Unable to load categories from database.", "danger");
    if (tbody) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5">
            <div class="state-container">
              <h4>Error Loading Categories</h4>
              <p>${err.message}</p>
              <button class="btn-primary" onclick="window.reloadCategories()">Retry</button>
            </div>
          </td>
        </tr>
      `;
    }
  }
}

window.reloadCategories = loadCategories;

window.editCategory = (id) => {
  const cat = currentCategories.find(c => c.category_id === id);
  if (!cat) return;

  document.getElementById("editCatId").value = cat.category_id;
  document.getElementById("editCatName").value = cat.category_name;
  document.getElementById("editCatDesc").value = cat.description || "";

  openModal("editCategoryModal");
};

window.deleteCategory = async (id, productCount) => {
  if (productCount > 0) {
    alert(`Cannot delete Category #${id} because it currently contains ${productCount} active product(s). Please reassign or remove the products first.`);
    return;
  }

  if (!confirm(`Are you sure you want to delete Category #${id}? This action cannot be undone.`)) {
    return;
  }

  try {
    await CategoryAPI.delete(id);
    showToast(`Category #${id} removed successfully`, "success");
    loadCategories();
  } catch (err) {
    showToast(`Delete failed: ${err.message}`, "danger");
  }
};

document.addEventListener("DOMContentLoaded", () => {
  loadCategories();

  // Search input with debounce
  const searchInput = document.getElementById("categorySearchInput");
  let debounceTimer;
  searchInput?.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      loadCategories();
    }, 300);
  });

  // Refresh button
  document.getElementById("refreshCategoriesBtn")?.addEventListener("click", () => {
    loadCategories();
    showToast("Categories refreshed", "info");
  });

  // Open Add Category Modal
  document.getElementById("openAddCategoryModalBtn")?.addEventListener("click", () => {
    document.getElementById("addCategoryForm").reset();
    openModal("addCategoryModal");
  });

  // Add Category form submission
  document.getElementById("addCategoryForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("addCatName").value.trim();
    const description = document.getElementById("addCatDesc").value.trim();

    if (!name) {
      showToast("Category name is required", "warning");
      return;
    }

    try {
      await CategoryAPI.create({
        category_name: name,
        description: description
      });

      showToast(`Category "${name}" created successfully`, "success");
      closeModal("addCategoryModal");
      document.getElementById("addCategoryForm").reset();
      loadCategories();
    } catch (err) {
      showToast(`Failed to create category: ${err.message}`, "danger");
    }
  });

  // Edit Category form submission
  document.getElementById("editCategoryForm")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("editCatId").value;
    const name = document.getElementById("editCatName").value.trim();
    const description = document.getElementById("editCatDesc").value.trim();

    if (!name) {
      showToast("Category name is required", "warning");
      return;
    }

    try {
      await CategoryAPI.update(id, {
        category_name: name,
        description: description
      });

      showToast(`Category #${id} updated successfully`, "success");
      closeModal("editCategoryModal");
      loadCategories();
    } catch (err) {
      showToast(`Failed to update category: ${err.message}`, "danger");
    }
  });
});
