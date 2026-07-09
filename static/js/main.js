// BUP Contest Tracker — main.js

// Auto-dismiss alerts after 5 seconds
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => {
    el.style.transition = 'opacity .5s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 500);
  }, 5000);
});

// Highlight active nav link
const path = window.location.pathname;
document.querySelectorAll('.nav-link').forEach(link => {
  if (link.getAttribute('href') && path.startsWith(link.getAttribute('href'))) {
    link.classList.add('active');
  }
});

// Countdown timer for event end time (if present)
const countdownEl = document.getElementById('event-countdown');
if (countdownEl) {
  const endTime = new Date(countdownEl.dataset.end);
  function updateCountdown() {
    const now = new Date();
    const diff = endTime - now;
    if (diff <= 0) {
      countdownEl.textContent = 'Contest ended';
      return;
    }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);
    countdownEl.textContent = `${h}h ${m}m ${s}s remaining`;
  }
  updateCountdown();
  setInterval(updateCountdown, 1000);
}
document.addEventListener("DOMContentLoaded", function () {
    const timerCard = document.querySelector(".contest-timer-card");

    if (!timerCard) {
        return;
    }

    const startTime = new Date(timerCard.dataset.start);
    const endTime = new Date(timerCard.dataset.end);

    const startTimer = document.getElementById("contestStartTimer");
    const endTimer = document.getElementById("contestEndTimer");
    const statusText = document.getElementById("contestStatusText");

    function formatTimeDifference(milliseconds) {
        if (milliseconds <= 0) {
            return "00:00:00";
        }

        const totalSeconds = Math.floor(milliseconds / 1000);
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        return (
            String(hours).padStart(2, "0") + ":" +
            String(minutes).padStart(2, "0") + ":" +
            String(seconds).padStart(2, "0")
        );
    }

    function updateContestTimer() {
        const now = new Date();

        const timeUntilStart = startTime - now;
        const timeUntilEnd = endTime - now;

        startTimer.textContent = formatTimeDifference(timeUntilStart);
        endTimer.textContent = formatTimeDifference(timeUntilEnd);

        if (now < startTime) {
            statusText.textContent = "Contest has not started yet.";
            statusText.className = "contest-status-text upcoming";
        }
        else if (now >= startTime && now <= endTime) {
            startTimer.textContent = "Started";
            statusText.textContent = "Contest is currently ongoing.";
            statusText.className = "contest-status-text ongoing";
        }
        else {
            startTimer.textContent = "Finished";
            endTimer.textContent = "Finished";
            statusText.textContent = "Contest has ended.";
            statusText.className = "contest-status-text ended";
        }
    }

    updateContestTimer();
    setInterval(updateContestTimer, 1000);
});