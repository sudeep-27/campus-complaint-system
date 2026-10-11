/* ============================================================
   Campus Complaint Management System - Dashboard JavaScript
   Handles: Sidebar, Charts, Tables, Modals, Filters
   ============================================================ */

'use strict';

// ══════════════════════════════════════════════════════════════
//  SIDEBAR MANAGER
// ══════════════════════════════════════════════════════════════
const Sidebar = {
  sidebar:   null,
  content:   null,
  toggle:    null,
  overlay:   null,
  collapsed: false,
  isMobile:  false,

  init() {
    this.sidebar = document.getElementById('sidebar');
    this.content = document.getElementById('mainContent');
    this.toggle  = document.getElementById('sidebarToggle');
    this.overlay = document.getElementById('sidebarOverlay');
    if (!this.sidebar) return;

    this.isMobile = window.innerWidth < 992;
    this.bindEvents();
    this.setActive();
    this.restoreState();
  },

  bindEvents() {
    if (this.toggle) {
      this.toggle.addEventListener('click', () => this.toggleSidebar());
    }

    document.querySelectorAll('.mobile-menu-btn').forEach(btn => {
      btn.addEventListener('click', () => this.openMobile());
    });

    if (this.overlay) {
      this.overlay.addEventListener('click', () => this.closeMobile());
    }

    window.addEventListener('resize', () => {
      this.isMobile = window.innerWidth < 992;
      if (!this.isMobile) this.closeMobile();
    });
  },

  toggleSidebar() {
    this.collapsed = !this.collapsed;
    this.sidebar.classList.toggle('collapsed', this.collapsed);
    if (this.content)  this.content.classList.toggle('expanded', this.collapsed);
    if (this.toggle)   this.toggle.classList.toggle('collapsed', this.collapsed);
    localStorage.setItem('ccms_sidebar', this.collapsed ? 'collapsed' : 'open');
  },

  openMobile() {
    this.sidebar.classList.add('open');
    if (this.overlay) { this.overlay.classList.add('visible'); }
    document.body.style.overflow = 'hidden';
  },

  closeMobile() {
    this.sidebar.classList.remove('open');
    if (this.overlay) { this.overlay.classList.remove('visible'); }
    document.body.style.overflow = '';
  },

  restoreState() {
    if (this.isMobile) return;
    const saved = localStorage.getItem('ccms_sidebar');
    if (saved === 'collapsed') {
      this.collapsed = true;
      this.sidebar.classList.add('collapsed');
      if (this.content) this.content.classList.add('expanded');
      if (this.toggle)  this.toggle.classList.add('collapsed');
    }
  },

  setActive() {
    const path = window.location.pathname.split('/').pop() || 'dashboard.html';
    document.querySelectorAll('.nav-item-custom').forEach(item => {
      const href = item.getAttribute('href') || '';
      item.classList.toggle('active', href.includes(path));
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  STAT WIDGET ANIMATIONS
// ══════════════════════════════════════════════════════════════
const StatWidgets = {
  init() {
    // Animate progress bars
    document.querySelectorAll('.stat-widget-bar-fill').forEach(bar => {
      const target = bar.getAttribute('data-width') || '0%';
      setTimeout(() => { bar.style.width = target; }, 300);
    });

    // Animate counter values
    document.querySelectorAll('.stat-widget-value[data-counter]').forEach(el => {
      const target = parseInt(el.getAttribute('data-counter'), 10);
      const suffix = el.getAttribute('data-suffix') || '';
      let current = 0;
      const increment = Math.ceil(target / 60);
      const timer = setInterval(() => {
        current = Math.min(current + increment, target);
        el.textContent = current.toLocaleString() + suffix;
        if (current >= target) clearInterval(timer);
      }, 20);
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  BAR CHART RENDERER (Canvas-free, pure CSS)
// ══════════════════════════════════════════════════════════════
const BarChart = {
  init() {
    document.querySelectorAll('.chart-bar[data-height]').forEach(bar => {
      const h = bar.getAttribute('data-height') || '0%';
      setTimeout(() => { bar.style.height = h; }, 400);
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  COMPLAINT TABLE FILTER & SEARCH
// ══════════════════════════════════════════════════════════════
const TableManager = {
  currentPage: 1,
  perPage:     8,
  rows:        [],

  init() {
    const table = document.getElementById('complaintsTable');
    if (!table) return;
    this.rows = Array.from(table.querySelectorAll('tbody tr'));
    this.bindFilters();
    this.renderPage();
  },

  bindFilters() {
    const search   = document.getElementById('tableSearch');
    const status   = document.getElementById('filterStatus');
    const priority = document.getElementById('filterPriority');
    const dept     = document.getElementById('filterDept');

    [search, status, priority, dept].forEach(el => {
      if (el) el.addEventListener('input', () => { this.currentPage = 1; this.filter(); });
    });
  },

  filter() {
    const search   = (document.getElementById('tableSearch')?.value   || '').toLowerCase();
    const status   = (document.getElementById('filterStatus')?.value  || '');
    const priority = (document.getElementById('filterPriority')?.value|| '');

    this.rows.forEach(row => {
      const text   = row.textContent.toLowerCase();
      const rowSt  = row.getAttribute('data-status')   || '';
      const rowPr  = row.getAttribute('data-priority') || '';

      const matches =
        (!search   || text.includes(search)) &&
        (!status   || rowSt  === status)     &&
        (!priority || rowPr  === priority);

      row.style.display = matches ? '' : 'none';
    });

    this.renderPage();
  },

  renderPage() {
    const visible = this.rows.filter(r => r.style.display !== 'none');
    const total   = visible.length;
    const pages   = Math.ceil(total / this.perPage) || 1;
    this.currentPage = Math.min(this.currentPage, pages);

    visible.forEach((row, i) => {
      row.style.display = (i >= (this.currentPage - 1) * this.perPage &&
                            i <   this.currentPage * this.perPage) ? '' : 'none';
    });

    this.renderPagination(pages, total);
  },

  renderPagination(pages, total) {
    const container = document.getElementById('tablePagination');
    if (!container) return;

    const info = `Showing ${Math.min((this.currentPage - 1) * this.perPage + 1, total)}–${Math.min(this.currentPage * this.perPage, total)} of ${total}`;

    let btns = `
      <button class="page-btn" onclick="TableManager.goto(${this.currentPage - 1})" ${this.currentPage === 1 ? 'disabled' : ''}>‹</button>
    `;

    for (let p = 1; p <= pages; p++) {
      if (pages > 7 && p > 2 && p < pages - 1 && Math.abs(p - this.currentPage) > 1) {
        if (p === 3 || p === pages - 2) btns += '<span style="padding:0 4px;color:var(--text-muted)">…</span>';
        continue;
      }
      btns += `<button class="page-btn ${p === this.currentPage ? 'active' : ''}" onclick="TableManager.goto(${p})">${p}</button>`;
    }

    btns += `<button class="page-btn" onclick="TableManager.goto(${this.currentPage + 1})" ${this.currentPage === pages ? 'disabled' : ''}>›</button>`;
    btns += `<span class="page-info">${info}</span>`;

    container.innerHTML = btns;
  },

  goto(page) {
    const visible = this.rows.filter(r => r.style.display !== 'none');
    const pages   = Math.ceil(visible.length / this.perPage) || 1;
    if (page < 1 || page > pages) return;
    this.currentPage = page;
    this.renderPage();
  }
};

// Make globally accessible for onclick pagination
window.TableManager = TableManager;

// ══════════════════════════════════════════════════════════════
//  COMPLAINT DETAIL MODAL
// ══════════════════════════════════════════════════════════════
const ComplaintModal = {
  modal: null,

  init() {
    this.modal = document.getElementById('complaintDetailModal');
  },

  open(id) {
    const data = (window.DUMMY_COMPLAINTS || DUMMY_COMPLAINTS).find(c => c.id === id);
    if (!data || !this.modal) return;

    this.modal.querySelector('#modalComplaintId').textContent   = '#' + data.id;
    this.modal.querySelector('#modalTitle').textContent         = data.title;
    this.modal.querySelector('#modalStatus').innerHTML          = this.statusBadge(data.status);
    this.modal.querySelector('#modalPriority').innerHTML        = this.priorityBadge(data.priority);
    this.modal.querySelector('#modalCategory').textContent      = data.category;
    this.modal.querySelector('#modalDepartment').textContent    = data.dept;
    this.modal.querySelector('#modalStudent').textContent       = data.student;
    this.modal.querySelector('#modalDate').textContent          = data.date;
    this.modal.querySelector('#modalDescription').textContent   = data.description;
    this.modal.querySelector('#modalAssigned').textContent      = data.assigned || 'Unassigned';

    const bsModal = new bootstrap.Modal(this.modal);
    bsModal.show();
  },

  statusBadge(s) {
    const map = { pending:'badge-pending', resolved:'badge-resolved', in_progress:'badge-progress', rejected:'badge-rejected', under_review:'badge-review' };
    return `<span class="badge-status ${map[s] || ''}">${s.replace('_',' ')}</span>`;
  },

  priorityBadge(p) {
    const map = { low:'priority-low', medium:'priority-medium', high:'priority-high', critical:'priority-critical' };
    return `<span class="priority-badge ${map[p] || ''}">${p}</span>`;
  }
};

window.ComplaintModal = ComplaintModal;

// ══════════════════════════════════════════════════════════════
//  STATUS UPDATE MODAL
// ══════════════════════════════════════════════════════════════
const StatusModal = {
  currentId: null,

  open(id) {
    this.currentId = id;
    const modal = document.getElementById('updateStatusModal');
    if (!modal) return;
    document.getElementById('statusComplaintId').textContent = '#' + id;
    new bootstrap.Modal(modal).show();
  },

  submit() {
    const status  = document.getElementById('newStatus')?.value;
    const remark  = document.getElementById('statusRemark')?.value;
    if (!status) { Toast.warning('Select Status', 'Please choose a status.'); return; }

    const btn = document.querySelector('#updateStatusModal button[type="submit"]');
    const oldText = btn ? btn.textContent : 'Update Status';
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Updating...';
    }

    fetch('/api/update-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ complaint_id: this.currentId, status: status, remark: remark })
    })
    .then(res => res.json())
    .then(data => {
      if (btn) {
        btn.disabled = false;
        btn.textContent = oldText;
      }
      if (data.success) {
        Toast.success('Status Updated', `Complaint #${this.currentId} status updated successfully.`);
        bootstrap.Modal.getInstance(document.getElementById('updateStatusModal'))?.hide();
        // Update table row visually
        const row = document.querySelector(`tr[data-id="${this.currentId}"]`);
        if (row) {
          const cell = row.querySelector('.status-cell');
          if (cell) cell.innerHTML = ComplaintModal.statusBadge(status);
          row.setAttribute('data-status', status);
        }
        DashboardStats.refresh();
      } else {
        Toast.error('Update Failed', data.message || 'Error updating status.');
      }
    })
    .catch(err => {
      console.error(err);
      if (btn) {
        btn.disabled = false;
        btn.textContent = oldText;
      }
      Toast.error('Server Error', 'Failed to connect to backend server.');
    });
  }
};

window.StatusModal = StatusModal;

// ══════════════════════════════════════════════════════════════
//  ASSIGN STAFF MODAL
// ══════════════════════════════════════════════════════════════
const AssignModal = {
  currentId: null,
  open(id) {
    this.currentId = id;
    const modal = document.getElementById('assignStaffModal');
    if (!modal) return;
    document.getElementById('assignComplaintId').textContent = '#' + id;
    new bootstrap.Modal(modal).show();
  },
  submit() {
    const staff = document.getElementById('assignStaff')?.value;
    if (!staff) { Toast.warning('Select Staff', 'Please choose a staff member.'); return; }

    const btn = document.querySelector('#assignStaffModal button[type="submit"]');
    const oldText = btn ? btn.textContent : 'Assign Officer';
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Assigning...';
    }

    fetch('/api/assign-staff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ complaint_id: this.currentId, staff: staff })
    })
    .then(res => res.json())
    .then(data => {
      if (btn) {
        btn.disabled = false;
        btn.textContent = oldText;
      }
      if (data.success) {
        Toast.success('Staff Assigned', `Complaint #${this.currentId} assigned to ${staff}`);
        bootstrap.Modal.getInstance(document.getElementById('assignStaffModal'))?.hide();
        // Update table row visually without page reload
        const row = document.querySelector(`tr[data-id="${this.currentId}"]`);
        if (row) {
          const staffCell = row.cells[5];
          if (staffCell) {
            staffCell.innerHTML = `<span style="font-size:0.78rem;font-weight:500;">${staff}</span>`;
          }
          const statusCell = row.querySelector('.status-cell');
          if (statusCell) {
            statusCell.innerHTML = ComplaintModal.statusBadge('in_progress');
          }
          row.setAttribute('data-status', 'in_progress');
        }
        DashboardStats.refresh();
      } else {
        Toast.error('Assignment Failed', data.message || 'Error assigning staff officer.');
      }
    })
    .catch(err => {
      console.error(err);
      if (btn) {
        btn.disabled = false;
        btn.textContent = oldText;
      }
      Toast.error('Server Error', 'Failed to connect to backend server.');
    });
  }
};

window.AssignModal = AssignModal;

// ══════════════════════════════════════════════════════════════
//  DELETE CONFIRMATION (calls real API + renumbers rows)
// ══════════════════════════════════════════════════════════════
const DeleteConfirm = {
  confirm(id) {
    if (!confirm(`Are you sure you want to delete Complaint #${id}? This action is permanent and cannot be undone.`)) return;

    fetch('/api/delete-complaint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ complaint_id: id })
    })
    .then(r => r.json())
    .then(data => {
      if (data.success) {
        const row = document.querySelector(`tr[data-id="${id}"]`);
        if (row) {
          row.style.animation = 'fadeOut 0.4s ease forwards';
          setTimeout(() => {
            row.remove();
            TableManager.rows = TableManager.rows.filter(r => r !== row);
            // Re-number all visible complaint badges sequentially
            DeleteConfirm.renumberRows();
            TableManager.renderPage();
            DashboardStats.refresh();
          }, 400);
        }
        Toast.success('Deleted', data.message);
      } else {
        Toast.error('Delete Failed', data.message || 'Could not delete the complaint.');
      }
    })
    .catch(err => {
      Toast.error('Error', 'Network error. Please try again.');
      console.error('Delete error:', err);
    });
  },

  renumberRows() {
    const allBadges = document.querySelectorAll('tbody .complaint-id-badge');
    allBadges.forEach((badge, i) => {
      badge.textContent = `#${i + 1}`;
    });
  }
};

window.DeleteConfirm = DeleteConfirm;

// ══════════════════════════════════════════════════════════════
//  DASHBOARD STATISTICS REFRESH
// ══════════════════════════════════════════════════════════════
const DashboardStats = {
  refresh() {
    fetch('/api/dashboard-stats')
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) {
              el.textContent = val;
              el.setAttribute('data-counter', val);
            }
          };
          setVal('statTotal', data.total);
          setVal('statResolved', data.resolved);
          setVal('statPending', data.pending);
          setVal('statInProgress', data.in_progress);

          const headerTotal = document.getElementById('statHeaderTotal');
          if (headerTotal) {
            if (headerTotal.textContent.includes('total')) {
              headerTotal.textContent = `↑ ${data.total} total`;
            }
          }

          // Donut chart logic
          if (data.total > 0) {
            const rate = Math.round(data.resolved / data.total * 100);
            const prog = Math.round(data.in_progress / data.total * 100);
            const pend = Math.round(data.pending / data.total * 100);

            const valEl = document.getElementById('donutValue');
            if (valEl) valEl.textContent = `${rate}%`;

            const chart = document.getElementById('donutChart');
            if (chart) {
              const legRes = document.getElementById('legendResolved');
              if (legRes && (legRes.innerHTML.includes('#10b981') || legRes.innerHTML.includes('background:#10b981'))) {
                // Admin dashboard (4 colors conic gradient including rejected/danger)
                chart.style.background = `conic-gradient(var(--success) 0% ${rate}%, var(--primary-light) ${rate}% ${rate + prog}%, var(--warning) ${rate + prog}% ${rate + prog + pend}%, var(--danger) ${rate + prog + pend}% 100%)`;
              } else {
                // Student dashboard (3 colors)
                chart.style.background = `conic-gradient(var(--success) 0% ${rate}%, var(--primary-light) ${rate}% ${rate + prog}%, rgba(0,0,0,0.06) ${rate + prog}% 100%)`;
              }
            }
          } else {
            const valEl = document.getElementById('donutValue');
            if (valEl) valEl.textContent = `0%`;
            const chart = document.getElementById('donutChart');
            if (chart) chart.style.background = 'rgba(0,0,0,0.06)';
          }

          // Legend counts
          const legRes = document.getElementById('legendResolved');
          if (legRes) {
            if (legRes.innerHTML.includes('#10b981') || legRes.innerHTML.includes('background:#10b981')) {
              legRes.innerHTML = `<div class="legend-dot" style="background:#10b981"></div>Resolved (${data.resolved})`;
            } else {
              legRes.innerHTML = `<div class="legend-dot" style="background:var(--success)"></div>Resolved (${data.resolved})`;
            }
          }
          const legProg = document.getElementById('legendInProgress');
          if (legProg) {
            if (legProg.innerHTML.includes('#6366f1') || legProg.innerHTML.includes('background:#6366f1')) {
              legProg.innerHTML = `<div class="legend-dot" style="background:#6366f1"></div>In Progress (${data.in_progress})`;
            } else {
              legProg.innerHTML = `<div class="legend-dot" style="background:var(--primary-light)"></div>In Progress (${data.in_progress})`;
            }
          }
          const legPend = document.getElementById('legendPending');
          if (legPend) {
            if (legPend.innerHTML.includes('#f59e0b') || legPend.innerHTML.includes('background:#f59e0b')) {
              legPend.innerHTML = `<div class="legend-dot" style="background:#f59e0b"></div>Pending (${data.pending})`;
            } else {
              legPend.innerHTML = `<div class="legend-dot" style="background:var(--warning)"></div>Pending (${data.pending})`;
            }
          }
        }
      })
      .catch(err => console.error('Error refreshing stats:', err));
  }
};

window.DashboardStats = DashboardStats;

// ══════════════════════════════════════════════════════════════
//  NOTIFICATIONS PANEL
// ══════════════════════════════════════════════════════════════
const NotifPanel = {
  init() {
    // Mark all read
    document.getElementById('markAllRead')?.addEventListener('click', () => {
      fetch('/api/mark-notifications-read', { method: 'POST' })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          document.querySelectorAll('.notif-item.unread').forEach(n => n.classList.remove('unread'));
          document.querySelectorAll('.notif-dot-indicator').forEach(d => d.remove());
          const dot = document.querySelector('.notif-dot');
          if (dot) dot.remove();
          Toast.info('Notifications', 'All notifications marked as read.');
        } else {
          Toast.error('Failed', 'Could not update read status.');
        }
      })
      .catch(err => {
        console.error(err);
        Toast.error('Server Error', 'Could not connect to backend.');
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  PROFILE PAGE
// ══════════════════════════════════════════════════════════════
const ProfilePage = {
  init() {
    const form = document.getElementById('profileForm');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      const phone = document.getElementById('profilePhone').value;
      const dept = document.getElementById('profileDept').value;
      btn.disabled = true;
      btn.textContent = 'Saving...';
      
      fetch('/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: phone, department: dept })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.textContent = 'Save Changes';
        if (data.success) {
          Toast.success('Profile Updated', 'Your profile changes have been saved.');
        } else {
          Toast.error('Update Failed', data.message || 'Error updating profile details.');
        }
      })
      .catch(err => {
        console.error(err);
        btn.disabled = false;
        btn.textContent = 'Save Changes';
        Toast.error('Server Error', 'Failed to connect to backend server.');
      });
    });

    const pwForm = document.getElementById('changePasswordForm');
    if (!pwForm) return;
    pwForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const current_pw = document.getElementById('currentPassword')?.value;
      const np = document.getElementById('password')?.value;
      const cp = document.getElementById('confirmPassword')?.value;
      if (np !== cp) { Toast.error('Mismatch', 'New passwords do not match.'); return; }
      
      const btn = pwForm.querySelector('[type="submit"]');
      btn.disabled = true;
      btn.textContent = 'Changing...';

      fetch('/api/change-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ current_password: current_pw, new_password: np })
      })
      .then(res => res.json())
      .then(data => {
        btn.disabled = false;
        btn.textContent = 'Change Password';
        if (data.success) {
          Toast.success('Password Changed', 'Your password has been updated successfully.');
          pwForm.reset();
          const strengthFill = document.getElementById('strengthFill');
          if (strengthFill) strengthFill.style.width = '0%';
          const strengthLabel = document.getElementById('strengthLabel');
          if (strengthLabel) strengthLabel.textContent = '';
        } else {
          Toast.error('Failed', data.message || 'Password update failed.');
        }
      })
      .catch(err => {
        console.error(err);
        btn.disabled = false;
        btn.textContent = 'Change Password';
        Toast.error('Server Error', 'Failed to connect to backend server.');
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  COMPLAINT SUBMIT FORM
// ══════════════════════════════════════════════════════════════
const ComplaintForm = {
  init() {
    const form = document.getElementById('submitComplaintForm');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      btn.disabled = true;
      btn.innerHTML = '<span style="display:inline-block;width:16px;height:16px;border:2px solid rgba(255,255,255,0.4);border-top-color:#fff;border-radius:50%;animation:spin 0.8s linear infinite;margin-right:8px;vertical-align:middle"></span>Submitting...';

      // Real FormData submission (since we support attachments!)
      const formData = new FormData(form);
      // Ensure we get the correct priority radio value if set
      const selectedPriority = form.querySelector('input[name="priority"]:checked')?.value || 'medium';
      formData.set('priority', selectedPriority);

      // Check for isAnonymous checkbox
      const isAnon = document.getElementById('isAnonymous')?.checked ? '1' : '0';
      formData.set('anonymous', isAnon);

      fetch('/complaint', {
        method: 'POST',
        body: formData
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          Toast.success('Complaint Submitted!', 'Your complaint has been registered. Track it in My Complaints.');
          form.reset();
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-send me-2"></i>Submit Complaint';
          document.querySelectorAll('.priority-option').forEach(o => { o.className = 'priority-option'; });
          const uploadText = document.querySelector('.upload-text');
          if (uploadText) uploadText.textContent = 'Click or drag file here to upload';
          setTimeout(() => { window.location.href = 'tracking.html'; }, 1500);
        } else {
          Toast.error('Submission Failed', data.message || 'Error submitting complaint.');
          btn.disabled = false;
          btn.innerHTML = '<i class="bi bi-send me-2"></i>Submit Complaint';
        }
      })
      .catch(err => {
        console.error(err);
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send me-2"></i>Submit Complaint';
        Toast.error('Server Error', 'Failed to connect to backend server.');
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  DUMMY DATA (realistic demo)
// ══════════════════════════════════════════════════════════════
const DUMMY_COMPLAINTS = [
  { id: 1001, title: 'WiFi Not Working in Block B Lab',         status: 'in_progress', priority: 'high',     category: 'Network / WiFi Issue',      dept: 'IT & Infrastructure',  student: 'Arjun Mehta',   date: '2025-05-10', description: 'The WiFi in Block B Computer Lab has been down since Monday. Students are unable to access online resources during lab sessions.', assigned: 'Ravi Shankar' },
  { id: 1002, title: 'Hostel Room 204 Plumbing Issue',          status: 'pending',     priority: 'critical', category: 'Hostel Maintenance',           dept: 'Hostel & Facilities', student: 'Priya Sharma',  date: '2025-05-12', description: 'The bathroom pipe in Room 204, Block C hostel is leaking and causing water damage to the floor.', assigned: null },
  { id: 1003, title: 'Library Books Missing from Shelf',        status: 'resolved',    priority: 'low',      category: 'Library Book Availability',    dept: 'Library',             student: 'Rohit Kumar',   date: '2025-05-08', description: 'Multiple books on Advanced Algorithms (Cormen) are missing from the shelves and not logged as borrowed.', assigned: 'Ms. Priya Nair' },
  { id: 1004, title: 'Canteen Food Quality - Stale Items',      status: 'under_review',priority: 'high',     category: 'Canteen Hygiene',              dept: 'Canteen & Cafeteria', student: 'Anjali Singh',  date: '2025-05-14', description: 'The sandwiches and milk served at the canteen appear to be expired. Several students felt sick after consuming them.', assigned: null },
  { id: 1005, title: 'Faculty Not Attending Lectures',          status: 'in_progress', priority: 'medium',   category: 'Faculty Concern',              dept: 'Academic Affairs',    student: 'Vikram Das',    date: '2025-05-11', description: 'Professor Mehta has not attended 4 consecutive Data Structures lectures without any substitute arrangement.', assigned: 'Prof. Sunita Sharma' },
  { id: 1006, title: 'Sports Equipment Damaged - Cricket Kit',  status: 'pending',     priority: 'medium',   category: 'Sports Equipment Damage',      dept: 'Sports & Recreation', student: 'Karan Patel',   date: '2025-05-13', description: 'The cricket bats and pads available in the sports room are damaged and need immediate replacement before inter-college tournament.', assigned: null },
  { id: 1007, title: 'Certificate Delay - Bonafide',            status: 'resolved',    priority: 'low',      category: 'Administrative Issue',         dept: 'Administration',      student: 'Neha Joshi',    date: '2025-05-07', description: 'Applied for bonafide certificate 3 weeks ago. Still not received. Need it urgently for bank account opening.', assigned: 'Dr. Kavya Menon' },
  { id: 1008, title: 'Security Camera Malfunction - Gate 2',    status: 'rejected',    priority: 'critical', category: 'Security Concern',             dept: 'Security',            student: 'Amit Roy',      date: '2025-05-09', description: 'The CCTV camera at Gate 2 entrance has been non-functional for 2 weeks, creating a security risk.', assigned: null },
  { id: 1009, title: 'Exam Timetable Clash - CSE Sem 5',        status: 'in_progress', priority: 'high',     category: 'Exam Scheduling',              dept: 'Academic Affairs',    student: 'Sneha Verma',   date: '2025-05-15', description: 'Data Structures and DBMS exams are scheduled at the same time slot on 20th May. Need immediate correction.', assigned: 'Prof. Sunita Sharma' },
  { id: 1010, title: 'Lost Laptop Bag Near Library',            status: 'pending',     priority: 'medium',   category: 'Lost & Found',                 dept: 'Security',            student: 'Rahul Gupta',   date: '2025-05-16', description: 'Lost a black Dell laptop bag near the library entrance. Contains laptop, charger and important documents.', assigned: null },
];

window.DUMMY_COMPLAINTS = DUMMY_COMPLAINTS;

// ══════════════════════════════════════════════════════════════
//  GLOBAL INITIALISER
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  Sidebar.init();
  StatWidgets.init();
  BarChart.init();
  TableManager.init();
  ComplaintModal.init();
  NotifPanel.init();
  ProfilePage.init();
  ComplaintForm.init();

  // Animate dash content cards
  document.querySelectorAll('.content-card, .stat-widget, .tracking-card').forEach((el, i) => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    setTimeout(() => {
      el.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
      el.style.opacity = '1';
      el.style.transform = 'translateY(0)';
    }, 20 + i * 15);
  });
});
