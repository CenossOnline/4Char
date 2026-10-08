const names = [
    {
        name: "iyey",
        score: 94,
        status: "ready",
        style: "weird",
        new: true
    },
    {
        name: "doaf",
        score: 93,
        status: "soon",
        style: "almost-word",
        release: "4 days"
    },
    {
        name: "uwiv",
        score: 91,
        status: "ready",
        style: "cryptic",
        new: true
    },
    {
        name: "oyim",
        score: 90,
        status: "ready",
        style: "almost-word"
    },
    {
        name: "wiyi",
        score: 87,
        status: "ready",
        style: "weird"
    },
    {
        name: "oyih",
        score: 86,
        status: "ready",
        style: "weird"
    },
    {
        name: "ufuv",
        score: 83,
        status: "ready",
        style: "cryptic"
    },
    {
        name: "ocvl",
        score: 82,
        status: "ready",
        style: "cryptic"
    },

    // Demo names for the interface
    {
        name: "qvel",
        score: 89,
        status: "soon",
        style: "cryptic",
        release: "11 days"
    },
    {
        name: "aven",
        score: 88,
        status: "ready",
        style: "pronounceable",
        new: true
    },
    {
        name: "velo",
        score: 85,
        status: "ready",
        style: "pronounceable"
    },
    {
        name: "kova",
        score: 84,
        status: "ready",
        style: "pronounceable"
    }
];


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


function renderNames() {

    const search = searchInput.value.toLowerCase().trim();
    const minimumScore = Number(scoreRange.value);

    let filtered = names.filter(item => {

        // Search
        if (search && !item.name.includes(search)) {
            return false;
        }

        // Status
        if (activeStatus === "ready" && item.status !== "ready") {
            return false;
        }
        // Style
        if (activeStyle !== "all" && item.style !== activeStyle) {
            return false;
        }

        // Score
        if (item.score < minimumScore) {
            return false;
        }

        // Rare letters
        if (!rareLetters.checked && /[qxzj]/i.test(item.name)) {
            return false;
        }

        // Vowel-heavy
        if (vowelsOnly.checked) {
            const vowels = item.name.match(/[aeiou]/g) || [];

            if (vowels.length < 2) {
                return false;
            }
        }

        return true;
    });


    // SORT

    if (sortSelect.value === "score") {

        filtered.sort((a, b) => b.score - a.score);

    } else if (sortSelect.value === "name") {

        filtered.sort((a, b) => a.name.localeCompare(b.name));

    } else if (sortSelect.value === "newest") {

        filtered.sort((a, b) => Number(b.new) - Number(a.new));
    }


    // RESULT COUNT

    resultCount.textContent = filtered.length;


    // EMPTY STATE

    if (filtered.length === 0) {

        grid.innerHTML = "";

        emptyState.classList.remove("hidden");

        return;

    } else {

        emptyState.classList.add("hidden");
    }


    // CARDS

    grid.innerHTML = filtered.map(createCard).join("");
}


function createCard(item) {

    let statusText = "CLAIM READY";
    let statusClass = "ready";
    let releaseText = "";    }


    return `
        <article class="name-card">

            <div class="card-top">

                <div class="card-status">

                    <span class="card-status-dot ${statusClass}">
                    </span>

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

                <span class="release">
                    ${releaseText}
                </span>

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


/* SEARCH */

searchInput.addEventListener("input", renderNames);


/* SORT */

sortSelect.addEventListener("change", renderNames);


/* SCORE */

scoreRange.addEventListener("input", () => {

    scoreValue.textContent = `${scoreRange.value}+`;

    renderNames();
});


/* OTHER FILTERS */

rareLetters.addEventListener("change", renderNames);

vowelsOnly.addEventListener("change", renderNames);


/* ADVANCED FILTER TOGGLE */

toggleFilters.addEventListener("click", () => {

    advancedPanel.classList.toggle("open");

    toggleFilters.classList.toggle("open");
});


/* "/" TO FOCUS SEARCH */

document.addEventListener("keydown", event => {

    if (
        event.key === "/" &&
        document.activeElement !== searchInput
    ) {

        event.preventDefault();

        searchInput.focus();
    }
});


/* INITIAL RENDER */

renderNames();