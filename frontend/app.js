const API_URL = "http://localhost:8000/api";

const usernameInput = document.getElementById("username");
const syncBtn = document.getElementById("sync-btn");
const clearBtn = document.getElementById("clear-btn");
const allDoneBtn = document.getElementById("all-done-btn");
const spinBtn = document.getElementById("spin-btn");
const movieDisplay = document.getElementById("movie-display");
const modal = document.getElementById("result-modal");
const closeModal = document.querySelector(".close");
const usersListDiv = document.getElementById("users-list");

// Winner elements
const winnerTitle = document.getElementById("winner-title");
const winnerPoster = document.getElementById("winner-poster");
const winnerLink = document.getElementById("winner-link");

let movies = [];
let addedUsers = [];  // Array of {username, profile_picture}

syncBtn.addEventListener("click", async () => {
    const username = usernameInput.value.trim();
    if (!username) return alert("Please enter a username");

    syncBtn.textContent = "Adding...";
    syncBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/sync?username=${username}`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            addedUsers = data.users;
            updateUsersDisplay();
            usernameInput.value = ""; // Clear input
            // Don't load movies yet - wait for All Done
            allDoneBtn.disabled = false;
            alert(data.message);
        } else {
            alert("Error: " + data.detail);
        }
    } catch (error) {
        console.error(error);
        alert("Failed to connect to backend");
    } finally {
        syncBtn.textContent = "Add User";
        syncBtn.disabled = false;
    }
});

clearBtn.addEventListener("click", async () => {
    if (!confirm("Clear all watchlists?")) return;

    try {
        const response = await fetch(`${API_URL}/clear`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            addedUsers = [];
            movies = [];
            updateUsersDisplay();
            spinBtn.disabled = true;
            allDoneBtn.disabled = true;
            // Clear wheel
            segments = [];
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            alert(data.message);
        }
    } catch (error) {
        console.error(error);
        alert("Failed to clear");
    }
});

allDoneBtn.addEventListener("click", async () => {
    allDoneBtn.textContent = "Loading...";
    allDoneBtn.disabled = true;

    await loadMovies();

    allDoneBtn.textContent = "All Done";
});

async function removeUser(username) {
    try {
        const response = await fetch(`${API_URL}/remove?username=${username}`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            addedUsers = data.users;
            updateUsersDisplay();
            await loadMovies();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (error) {
        console.error(error);
        alert("Failed to remove user");
    }
}

function updateUsersDisplay() {
    if (addedUsers.length === 0) {
        usersListDiv.innerHTML = '<span style="color: var(--text-color); font-size: 0.9rem;">No users added</span>';
    } else {
        usersListDiv.innerHTML = addedUsers.map(user => {
            const avatarImg = user.profile_picture
                ? `<img src="${user.profile_picture}" class="user-avatar" alt="${user.username}" />`
                : `<div class="user-avatar" style="background-color: var(--accent-green);"></div>`;

            return `
                <div class="user-item">
                    <div class="user-info">
                        ${avatarImg}
                        <span>${user.username}</span>
                    </div>
                    <button class="remove-user-btn" onclick="removeUser('${user.username}')">×</button>
                </div>
            `;
        }).join('');
    }
}

async function loadMovies() {
    try {
        const response = await fetch(`${API_URL}/roulette`);
        if (response.ok) {
            movies = await response.json();
            if (movies.length > 0) {
                spinBtn.disabled = false;
                // Initial draw with random selection
                const initialSegs = movies.slice(0, SEGMENT_COUNT);
                segments = initialSegs;
                drawWheel();
            }
        }
    } catch (error) {
        console.error("Could not load movies", error);
    }
}

// Wheel configuration
const canvas = document.getElementById("roulette-wheel");
const ctx = canvas.getContext("2d");
let segments = [];
let currentRotation = 0;
const SEGMENT_COUNT = 10;
const SPIN_DURATION = 5000; // ms

// Colors
const colors = ["#00e054", "#ff8000", "#40bcf4"]; // Green, Orange, Blue

function drawWheel() {
    if (segments.length === 0) return;

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = canvas.width / 2 - 10;
    const arcSize = (2 * Math.PI) / segments.length;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    segments.forEach((movie, i) => {
        const startAngle = i * arcSize + currentRotation;
        const endAngle = startAngle + arcSize;

        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, startAngle, endAngle);
        ctx.lineTo(centerX, centerY);
        ctx.fillStyle = colors[i % colors.length];
        ctx.fill();
        ctx.stroke();

        // Text
        ctx.save();
        ctx.translate(centerX, centerY);
        ctx.rotate(startAngle + arcSize / 2);
        ctx.textAlign = "right";
        ctx.fillStyle = "#fff";
        ctx.font = "bold 24px Roboto";
        ctx.fillText(movie.title.substring(0, 20), radius - 20, 10);
        ctx.restore();
    });
}

function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}

spinBtn.addEventListener("click", async () => {
    if (movies.length === 0) return alert("Sync watchlist first!");

    spinBtn.disabled = true;

    try {
        // 1. Get official winner
        const response = await fetch(`${API_URL}/spin`);
        const winner = await response.json();

        // 2. Prepare wheel segments (Winner + 9 randoms)
        const otherMovies = movies.filter(m => m.letterboxd_url !== winner.letterboxd_url);
        // Shuffle other movies
        otherMovies.sort(() => 0.5 - Math.random());

        // Take 9 random movies and add winner
        const wheelMovies = otherMovies.slice(0, SEGMENT_COUNT - 1);
        wheelMovies.push(winner);

        // Shuffle so winner position is random
        wheelMovies.sort(() => 0.5 - Math.random());
        segments = wheelMovies;

        // Find winner index
        const winnerIndex = segments.findIndex(m => m.letterboxd_url === winner.letterboxd_url);

        // 3. Calculate rotation to land on winner
        // The pointer is at TOP (-PI/2 or 270 degrees).
        // Each segment is arcSize. Center of segment i is i*arcSize + arcSize/2.

        const arcSize = (2 * Math.PI) / SEGMENT_COUNT;

        // We want the winner's center (winnerAngle) to end up at -PI/2 (Top)
        // currentRotation + winnerAngle = -PI/2 + k*2PI
        // So targetRotation = -PI/2 - winnerAngle + k*2PI

        const winnerAngle = winnerIndex * arcSize + arcSize / 2;

        const fullRotations = 5 * (2 * Math.PI);

        // Calculate destination
        // We subtract PI/2 because canvas 0 is at 3 o'clock, so -PI/2 is 12 o'clock.
        // We subtract winnerAngle to bring that specific segment to 0.
        // We add fullRotations for the spin effect.
        const totalRot = fullRotations - (winnerAngle + Math.PI / 2) - (currentRotation % (2 * Math.PI));

        const startRot = currentRotation;
        const targetRot = startRot + totalRot;

        const startTime = performance.now();

        function animate(time) {
            const elapsed = time - startTime;
            const progress = Math.min(elapsed / SPIN_DURATION, 1);
            const ease = easeOutCubic(progress);

            currentRotation = startRot + (targetRot - startRot) * ease;
            drawWheel();

            if (progress < 1) {
                requestAnimationFrame(animate);
            } else {
                spinBtn.disabled = false;
                showWinnerDetail(winner);
            }
        }

        requestAnimationFrame(animate);

    } catch (error) {
        console.error(error);
        alert("Error spinning");
        spinBtn.disabled = false;
    }
});

function showWinnerDetail(winner) {
    winnerTitle.textContent = winner.title;
    if (winner.poster_url && winner.poster_url !== "null") {
        winnerPoster.src = winner.poster_url;
    } else {
        winnerPoster.src = "https://via.placeholder.com/300x450?text=" + encodeURIComponent(winner.title);
    }
    winnerLink.href = winner.letterboxd_url;
    modal.classList.remove("hidden");
}

closeModal.addEventListener("click", () => {
    modal.classList.add("hidden");
});

window.onclick = (event) => {
    if (event.target == modal) {
        modal.classList.add("hidden");
    }
};

// Initial load check
loadMovies();
