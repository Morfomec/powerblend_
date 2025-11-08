document.addEventListener("DOMContentLoaded", function () {
    // ===============================
    // Chart.js Configuration
    // ===============================
    const ctx = document.getElementById('salesChart');
    if (ctx) {
        new Chart(ctx.getContext('2d'), {
            type: 'bar',
            data: {
                labels: ['JAN', 'FEB', 'MAR', 'APRIL', 'MAY', 'JUN', 'JULY', 'AUG', 'SEP', 'OCT', 'NOV'],
                datasets: [{
                    label: 'Total Users',
                    data: [0, 0, 300000, 1400000, 1200000, 200000, 1800000, 0, 0, 0, 0],
                    backgroundColor: '#28a745',
                    borderRadius: 4,
                    barThickness: 30
                }, {
                    label: 'Total Sales',
                    data: [0, 0, 250000, 1300000, 1100000, 180000, 1700000, 0, 0, 0, 0],
                    backgroundColor: '#20c997',
                    borderRadius: 4,
                    barThickness: 30
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 2000000,
                        ticks: { callback: v => v.toLocaleString() },
                        grid: { display: true, color: '#f0f0f0' }
                    },
                    x: { grid: { display: false } }
                },
                interaction: { intersect: false, mode: 'index' }
            }
        });
    }

    // ===============================
    // Sidebar Navigation with Dropdown
    // ===============================
    document.querySelectorAll('.sidebar-menu a').forEach(link => {
        link.addEventListener('click', function (e) {
            if (this.classList.contains('dropdown-toggle')) {
                e.preventDefault();
                const dropdownId = this.getAttribute('data-dropdown');
                const submenu = document.getElementById(dropdownId);
                const dropdownIcon = this.querySelector('.dropdown-icon');

                submenu.classList.toggle('open');
                dropdownIcon.classList.toggle('rotated');

                // Close others
                document.querySelectorAll('.submenu').forEach(menu => {
                    if (menu !== submenu) menu.classList.remove('open');
                });
                document.querySelectorAll('.dropdown-icon').forEach(icon => {
                    if (icon !== dropdownIcon) icon.classList.remove('rotated');
                });
            }

            document.querySelectorAll('.sidebar-menu a').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });

    document.querySelectorAll('.submenu a').forEach(link => {
        link.addEventListener('click', function () {
            document.querySelectorAll('.sidebar-menu > li > a').forEach(l => l.classList.remove('active'));
            document.querySelectorAll('.submenu a').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // ===============================
    // Confirm Modal Logic
    // ===============================
    const confirmModal = document.getElementById("confirmModal");
    if (confirmModal) {
        const confirmMessage = document.getElementById("confirmMessage");
        const confirmYes = document.getElementById("confirmYes");

        let targetUrl = null;

        // Triggered when modal opens
        confirmModal.addEventListener("show.bs.modal", function (event) {
            const button = event.relatedTarget;
            targetUrl = button.getAttribute("data-url");
            const message = button.getAttribute("data-message") || "Are you sure?";
            confirmMessage.textContent = message;
        });

        confirmYes.addEventListener("click", function () {
            if (targetUrl) {
                window.location.href = targetUrl; // Navigate to delete or action URL
            }
        });
    }
});





// document.addEventListener("DOMContentLoaded", function() {
//     // Get all dropdown toggle links
//     const dropdownToggles = document.querySelectorAll(".dropdown-toggle");

//     dropdownToggles.forEach(toggle => {
//         toggle.addEventListener("click", function(e) {
//             e.preventDefault();
//             const submenuId = this.getAttribute("data-dropdown");
//             const submenu = document.getElementById(submenuId);

//             // Toggle submenu visibility
//             if (submenu) {
//                 submenu.classList.toggle("show");
//             }

//             // Optional: close other open submenus
//             dropdownToggles.forEach(otherToggle => {
//                 const otherId = otherToggle.getAttribute("data-dropdown");
//                 if (otherId !== submenuId) {
//                     const otherSubmenu = document.getElementById(otherId);
//                     if (otherSubmenu) otherSubmenu.classList.remove("show");
//                 }
//             });
//         });
//     });
// });
