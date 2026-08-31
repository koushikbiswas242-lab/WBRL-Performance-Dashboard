// =====================================================
// WBRL PERFORMANCE DASHBOARD - APP.JS
// =====================================================

document.addEventListener("DOMContentLoaded", () => {

    // =====================================================
    // PAGE CONFIGURATION
    // =====================================================

    const pages = {
        dashboard: "dashboardPage",
        master: "masterPage",
        ica: "icaPage",
        tpd: "tpdPage"
    };

    const titles = {
        dashboard: "State Performance Dashboard",
        master: "Master Data Upload",
        ica: "ICA Weekly Report Upload",
        tpd: "TPD Weekly Report Upload"
    };


    // =====================================================
    // SAFE ELEMENT GETTER
    // =====================================================

    function getElement(id) {
        return document.getElementById(id);
    }


    // =====================================================
    // NAVIGATION
    // =====================================================

    const navButtons = document.querySelectorAll(".nav");

    navButtons.forEach(button => {

        button.addEventListener("click", () => {

            const pageName = button.dataset.page;

            if (!pageName || !pages[pageName]) {
                console.error("Invalid page:", pageName);
                return;
            }


            // Remove active class
            navButtons.forEach(item => {
                item.classList.remove("active");
            });


            // Add active class
            button.classList.add("active");


            // Hide all pages
            Object.values(pages).forEach(pageId => {

                const page = getElement(pageId);

                if (page) {
                    page.classList.add("hidden");
                }

            });


            // Show selected page
            const selectedPage =
                getElement(pages[pageName]);

            if (selectedPage) {
                selectedPage.classList.remove("hidden");
            }


            // Change page title
            const pageTitle =
                getElement("pageTitle");

            if (pageTitle) {
                pageTitle.textContent =
                    titles[pageName];
            }

        });

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
                    ${item.name || "Unknown"}
                </span>

                <span class="score">
                    ${item.score || 0}%
                </span>

            </div>

        `).join("");

    }


    // =====================================================
    // LOAD DISTRICTS
    // =====================================================

    async function loadDistricts() {

        const districtSelect =
            getElement("districtFilter");

        if (!districtSelect) return;


        try {

            const response =
                await fetch("/api/dashboard/districts");


            if (!response.ok) {
                throw new Error("Could not load districts");
            }


            const districts =
                await response.json();


            districtSelect.innerHTML =
                `<option value="">All Districts</option>`;


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
            getElement("blockFilter");

        if (!blockSelect) return;


        blockSelect.innerHTML =
            `<option value="">Select Block</option>`;


        if (!district) return;


        try {

            const response =
                await fetch(
                    `/api/dashboard/blocks/${encodeURIComponent(district)}`
                );


            if (!response.ok) {
                throw new Error("Could not load blocks");
            }


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
    // GET DASHBOARD API URL
    // =====================================================

    function getDashboardURL() {

        const levelElement =
            getElement("dashboardLevel");

        const districtElement =
            getElement("districtFilter");

        const blockElement =
            getElement("blockFilter");


        if (!levelElement) {
            return "/api/dashboard/state";
        }


        const level =
            levelElement.value;

        const district =
            districtElement
                ? districtElement.value
                : "";

        const block =
            blockElement
                ? blockElement.value
                : "";


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
            getElement("status");

        const url =
            getDashboardURL();


        if (!url) {

            if (status) {
                status.textContent =
                    "Please select District and Block.";
            }

            return;

        }


        if (status) {
            status.textContent =
                "Refreshing live data...";
        }


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
                data.summary || {};


            // =====================================================
            // KPI DATA
            // =====================================================

            const kpis = {

                total: summary.total_aww || 0,

                active: summary.active_aww || 0,

                inactive: summary.inactive_aww || 0,

                gold: summary.gold || 0,

                silver: summary.silver || 0,

                bronze: summary.bronze || 0

            };


            Object.entries(kpis).forEach(
                ([id, value]) => {

                    const element =
                        getElement(id);

                    if (element) {
                        element.textContent = value;
                    }

                }
            );


            const rate =
                getElement("rate");

            if (rate) {

                rate.textContent =
                    (summary.certification_rate || 0)
                    + "%";

            }


            // =====================================================
            // RANKINGS
            // =====================================================

            const top =
                getElement("top");

            if (top) {

                top.innerHTML =
                    rankHtml(
                        data.top_supervisors || []
                    );

            }


            const bottom =
                getElement("bottom");

            if (bottom) {

                bottom.innerHTML =
                    rankHtml(
                        data.bottom_supervisors || []
                    );

            }


            const blocks =
                getElement("blocks");

            if (blocks) {

                blocks.innerHTML =
                    rankHtml(
                        data.top_blocks || []
                    );

            }


            // =====================================================
            // SYSTEM INFO
            // =====================================================

            const systemInfo =
                getElement("systemInfo");

            if (systemInfo) {

                systemInfo.textContent =
                    `${summary.total_aww || 0} AWW records loaded. Live analytics is active.`;

            }


            if (status) {

                status.textContent =
                    "Live data loaded successfully.";

            }

        }

        catch (error) {

            console.error(
                "Dashboard error:",
                error
            );


            if (status) {

                status.textContent =
                    "Could not load live dashboard data.";

            }

        }

    }


    // =====================================================
    // DASHBOARD LEVEL CHANGE
    // =====================================================

    const dashboardLevel =
        getElement("dashboardLevel");

    if (dashboardLevel) {

        dashboardLevel.addEventListener(
            "change",
            () => {

                const level =
                    dashboardLevel.value;

                const districtBox =
                    getElement("districtFilterBox");

                const blockBox =
                    getElement("blockFilterBox");

                const pageTitle =
                    getElement("pageTitle");


                // STATE
                if (level === "state") {

                    if (districtBox) {
                        districtBox.classList.add("hidden");
                    }

                    if (blockBox) {
                        blockBox.classList.add("hidden");
                    }

                    if (pageTitle) {
                        pageTitle.textContent =
                            "State Performance Dashboard";
                    }

                }


                // DISTRICT
                else if (level === "district") {

                    if (districtBox) {
                        districtBox.classList.remove("hidden");
                    }

                    if (blockBox) {
                        blockBox.classList.add("hidden");
                    }

                    if (pageTitle) {
                        pageTitle.textContent =
                            "District Performance Dashboard";
                    }

                }


                // BLOCK
                else if (level === "block") {

                    if (districtBox) {
                        districtBox.classList.remove("hidden");
                    }

                    if (blockBox) {
                        blockBox.classList.remove("hidden");
                    }

                    if (pageTitle) {
                        pageTitle.textContent =
                            "Block Performance Dashboard";
                    }

                }


                loadDashboard();

            }
        );

    }


    // =====================================================
    // DISTRICT CHANGE
    // =====================================================

    const districtFilter =
        getElement("districtFilter");

    if (districtFilter) {

        districtFilter.addEventListener(
            "change",
            async function () {

                await loadBlocks(this.value);

                loadDashboard();

            }
        );

    }


    // =====================================================
    // BLOCK CHANGE
    // =====================================================

    const blockFilter =
        getElement("blockFilter");

    if (blockFilter) {

        blockFilter.addEventListener(
            "change",
            loadDashboard
        );

    }


    // =====================================================
    // SHOW MESSAGE
    // =====================================================

    function showMessage(
        element,
        text,
        success = true
    ) {

        if (!element) return;


        element.className =
            "message " +
            (success ? "success" : "error");

        element.textContent =
            text;

    }


    // =====================================================
    // MASTER DATA UPLOAD
    // =====================================================

    const masterForm =
        getElement("masterForm");

    if (masterForm) {

        masterForm.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();


                const message =
                    getElement("masterMsg");

                const formData =
                    new FormData(this);


                showMessage(
                    message,
                    "Uploading master data..."
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
New: ${data.created || 0}
Updated: ${data.updated || 0}
Skipped: ${data.skipped || 0}`,

                        true

                    );


                    await loadDistricts();

                    await loadDashboard();

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

    }


    // =====================================================
    // ICA / TPD REPORT UPLOAD
    // =====================================================

    const reportForms =
        document.querySelectorAll(".reportForm");


    reportForms.forEach(form => {

        form.addEventListener(
            "submit",
            async function (event) {

                event.preventDefault();


                const message =
                    form.parentElement
                        .querySelector(".message");


                const formData =
                    new FormData(form);


                formData.append(
                    "report_type",
                    form.dataset.type
                );


                showMessage(
                    message,
                    "Uploading report..."
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
Processed: ${data.processed || 0}
Skipped: ${data.skipped || 0}`,

                        true

                    );


                    await loadDashboard();

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

    });


    // =====================================================
    // REFRESH BUTTON
    // =====================================================

    const refreshButton =
        getElement("refreshBtn");

    if (refreshButton) {

        refreshButton.addEventListener(
            "click",
            loadDashboard
        );

    }


    // =====================================================
    // INITIAL LOAD
    // =====================================================

    loadDistricts();
    loadDashboard();

});
