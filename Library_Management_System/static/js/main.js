// Library Management System - client-side helpers (no external libraries).
(function () {
  "use strict";

  // Mobile navigation toggle
  var toggle = document.getElementById("navToggle");
  var nav = document.getElementById("mainNav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () { nav.classList.toggle("open"); });
  }

  // Dismissible alerts + auto-hide success/info messages after 6 seconds
  document.querySelectorAll(".alert").forEach(function (alertBox) {
    var close = alertBox.querySelector(".alert-close");
    if (close) close.addEventListener("click", function () { alertBox.remove(); });
    if (!alertBox.classList.contains("alert-danger")) {
      setTimeout(function () { alertBox.remove(); }, 6000);
    }
  });

  // Confirmation dialogs for destructive / important actions:
  // <form data-confirm="Are you sure?">
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      if (!window.confirm(form.getAttribute("data-confirm"))) e.preventDefault();
    });
  });

  // Live table search: filters rows as you type (Books and Members pages).
  var liveSearch = document.getElementById("liveSearch");
  var table = document.getElementById("booksTable") || document.getElementById("membersTable");
  if (liveSearch && table) {
    liveSearch.addEventListener("input", function () {
      var term = liveSearch.value.trim().toLowerCase();
      table.querySelectorAll("tbody tr").forEach(function (row) {
        if (row.querySelector(".empty")) return;
        row.style.display = row.textContent.toLowerCase().indexOf(term) === -1 ? "none" : "";
      });
    });
  }

  // Filter boxes above <select> lists on the Issue page.
  document.querySelectorAll(".select-filter").forEach(function (box) {
    var select = document.getElementById(box.getAttribute("data-target"));
    if (!select) return;
    box.addEventListener("input", function () {
      var term = box.value.trim().toLowerCase();
      Array.prototype.forEach.call(select.options, function (opt) {
        var match = opt.text.toLowerCase().indexOf(term) !== -1;
        opt.hidden = !match;
        opt.disabled = !match;
      });
    });
  });

  // Issue form: require both selections before submitting.
  var memberSelect = document.getElementById("memberSelect");
  var bookSelect = document.getElementById("bookSelect");
  if (memberSelect && bookSelect) {
    memberSelect.form.addEventListener("submit", function (e) {
      if (!memberSelect.value || !bookSelect.value) {
        e.preventDefault();
        window.alert("Please select both a member and a book.");
      }
    });
  }
})();
