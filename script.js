console.log("FinPilot AI Loaded");

console.log("FinPilot AI Loaded");

// Auto-hide flash notifications
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".flash-message").forEach(function (message) {
        setTimeout(function () {
            message.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            message.style.opacity = "0";
            message.style.transform = "translateX(30px)";

            setTimeout(function () {
                message.remove();
            }, 500);
        }, 3500);
    });
});
