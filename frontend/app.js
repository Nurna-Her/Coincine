const API_URL = "/api"; // The backend serves this page, so the API is same-origin

const usernameInput = document.getElementById("username");
const syncBtn = document.getElementById("sync-btn");
const clearBtn = document.getElementById("clear-btn");
const allDoneBtn = document.getElementById("all-done-btn");
const spinBtn = document.getElementById("spin-btn");
const movieDisplay = document.getElementById("movie-display");
const modal = document.getElementById("result-modal");
const closeModal = document.querySelector(".close");
const usersListDiv = document.getElementById("users-list");
const mixBtn = document.getElementById("mix-btn");
const matchBtn = document.getElementById("match-btn");
const maxMoviesInput = document.getElementById("max-movies-input");
const selectModeBtn = document.getElementById("select-mode-btn");
const eliminateModeBtn = document.getElementById("eliminate-mode-btn");
const reloadBtn = document.getElementById("reload-btn");

// Winner elements
const winnerTitle = document.getElementById("winner-title");
const winnerLink = document.getElementById("winner-link");

let movies = [];
let sessionUsers = [];  // Array of {username, profile_picture, frequent}
let currentMode = "mix"; // Default watchlist mode
let interactionMode = "select"; // 'select' or 'eliminate'
let isSpinning = false;
let reloadPending = false; // A roulette reload was requested mid-spin
let loadRequestId = 0; // Lets loadMovies drop responses that arrive out of order

// On load, fetch saved users or whatever is needed
window.addEventListener("DOMContentLoaded", async () => {
    await loadSavedUsers();
});

async function loadSavedUsers() {
    try {
        const response = await fetch(`${API_URL}/users/saved`);
        if (response.ok) {
            const savedUsers = await response.json();
            // Automatically add saved users to current session for convenience? 
            // Or just show them in a "Frequent" section?
            // The user said: "Si al añadir un usuario este ya existe en la base de datos, se añade directamente (a la lista de la sesión)".
            // Let's just update the display logic to show who is in session.
        }
    } catch (error) {
        console.error("Error loading saved users", error);
    }
}

syncBtn.addEventListener("click", async () => {
    const username = usernameInput.value.trim();
    if (!username) return alert("Please enter a username");

    syncBtn.textContent = "Adding...";
    syncBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/add_user?username=${encodeURIComponent(username)}`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            sessionUsers = data.users;
            updateUsersDisplay();
            usernameInput.value = ""; // Clear input
            allDoneBtn.disabled = false;
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
            sessionUsers = [];
            updateUsersDisplay();
            allDoneBtn.disabled = true;
            resetWheel();
            alert(data.message);
        }
    } catch (error) {
        console.error(error);
        alert("Failed to clear");
    }
});

allDoneBtn.addEventListener("click", async () => {
    allDoneBtn.textContent = "Syncing...";
    allDoneBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/sync_all`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            alert(data.message);
            await loadMovies();
            allDoneBtn.textContent = "Synced!";
        } else {
            alert("Error: " + data.detail);
            allDoneBtn.textContent = "Sync Up!";
            allDoneBtn.disabled = false;
        }
    } catch (error) {
        console.error(error);
        alert("Failed to sync");
        allDoneBtn.textContent = "Sync Up!";
        allDoneBtn.disabled = false;
    }
});

// Watchlist Modes
mixBtn.addEventListener("click", () => setMode("mix"));
matchBtn.addEventListener("click", () => setMode("match"));
maxMoviesInput.addEventListener("change", () => loadMovies());

function setMode(mode) {
    if (currentMode === mode) return;
    currentMode = mode;

    // UI Toggle
    mixBtn.classList.toggle("active", mode === "mix");
    matchBtn.classList.toggle("active", mode === "match");

    loadMovies(); // Automatically update roulette
}

// Interaction Modes
selectModeBtn.addEventListener("click", () => setInteractionMode("select"));
eliminateModeBtn.addEventListener("click", () => setInteractionMode("eliminate"));

