/* ============================================================
   Campus Complaint Management System - Main JavaScript
   Handles: Theme, Navbar, Animations, Toasts, Loading
   ============================================================ */

'use strict';

// ══════════════════════════════════════════════════════════════
//  PAGE LOADER
// ══════════════════════════════════════════════════════════════
const PageLoader = {
  init() {
    const loader = document.getElementById('pageLoader');
    if (!loader) return;
    window.addEventListener('load', () => {
      setTimeout(() => loader.classList.add('hidden'), 600);
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  THEME MANAGER (Dark / Light Mode)
// ══════════════════════════════════════════════════════════════
const ThemeManager = {
  STORAGE_KEY: 'ccms_theme',
  current: 'light',

  init() {
    const saved = localStorage.getItem(this.STORAGE_KEY) || 'light';
    this.apply(saved);
    this.bindToggle();
  },

  apply(theme) {
    this.current = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(this.STORAGE_KEY, theme);
    this.updateIcons(theme);
  },

  toggle() {
    this.apply(this.current === 'light' ? 'dark' : 'light');
  },

  updateIcons(theme) {
    document.querySelectorAll('.theme-icon').forEach(el => {
      el.textContent = theme === 'dark' ? '☀️' : '🌙';
    });
  },

  bindToggle() {
    document.querySelectorAll('.theme-toggle').forEach(btn => {
      btn.addEventListener('click', () => this.toggle());
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  NAVBAR (scroll effect)
// ══════════════════════════════════════════════════════════════
const Navbar = {
  init() {
    const nav = document.querySelector('.main-navbar');
    if (!nav) return;
    window.addEventListener('scroll', () => {
      nav.classList.toggle('scrolled', window.scrollY > 50);
    }, { passive: true });
  }
};

// ══════════════════════════════════════════════════════════════
//  SCROLL ANIMATIONS
// ══════════════════════════════════════════════════════════════
const ScrollAnimations = {
  init() {
    const els = document.querySelectorAll('.animate-on-scroll');
    if (!els.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          e.target.classList.add('visible');
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    els.forEach(el => observer.observe(el));
  }
};

// ══════════════════════════════════════════════════════════════
//  ANIMATED COUNTERS
// ══════════════════════════════════════════════════════════════
const CounterAnimation = {
  init() {
    const counters = document.querySelectorAll('[data-counter]');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          this.animateCounter(e.target);
          observer.unobserve(e.target);
        }
      });
    }, { threshold: 0.5 });

    counters.forEach(el => observer.observe(el));
  },

  animateCounter(el) {
    const target   = parseInt(el.getAttribute('data-counter'), 10);
    const suffix   = el.getAttribute('data-suffix') || '';
    const duration = 2000;
    const start    = performance.now();

    const tick = (now) => {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const ease     = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const value    = Math.round(ease * target);
      el.textContent = value.toLocaleString() + suffix;
      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }
};

// ══════════════════════════════════════════════════════════════
//  TOAST NOTIFICATIONS
// ══════════════════════════════════════════════════════════════
const Toast = {
  container: null,
  ICONS: {
    success: '✅',
    error:   '❌',
    warning: '⚠️',
    info:    'ℹ️'
  },

  init() {
    this.container = document.getElementById('toastContainer');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toastContainer';
      this.container.className = 'toast-container-custom';
      document.body.appendChild(this.container);
    }
  },

  show(type = 'info', title = '', message = '', duration = 4000) {
    const toast = document.createElement('div');
    toast.className = `toast-custom ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${this.ICONS[type]}</span>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
      <span class="toast-close" onclick="this.parentElement.remove()">✕</span>
    `;
    this.container.appendChild(toast);
    setTimeout(() => toast.remove(), duration + 400);
  },

  success(title, message) { this.show('success', title, message); },
  error(title, message)   { this.show('error',   title, message); },
  warning(title, message) { this.show('warning', title, message); },
  info(title, message)    { this.show('info',    title, message); }
};

// ══════════════════════════════════════════════════════════════
//  BACK TO TOP BUTTON
// ══════════════════════════════════════════════════════════════
const BackToTop = {
  btn: null,
  init() {
    this.btn = document.querySelector('.back-to-top');
    if (!this.btn) return;
    window.addEventListener('scroll', () => {
      this.btn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });
    this.btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  PASSWORD VISIBILITY TOGGLE
// ══════════════════════════════════════════════════════════════
const PasswordToggle = {
  init() {
    document.querySelectorAll('.input-icon-right[data-toggle-pw]').forEach(btn => {
      btn.addEventListener('click', () => {
        const input = document.querySelector(btn.getAttribute('data-toggle-pw'));
        if (!input) return;
        const isText = input.type === 'text';
        input.type = isText ? 'password' : 'text';
        btn.textContent = isText ? '👁️' : '🙈';
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  PASSWORD STRENGTH METER
// ══════════════════════════════════════════════════════════════
const PasswordStrength = {
  init() {
    const input = document.getElementById('password');
    const bar   = document.getElementById('strengthFill');
    const label = document.getElementById('strengthLabel');
    if (!input || !bar) return;

    input.addEventListener('input', () => {
      const val = input.value;
      const score = this.score(val);
      const levels = [
        { label: 'Very Weak', color: '#ef4444', width: '20%' },
        { label: 'Weak',      color: '#f97316', width: '40%' },
        { label: 'Fair',      color: '#f59e0b', width: '60%' },
        { label: 'Strong',    color: '#10b981', width: '80%' },
        { label: 'Very Strong', color: '#059669', width: '100%' }
      ];
      const level = levels[Math.min(score, 4)];
      bar.style.width     = val.length ? level.width : '0%';
      bar.style.background = level.color;
      if (label) label.textContent = val.length ? level.label : '';
    });
  },

  score(pw) {
    let s = 0;
    if (pw.length >= 8)  s++;
    if (/[A-Z]/.test(pw)) s++;
    if (/[0-9]/.test(pw)) s++;
    if (/[^A-Za-z0-9]/.test(pw)) s++;
    return s;
  }
};

// ══════════════════════════════════════════════════════════════
//  FORM VALIDATION
// ══════════════════════════════════════════════════════════════
const FormValidator = {
  init() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
      form.addEventListener('submit', (e) => {
        if (!form.checkValidity()) {
          e.preventDefault();
          e.stopPropagation();
          form.classList.add('was-validated');
          Toast.warning('Validation Error', 'Please fill all required fields correctly.');
        }
      });
    });

    // Real-time email validation
    document.querySelectorAll('input[type="email"]').forEach(input => {
      input.addEventListener('blur', () => {
        const valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value);
        input.style.borderColor = input.value ? (valid ? 'var(--success)' : 'var(--danger)') : '';
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  FILE UPLOAD DRAG & DROP
// ══════════════════════════════════════════════════════════════
const FileUpload = {
  init() {
    document.querySelectorAll('.file-upload-area').forEach(area => {
      ['dragenter','dragover'].forEach(ev =>
        area.addEventListener(ev, e => { e.preventDefault(); area.classList.add('dragover'); })
      );
      ['dragleave','drop'].forEach(ev =>
        area.addEventListener(ev, e => {
          e.preventDefault();
          area.classList.remove('dragover');
          if (ev === 'drop') this.handleDrop(e.dataTransfer.files, area);
        })
      );
      const input = area.querySelector('input[type="file"]');
      if (input) {
        input.addEventListener('change', () => this.handleDrop(input.files, area));
      }
    });
  },

  handleDrop(files, area) {
    if (!files.length) return;
    const file = files[0];
    const allowed = ['image/jpeg','image/png','application/pdf','image/gif'];
    if (!allowed.includes(file.type)) {
      Toast.error('Invalid File', 'Please upload JPG, PNG, PDF or GIF files only.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      Toast.error('File Too Large', 'Maximum file size is 5MB.');
      return;
    }
    const label = area.querySelector('.upload-text');
    if (label) label.textContent = `✅ ${file.name}`;
    Toast.success('File Selected', `${file.name} ready to upload.`);
  }
};

// ══════════════════════════════════════════════════════════════
//  PRIORITY SELECTOR
// ══════════════════════════════════════════════════════════════
const PrioritySelector = {
  init() {
    document.querySelectorAll('.priority-option').forEach(opt => {
      opt.addEventListener('click', () => {
        document.querySelectorAll('.priority-option').forEach(o => {
          o.className = 'priority-option';
        });
        const val = opt.querySelector('input[type="radio"]')?.value || '';
        opt.classList.add('priority-option', `selected-${val}`);
        const radio = opt.querySelector('input[type="radio"]');
        if (radio) radio.checked = true;
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  SMOOTH SCROLLING FOR ANCHOR LINKS
// ══════════════════════════════════════════════════════════════
const SmoothScroll = {
  init() {
    document.querySelectorAll('a[href^="#"]').forEach(link => {
      link.addEventListener('click', (e) => {
        const target = document.querySelector(link.getAttribute('href'));
        if (target) {
          e.preventDefault();
          const offset = 80; // navbar height
          const y = target.getBoundingClientRect().top + window.scrollY - offset;
          window.scrollTo({ top: y, behavior: 'smooth' });
        }
      });
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  CONTACT FORM
// ══════════════════════════════════════════════════════════════
const ContactForm = {
  init() {
    const form = document.getElementById('contactForm');
    if (!form) return;
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const btn = form.querySelector('[type="submit"]');
      btn.disabled = true;
      btn.innerHTML = '<span class="loader-spinner" style="width:18px;height:18px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:8px"></span>Sending...';
      setTimeout(() => {
        Toast.success('Message Sent!', 'We\'ll get back to you within 24 hours.');
        form.reset();
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-send me-2"></i>Send Message';
      }, 1500);
    });
  }
};

// ══════════════════════════════════════════════════════════════
//  GLOBAL INITIALISER
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  PageLoader.init();
  ThemeManager.init();
  Navbar.init();
  ScrollAnimations.init();
  CounterAnimation.init();
  Toast.init();
  BackToTop.init();
  PasswordToggle.init();
  PasswordStrength.init();
  FormValidator.init();
  FileUpload.init();
  PrioritySelector.init();
  SmoothScroll.init();
  ContactForm.init();
});

// Expose globally for inline onclick handlers
window.Toast = Toast;
window.ThemeManager = ThemeManager;
