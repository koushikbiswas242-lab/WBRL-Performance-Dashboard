const pages = {
    dashboard: "dashboardPage",
    master: "masterPage",
    ica: "icaPage",
    tpd: "tpdPage"
};


// =====================================================
// NAVIGATION
// =====================================================

document.querySelectorAll(".nav").forEach(button => {

    button.onclick = () => {

        document
            .querySelectorAll(".nav")
            .forEach(item =>
                item.classList.remove("active")
            );

        button.classList.add("active");

        Object
            .values(pages)
            .forEach(id =>
                document
                    .getElementById(id)
                    .classList.add("hidden")
            );

        document
            .getElementById(
                pages[button.dataset.page]
            )
            .classList.remove("hidden");


        const titles = {

            dashboard:
                "State Performance Dashboard",

            master:
                "Master Data Upload",

            ica:
                "ICA Weekly Report Upload",

            tpd:
                "TPD Weekly Report Upload"

        };


        document
            .getElementById("pageTitle")
            .textContent =
                titles[button.dataset.page];

    };

});


// =====================================================
// RANKING HTML
// =====================================================

function rankHtml(items) {

    if (!items || !items.length) {

        return `
            <p class="empty">
                No data available yet.
            </p>
        `;

    }

    return items.map((item, index) => `

        <div class="row">

            <span class="rank">
                ${index + 1}
            </span>

            <span class="name">
                ${item.name}
            </span>

            <span class="score">
                ${item.score}%
            </span>

        </div>

    `).join("");

}


// =====================================================
// LOAD DISTRICTS
// =====================================================

async function loadDistricts() {

    const districtSelect =
        document.getElementById("districtFilter");

    try {

        const response = await fetch(
            "/api/dashboard/districts"
        );

        const districts =
            await response.json();

        districtSelect.innerHTML =
            `<option value="">
                All Districts
            </option>`;

        districts.forEach(district => {

            const option =
                document.createElement("option");

            option.value = district;

            option.textContent = district;

            districtSelect.appendChild(option);

        });

    }

    catch (error) {

        console.error(
            "District loading error:",
            error
        );

    }

}


// =====================================================
// LOAD BLOCKS
// =====================================================

async function loadBlocks(district) {

    const blockSelect =
        document.getElementById("blockFilter");

    blockSelect.innerHTML =
        `<option value="">
            Select Block
        </option>`;

    if (!district) return;

    try {

        const response = await fetch(
            `/api/dashboard/blocks/${encodeURIComponent(district)}`
        );

        const blocks =
            await response.json();

        blocks.forEach(block => {

            const option =
                document.createElement("option");

            option.value = block;

            option.textContent = block;

            blockSelect.appendChild(option);

        });

    }

    catch (error) {

        console.error(
            "Block loading error:",
            error
        );

    }

}


// =====================================================
// GET CURRENT DASHBOARD API
// =====================================================

function getDashboardURL() {

    const level =
        document.getElementById(
            "dashboardLevel"
        ).value;

    const district =
        document.getElementById(
            "districtFilter"
        ).value;

    const block =
        document.getElementById(
            "blockFilter"
        ).value;


    // STATE
    if (level === "state") {

        return "/api/dashboard/state";

    }


    // DISTRICT
    if (level === "district") {

        if (!district) {

            return "/api/dashboard/state";

        }

        return `/api/dashboard/district/${encodeURIComponent(district)}`;

    }


    // BLOCK
    if (level === "block") {

        if (!district || !block) {

            return null;

        }

        return `/api/dashboard/block/${encodeURIComponent(district)}/${encodeURIComponent(block)}`;

    }


    return "/api/dashboard/state";

}


// =====================================================
// LOAD DASHBOARD
// =====================================================

async function loadDashboard() {

    const status =
        document.getElementById("status");

    const url =
        getDashboardURL();


    if (!url) {

        status.textContent =
            "Please select District and Block.";

        return;

    }


    status.textContent =
        "Refreshing live data...";


    try {

        const response =
            await fetch(url);

        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Dashboard loading error"
            );

        }


        const summary =
            data.summary;


        // KPI DATA

        document
            .getElementById("total")
            .textContent =
                summary.total_aww;


        document
            .getElementById("active")
            .textContent =
                summary.active_aww;


        document
            .getElementById("inactive")
            .textContent =
                summary.inactive_aww;


        document
            .getElementById("gold")
            .textContent =
                summary.gold;


        document
            .getElementById("silver")
            .textContent =
                summary.silver;


        document
            .getElementById("bronze")
            .textContent =
                summary.bronze;


        document
            .getElementById("rate")
            .textContent =
                summary.certification_rate + "%";


        // RANKINGS

        document
            .getElementById("top")
            .innerHTML =
                rankHtml(
                    data.top_supervisors
                );


        document
            .getElementById("bottom")
            .innerHTML =
                rankHtml(
                    data.bottom_supervisors
                );


        document
            .getElementById("blocks")
            .innerHTML =
                rankHtml(
                    data.top_blocks || []
                );


        // SYSTEM INFO

        document
            .getElementById("systemInfo")
            .textContent =
                `${summary.total_aww} AWW records loaded. ` +
                `Live analytics is active.`;


        status.textContent =
            "Live data loaded successfully.";


    }

    catch (error) {

        console.error(error);

        status.textContent =
            "Could not load live dashboard data.";

    }

}


