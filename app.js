let names = [];

const HIDDEN_NAMES = new Set([
    "afus",
    "ukig",
    "oyim",
    "reve"
]);

let activeStatus = "all";
let activeStyle = "all";

const grid = document.getElementById("nameGrid");
const emptyState = document.getElementById("emptyState");
const resultCount = document.getElementById("resultCount");

const searchInput = document.getElementById("searchInput");
const sortSelect = document.getElementById("sortSelect");

const scoreRange = document.getElementById("scoreRange");
const scoreValue = document.getElementById("scoreValue");

const advancedPanel = document.getElementById("advancedPanel");
const toggleFilters = document.getElementById("toggleFilters");

const rareLetters = document.getElementById("rareLetters");
const vowelsOnly = document.getElementById("vowelsOnly");

const lastScan = document.querySelector(".last-scan strong");


function getScore(name) {
    let score = 70;

    if (new Set(name).size === 4) score += 8;
    if (/[aeiou]/.test(name)) score += 4;
    if (/[qxzj]/.test(name)) score += 6;

    const pattern = [...name]
        .map(letter => /[aeiou]/.test(letter) ? "V" : "C")
        .join("");

    if (["CVCV", "VCVC", "CVVC"].includes(pattern)) score += 7;
    if (/^[a-z]{4}$/.test(name)) score += 2;

    return Math.min(score, 99);
}


function getStyle(name) {
    const vowels = (name.match(/[aeiou]/g) || []).length;
    const pattern = [...name]
        .map(letter => /[aeiou]/.test(letter) ? "V" : "C")
        .join("");

    if (["CVCV", "VCVC", "CVVC"].includes(pattern) && vowels >= 2) {
        return "almost-word";
    }

    if (vowels >= 2) {
        return "weird";
    }

    return "cryptic";
}


function prepareNames(rawNames) {
    return rawNames
        .filter(name => typeof name === "string" && /^[a-z]{4}$/.test(name))
        .map(name => {
            const normalized = name.toLowerCase();

            return {
                name: normalized,
                score: getScore(normalized),
                status: "ready",
                style: getStyle(normalized)
            };
        });
}


async function loadNames() {
    try {
        // Cache-bust so the browser picks up the latest scanner database.
        const response = await fetch(`data/names.json?t=${Date.now()}`, {
            cache: "no-store"
        });

        if (!response.ok) {
            throw new Error(`Database returned HTTP ${response.status}`);
        }

        const data = await response.json();

        const publicNames = (Array.isArray(data) ? data : data.names || [])
            .filter(name => !HIDDEN_NAMES.has(String(name).toLowerCase()));

        names = prepareNames(publicNames);

        if (data.updated_at && lastScan) {
            const date = new Date(data.updated_at * 1000);
            lastScan.textContent = `LAST SCAN · ${date.toLocaleString([], {
                dateStyle: "medium",
                timeStyle: "short"
            })}`;
        }

        renderNames();

    } catch (error) {
        console.error("Could not load 4CHAR database:", error);
        names = [];
        renderNames();
    }
}


function renderNames() {
    const search = searchInput.value.toLowerCase().trim();
    const minimumScore = Number(scoreRange.value);

    let filtered = names.filter(item => {

        if (search && !item.name.includes(search)) {
            return false;
        }

        if (activeStatus === "ready" && item.status !== "ready") {
            return false;
        }

        if (activeStyle !== "all" && item.style !== activeStyle) {
            return false;
        }

        if (item.score < minimumScore) {
            return false;
        }

        if (!rareLetters.checked && /[qxzj]/i.test(item.name)) {
            return false;
        }

        if (vowelsOnly.checked) {
            const vowels = item.name.match(/[aeiou]/g) || [];

            if (vowels.length < 2) {
                return false;
            }
        }

        return true;
    });


    if (sortSelect.value === "score") {
        filtered.sort((a, b) => b.score - a.score);

    } else if (sortSelect.value === "name") {
        filtered.sort((a, b) => a.name.localeCompare(b.name));
    }


    resultCount.textContent = filtered.length;


    if (filtered.length === 0) {
        grid.innerHTML = "";
        emptyState.classList.remove("hidden");
        return;
    }

    emptyState.classList.add("hidden");
    grid.innerHTML = filtered.map(createCard).join("");
}


function createCard(item) {
    const statusText = "CLAIM READY";
    const statusClass = "ready";

    return `
        <article class="name-card">

            <div class="card-top">

                <div class="card-status">

                    <span class="card-status-dot ${statusClass}"></span>

                    ${statusText}

                </div>

                <span class="score">
                    ${item.score}
                </span>

            </div>


            <div class="name">
                ${item.name}
            </div>


            <div class="card-bottom">

                <span class="style">
                    ${item.style.replace("-", " ")}
                </span>

                <span class="release"></span>

            </div>

        </article>
    `;
}


/* STATUS FILTERS */

document.querySelectorAll(".filter").forEach(button => {

    button.addEventListener("click", () => {

        document
            .querySelectorAll(".filter")
            .forEach(btn => btn.classList.remove("active"));

        button.classList.add("active");

        activeStatus = button.dataset.status;

        renderNames();
    });
});


/* STYLE FILTERS */

document.querySelectorAll(".chip").forEach(button => {

    button.addEventListener("click", () => {

        document
            .querySelectorAll(".chip")
            .forEach(btn => btn.classList.remove("active"));

        button.classList.add("active");

        activeStyle = button.dataset.style;

        renderNames();
    });
});


searchInput.addEventListener("input", renderNames);

sortSelect.addEventListener("change", renderNames);


scoreRange.addEventListener("input", () => {

    scoreValue.textContent = `${scoreRange.value}+`;

    renderNames();
});


rareLetters.addEventListener("change", renderNames);

vowelsOnly.addEventListener("change", renderNames);


toggleFilters.addEventListener("click", () => {

    advancedPanel.classList.toggle("open");
    toggleFilters.classList.toggle("open");
});


document.addEventListener("keydown", event => {

    if (
        event.key === "/" &&
        document.activeElement !== searchInput
    ) {

        event.preventDefault();
        searchInput.focus();
    }
});


loadNames();

// Refresh the public list periodically without requiring a page reload.
setInterval(loadNames, 60 * 1000);