function setInteractionMode(mode) {
    if (interactionMode === mode) return;
    interactionMode = mode;

    // UI Toggle
    selectModeBtn.classList.toggle("active", mode === "select");
    eliminateModeBtn.classList.toggle("active", mode === "eliminate");

    // Reset movies if we switch modes? 
    // Usually better to keep current pool unless user wants a fresh start.
    // For now, just change the behavior of the next spin.
}

// Reload logic
reloadBtn.addEventListener("click", () => {
    loadMovies();
});

function mix_watchlists() {
    console.log("Mode: Mix watchlists - Placeholder");
    // Placeholder logic for mixing (current default behavior)
    loadMovies(); // Automatically update roulette
}

function match_watchlists() {
    console.log("Mode: Match watchlists - Placeholder");
    // Placeholder logic for matching (pass for now)
    loadMovies(); // Automatically update roulette
}

async function removeUser(username) {
    try {
        const response = await fetch(`${API_URL}/remove?username=${encodeURIComponent(username)}`, {
            method: "POST"
        });
        const data = await response.json();

        if (response.ok) {
            sessionUsers = data.users;
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

async function toggleSaveUser(username, isSaved) {
    const method = isSaved ? "DELETE" : "POST";
    try {
        const response = await fetch(`${API_URL}/users/${encodeURIComponent(username)}/save_user`, {
            method: method
        });
        if (response.ok) {
            // Update local state and redraw
            const user = sessionUsers.find(u => u.username === username);
            if (user) user.frequent = !isSaved;
            updateUsersDisplay();
        }
    } catch (error) {
        console.error(error);
    }
}

async function refreshUser(username, btn) {
    const originalText = btn.textContent;
    btn.textContent = "...";
    btn.disabled = true;
    try {
        const response = await fetch(`${API_URL}/users/${encodeURIComponent(username)}/update_user`, {
            method: "POST"
        });
        const data = await response.json();
        if (response.ok) {
            alert(data.message);
            await loadMovies();
        } else {
            alert("Error: " + data.detail);
        }
    } catch (error) {
        console.error(error);
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Small DOM helper: user data is only ever set through properties/textContent, never parsed as HTML
function createElement(tag, className, props = {}) {
    const elem = document.createElement(tag);
    if (className) elem.className = className;
    Object.assign(elem, props);
    return elem;
}

function updateUsersDisplay() {
    usersListDiv.replaceChildren();

    if (sessionUsers.length === 0) {
        const emptyMsg = createElement("span", "", { textContent: "No users added" });
        emptyMsg.style.color = "var(--text-color)";
        emptyMsg.style.fontSize = "0.9rem";
        usersListDiv.append(emptyMsg);
        return;
    }

    sessionUsers.forEach(user => {
        const frequentClass = user.frequent ? "user-avatar frequent" : "user-avatar";
        let avatar;
        if (user.profile_picture) {
            avatar = createElement("img", frequentClass, { src: user.profile_picture, alt: user.username });
        } else {
            avatar = createElement("div", frequentClass);
            avatar.style.backgroundColor = "var(--accent-green)";
        }

        const saveBtn = createElement("button", "action-btn save-btn", {
            title: user.frequent ? "Unsave User" : "Save User",
            textContent: user.frequent ? "★" : "☆"
        });
        saveBtn.addEventListener("click", () => toggleSaveUser(user.username, user.frequent));

        const refreshBtn = createElement("button", "action-btn refresh-btn", { title: "Refresh Watchlist", textContent: "↻" });
        refreshBtn.addEventListener("click", () => refreshUser(user.username, refreshBtn));

        const removeBtn = createElement("button", "remove-user-btn", { title: "Remove from session", textContent: "×" });
        removeBtn.addEventListener("click", () => removeUser(user.username));

        const actions = createElement("div", "user-actions");
        actions.append(saveBtn, refreshBtn);

        const details = createElement("div", "user-details");
        details.append(createElement("span", "username", { textContent: user.username }), actions);

        const info = createElement("div", "user-info");
        info.append(avatar, details);

        const item = createElement("div", "user-item");
        item.append(info, removeBtn);
        usersListDiv.append(item);
    });
}

function getMaxMovies() {
    // Clamp to the input's own bounds: 0 or negative limits would empty or break the roulette
    const min = Number(maxMoviesInput.min);
    const max = Number(maxMoviesInput.max);
    const value = parseInt(maxMoviesInput.value, 10);
    const clamped = Number.isNaN(value) ? 20 : Math.min(Math.max(value, min), max);
    maxMoviesInput.value = clamped;
    return clamped;
}

function resetWheel() {
    movies = [];
    segments = [];
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    spinBtn.disabled = true;
}

async function loadMovies() {
    if (isSpinning) {
        // Swapping the pool mid-spin would move the winner's segment: reload once the wheel stops
        reloadPending = true;
        return;
    }

    const requestId = ++loadRequestId;
    const maxMovies = getMaxMovies();
    try {
        const response = await fetch(`${API_URL}/roulette?mode=${currentMode}&max_movies=${maxMovies}`);
        const data = await response.json();

        // A newer request was made, or a spin started, while this one was in flight
        if (requestId !== loadRequestId) return;
        if (isSpinning) {
            reloadPending = true;
            return;
        }

        if (!response.ok || data.length === 0) {
            // No users left or no movies match: never keep a stale pool around
            resetWheel();
            return;
        }

        movies = data;
        spinBtn.disabled = false;
        // Initial draw with whatever is returned
        segments = movies;
        drawWheel();
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
const colors = [
    "#00e054", // Green
    "#ff8000", // Orange
    "#40bcf4", // Blue
    "#7b3fe4", // Purple
    "#e53935", // Red
    "#ffd200", // Yellow
    "#ff3d81"  // Pink
];

function drawWheel() {
    if (segments.length === 0) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        return;
    }

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
        ctx.fillText((movie.title || "").substring(0, 20), radius - 20, 10);
        ctx.restore();
    });
}

function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
}

function finishSpin() {
    isSpinning = false;
    spinBtn.disabled = movies.length === 0;
    if (reloadPending) {
        reloadPending = false;
        loadMovies();
    }
}

spinBtn.addEventListener("click", async () => {
    if (isSpinning) return;
    if (movies.length === 0) return alert("Sync watchlist first!");

    if (interactionMode === "eliminate" && movies.length === 1) {
        // Nothing left to eliminate: the last movie standing is the winner
        return showWinnerDetail(movies[0]);
    }

    isSpinning = true;
    spinBtn.disabled = true;

    try {
        let winner;
        if (interactionMode === "select") {
            // 1. Get official winner from backend
            const response = await fetch(`${API_URL}/spin`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail);
            winner = data;
        } else {
            // Elimination mode: Pick from local array to stay in sync with removals
            winner = movies[Math.floor(Math.random() * movies.length)];
        }

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

        const arcSize = (2 * Math.PI) / segments.length;

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
                handleSpinResult(winner);
                finishSpin();
            }
        }

        requestAnimationFrame(animate);

    } catch (error) {
        console.error(error);
        alert("Error spinning" + (error.message ? `: ${error.message}` : ""));
        finishSpin();
    }
});

function handleSpinResult(winner) {
    if (interactionMode === "select") {
        showWinnerDetail(winner);
    } else {
        // Elimination mode
        // 1. Remove from current movies list
        movies = movies.filter(m => m.letterboxd_url !== winner.letterboxd_url);
        console.log("Eliminated:", winner.title);

        // Reprepare segments (next window) and redraw
        // Shuffle or just pick the next 10
        segments = movies.slice(0, Math.min(movies.length, SEGMENT_COUNT));
        segments.sort(() => 0.5 - Math.random());
        drawWheel();

        if (movies.length === 1) {
            // Only one left! This is the actual winner
            showWinnerDetail(movies[0]);
        }
    }
}

function showWinnerDetail(winner) {
    winnerTitle.textContent = winner.title;
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

