document.addEventListener("DOMContentLoaded", function () {

    console.log("🏥 HMS Loaded Successfully");

    handleFlashMessages();
    handleFormConfirmation();
    handleTableHover();
    handleDashboardCounters();
    handleCardClick();

});



function handleFlashMessages() {

    let alerts = document.querySelectorAll('.alert');

    alerts.forEach(alert => {

       
        alert.style.transition = "opacity 0.3s ease";

        setTimeout(() => {
            alert.style.opacity = "0";

            setTimeout(() => {
                alert.remove();
            }, 300);

        }, 1200); 
    });
}



function handleFormConfirmation() {

    let forms = document.querySelectorAll("form");

    forms.forEach(form => {
        form.addEventListener("submit", function (e) {

            let confirmSubmit = confirm("Are you sure you want to submit?");
            if (!confirmSubmit) {
                e.preventDefault();
            }

        });
    });
}



function handleTableHover() {

    let rows = document.querySelectorAll("table tr");

    rows.forEach(row => {
        row.addEventListener("mouseenter", () => {
            row.style.backgroundColor = "#f1f1f1";
        });

        row.addEventListener("mouseleave", () => {
            row.style.backgroundColor = "";
        });
    });
}



function animateCounter(element, target) {

    let count = 0;
    let speed = 20;

    let interval = setInterval(() => {

        if (count >= target) {
            clearInterval(interval);
        } else {
            count++;
            element.innerText = count;
        }

    }, speed);
}



function handleDashboardCounters() {

    let p = document.getElementById("patients");
    let d = document.getElementById("doctors");
    let a = document.getElementById("appointments");

    if (p) animateCounter(p, parseInt(p.innerText));
    if (d) animateCounter(d, parseInt(d.innerText));
    if (a) animateCounter(a, parseInt(a.innerText));
}



function handleCardClick() {

    let cards = document.querySelectorAll(".card");

    cards.forEach(card => {
        card.addEventListener("click", function () {

            card.style.transform = "scale(0.97)";

            setTimeout(() => {
                card.style.transform = "scale(1)";
            }, 150);

        });
    });
}