// =====================================================
// FILTER LEVEL CHANGE
// =====================================================

document
    .getElementById("dashboardLevel")
    .addEventListener(
        "change",
        async function () {

            const level =
                this.value;

            const districtBox =
                document.getElementById(
                    "districtFilterBox"
                );

            const blockBox =
                document.getElementById(
                    "blockFilterBox"
                );


            // STATE
            if (level === "state") {

                districtBox.classList.add("hidden");

                blockBox.classList.add("hidden");

                document
                    .getElementById("pageTitle")
                    .textContent =
                        "State Performance Dashboard";

            }


            // DISTRICT
            else if (level === "district") {

                districtBox.classList.remove("hidden");

                blockBox.classList.add("hidden");

                document
                    .getElementById("pageTitle")
                    .textContent =
                        "District Performance Dashboard";

            }


            // BLOCK
            else {

                districtBox.classList.remove("hidden");

                blockBox.classList.remove("hidden");

                document
                    .getElementById("pageTitle")
                    .textContent =
                        "Block Performance Dashboard";

            }


            loadDashboard();

        }
    );


// =====================================================
// DISTRICT CHANGE
// =====================================================

document
    .getElementById("districtFilter")
    .addEventListener(
        "change",
        async function () {

            const district =
                this.value;

            await loadBlocks(district);

            loadDashboard();

        }
    );


// =====================================================
// BLOCK CHANGE
// =====================================================

document
    .getElementById("blockFilter")
    .addEventListener(
        "change",
        loadDashboard
    );


// =====================================================
// MESSAGE
// =====================================================

function showMessage(
    element,
    text,
    success = true
) {

    element.className =
        "message " +
        (
            success
                ? "success"
                : "error"
        );

    element.textContent = text;

}


// =====================================================
// MASTER UPLOAD
// =====================================================

document
    .getElementById("masterForm")
    .addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();

            const message =
                document.getElementById(
                    "masterMsg"
                );

            const formData =
                new FormData(this);


            showMessage(
                message,
                "Uploading master data...",
                true
            );


            try {

                const response =
                    await fetch(
                        "/api/master/upload",
                        {
                            method: "POST",
                            body: formData
                        }
                    );

                const data =
                    await response.json();


                if (!response.ok) {

                    throw new Error(
                        data.detail ||
                        "Upload failed"
                    );

                }


                showMessage(

                    message,

                    `${data.message}
                    New: ${data.created},
                    Updated: ${data.updated},
                    Skipped: ${data.skipped}`,

                    true

                );


                await loadDistricts();

                loadDashboard();

                this.reset();


            }

            catch (error) {

                showMessage(
                    message,
                    error.message,
                    false
                );

            }

        }
    );


// =====================================================
// ICA / TPD UPLOAD
// =====================================================

document
    .querySelectorAll(".reportForm")
    .forEach(form => {

        form.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();

                const message =
                    form
                        .parentElement
                        .querySelector(".message");

                const formData =
                    new FormData(form);


                formData.append(
                    "report_type",
                    form.dataset.type
                );


                try {

                    const response =
                        await fetch(
                            "/api/report/upload",
                            {
                                method: "POST",
                                body: formData
                            }
                        );


                    const data =
                        await response.json();


                    if (!response.ok) {

                        throw new Error(
                            data.detail ||
                            "Upload failed"
                        );

                    }


                    showMessage(

                        message,

                        `${data.message}
                        Processed: ${data.processed},
                        Skipped: ${data.skipped}`,

                        true

                    );


                    loadDashboard();

                    form.reset();


                }

                catch (error) {

                    showMessage(
                        message,
                        error.message,
                        false
                    );

                }

            }
        );

    );


// =====================================================
// INITIAL LOAD
// =====================================================

document.addEventListener(
    "DOMContentLoaded",
    async () => {

        await loadDistricts();

        loadDashboard();

    }
);
