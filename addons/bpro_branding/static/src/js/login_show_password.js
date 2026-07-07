document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".bpro-toggle-password").forEach(function (btn) {
        const input = btn.parentElement.querySelector("#password");
        const icon = btn.querySelector("i");
        if (!input) return;
        btn.addEventListener("click", function () {
            const show = input.type === "password";
            input.type = show ? "text" : "password";
            icon.classList.toggle("fa-eye", !show);
            icon.classList.toggle("fa-eye-slash", show);
            btn.setAttribute("aria-label", show ? "Hide password" : "Show password");
        });
    });
});
