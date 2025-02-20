document.addEventListener("DOMContentLoaded", () => {
    const addressInput = document.getElementById("address");
    const suggestionList = document.getElementById("address-suggestions");
    const latitudeInput = document.getElementById("latitude");
    const longitudeInput = document.getElementById("longitude");
    const fetchDataButton = document.getElementById("fetch-data");
    const fileInput = document.getElementById("csv-upload");
    const uploadButton = document.getElementById("upload-csv");
    const compareButton = document.getElementById("compare");
    const ctx = document.getElementById("solarChart").getContext("2d");

    let solarChart;
    let solarData = null;
    let csvData = null;

    
    function disableButtons(){
        fetchDataButton.disabled = true;
        compareButton.disabled = true;
    }


    // Initially disable fetchDataButton and compareButton
    disableButtons();

    function checkButtons() {
        // Enable fetchDataButton only if CSV is uploaded
        fetchDataButton.disabled = !csvData;
        // Enable compareButton only if both CSV and solar data are available
        compareButton.disabled = !(csvData && solarData);
    }

    function fetchSuggestions(query) {
        fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=json&addressdetails=1`)
            .then(response => response.json())
            .then(data => {
                if (data.length === 0) return;
                suggestionList.innerHTML = "";
                data.slice(0, 3).forEach(item => {
                    const li = document.createElement("li");
                    li.textContent = item.display_name;
                    li.onclick = () => selectAddress(item);
                    suggestionList.appendChild(li);
                });
                suggestionList.style.display = "block";
            });
    }

    function selectAddress(item) {
        addressInput.value = item.display_name;
        latitudeInput.value = item.lat;
        longitudeInput.value = item.lon;
        suggestionList.innerHTML = "";
    }

    addressInput.addEventListener("input", () => {
        clearTimeout(this.debounceTimeout);
        if (addressInput.value.length >= 10) {
            this.debounceTimeout = setTimeout(() => fetchSuggestions(addressInput.value), 1000);
        } else {
            suggestionList.innerHTML = "";
            suggestionList.style.display = "none";
        }
    });

    fetchDataButton.addEventListener("click", () => {
        if (!csvData) {
            alert("Please upload a CSV file first.");
            return;
        }

        const lat = latitudeInput.value;
        const lon = longitudeInput.value;
        if (!lat || !lon) {
            alert("Please enter a valid latitude and longitude.");
            return;
        }

        fetch(`/get_solar_data?lat=${lat}&lon=${lon}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error fetching solar data: " + data.error);
                    return;
                }
                solarData = data.solar_data;
                updateChart();
                checkButtons();
            });
    });

    document.getElementById('csv-upload').addEventListener('change', function() {
        const fileName = this.files[0] ? this.files[0].name : "Choose CSV File";
        document.getElementById('file-name').textContent = fileName;
    });
    

    uploadButton.addEventListener("click", () => {
        const file = fileInput.files[0];
        if (!file) {
            alert("Please select a CSV file.");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        fetch("/upload_csv", { method: "POST", body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error uploading CSV: " + data.error);
                    return;
                }
                csvData = data.csv_data;
                updateChart();
                checkButtons();

                // Reset recommendation section
                document.getElementById("expected-power").textContent = "Expected Power: --";
                document.getElementById("true-power").textContent = "Actual Power: --";
                document.getElementById("efficiency").textContent = "Efficiency: --";
                document.getElementById("recommendation").textContent = "Recommendation: --";

            })
            .catch(error => alert("Error uploading file: " + error));
    });




    function updateChart() {
        let labelsSet = new Set();
        let solarValuesMap = new Map();
        let csvValuesMap = new Map();

        if (solarData) {
            solarData.forEach(entry => {
                // let timeLabel = `${entry.X}:00`;
                let timeLabel = `${entry.X}`;
                labelsSet.add(timeLabel);
                solarValuesMap.set(timeLabel, entry["Eficiencia Esperada"]);
            });
        }

        if (csvData) {
            csvData.forEach(entry => {
                // let timeLabel = `${entry.X}:00`;
                let timeLabel = `${entry.X}`;
                labelsSet.add(timeLabel);
                csvValuesMap.set(timeLabel, entry["Eficiencia Real"]);
            });
        }

        let labels = Array.from(labelsSet).sort((a, b) => parseInt(a) - parseInt(b));
        let solarValues = labels.map(label => solarValuesMap.get(label) || null);
        let csvValues = labels.map(label => csvValuesMap.get(label) || null);

        if (solarChart) {
            solarChart.destroy();
        }

        solarChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Expected Efficiency",
                        data: solarValues,
                        borderColor: "#00BFFF",
                        backgroundColor: "rgba(0, 191, 255, 0.5)",
                        fill: true,
                    },
                    {
                        label: "Actual Efficiency",
                        data: csvValues,
                        borderColor: "#FF4500",
                        backgroundColor: "rgba(255, 69, 0, 0.5)",
                        fill: true,
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: { title: { display: true, text: "Month-Day-Hour" } },
                    y: { title: { display: true, text: "Efficiency (%)" } }
                }
            }
        });
    }

    compareButton.addEventListener("click", () => {
        if (!csvData || !solarData) {
            alert("Please upload CSV and fetch solar data before comparing.");
            return;
        }

        fetch("/compare_data", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ solar_data: solarData, csv_data: csvData })
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert("Error comparing data: " + data.error);
                return;
            }

            disableButtons();
            
            document.getElementById("expected-power").textContent = `Expected Power: ${data.expected_power}%`;
            document.getElementById("true-power").textContent = `Actual Power: ${data.true_power}%`;
            document.getElementById("efficiency").textContent = `Efficiency: ${data.efficiency}%`;
            document.getElementById("recommendation").textContent = `Recommendation: ${data.recommendation}`;
        })
        .catch(error => alert("Error fetching comparison results: " + error));
    });

});
