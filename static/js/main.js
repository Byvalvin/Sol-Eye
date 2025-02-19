document.addEventListener("DOMContentLoaded", () => {
    // Get references to input fields and result areas
    const addressInput = document.getElementById("address");
    const suggestionList = document.getElementById("address-suggestions");
    const latitudeInput = document.getElementById("latitude");
    const longitudeInput = document.getElementById("longitude");
    const expectedPowerOutput = document.getElementById("expected-power");

    const manualBtn = document.getElementById("manual-btn");
    const csvBtn = document.getElementById("csv-btn");
    const manualInputSection = document.getElementById("manual-input");
    const csvInputSection = document.getElementById("csv-input");

    const currentInput = document.getElementById("current");
    const voltageInput = document.getElementById("voltage");
    const powerInput = document.getElementById("power");
    const csvInput = document.getElementById("csv-upload");
    const truePowerOutput = document.getElementById("true-power");

    const efficiencyOutput = document.getElementById("efficiency");
    const recommendationOutput = document.getElementById("recommendation");
    const calculateButton = document.getElementById("calculate");

    // Fetch address suggestions from OpenStreetMap API
    let debounceTimeout;

    function fetchSuggestions(query) {
        fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=json&addressdetails=1`)
            .then(response => response.json())
            .then(data => {
                suggestionList.innerHTML = "";
                if (data.length === 0) {
                    suggestionList.style.display = "none";
                    return;
                }
                data.forEach(item => {
                    const li = document.createElement("li");
                    li.textContent = item.display_name;
                    li.onclick = () => {
                        addressInput.value = item.display_name;
                        latitudeInput.value = item.lat;
                        longitudeInput.value = item.lon;
                        suggestionList.innerHTML = "";
                    };
                    suggestionList.appendChild(li);
                });
                suggestionList.style.display = "block";
            });
    }

    addressInput.addEventListener("input", () => {
        clearTimeout(debounceTimeout);
        const address = addressInput.value;
        if (address.length > 3) {
            debounceTimeout = setTimeout(() => fetchSuggestions(address), 300);
        } else {
            suggestionList.innerHTML = "";
            suggestionList.style.display = "none";
        }
    });

    document.addEventListener("click", (event) => {
        if (!addressInput.contains(event.target) && !suggestionList.contains(event.target)) {
            suggestionList.style.display = "none";
        }
    });

    // Handle input event for address field
    addressInput.addEventListener("input", function () {
        const address = addressInput.value;
        if (address.length > 3) {
            fetchSuggestions(address);
        }
    });

    manualBtn.addEventListener("click", () => {
        manualInputSection.classList.remove("disabled");
        csvInputSection.classList.add("disabled");
        manualBtn.classList.add("active");
        csvBtn.classList.remove("active");
    });

    csvBtn.addEventListener("click", () => {
        csvInputSection.classList.remove("disabled");
        manualInputSection.classList.add("disabled");
        csvBtn.classList.add("active");
        manualBtn.classList.remove("active");
    });

    // Fetch expected power based on latitude and longitude
    function fetchExpectedPower(lat, lon) {
        if (!lat || !lon) return;
        fetch(`http://localhost:5000/get_expected_power?lat=${lat}&lon=${lon}`)
            .then(response => response.json())
            .then(data => {
                expectedPowerOutput.textContent = data.error
                    ? "Error fetching expected power"
                    : `Expected Power: ${data.expected_power} W`;
            });
    }

    // Update expected power when latitude or longitude changes
    latitudeInput.addEventListener("input", () => fetchExpectedPower(latitudeInput.value, longitudeInput.value));
    longitudeInput.addEventListener("input", () => fetchExpectedPower(latitudeInput.value, longitudeInput.value));

    // Calculate true power from user input
    function calculateTruePower() {
        const current = parseFloat(currentInput.value);
        const voltage = parseFloat(voltageInput.value);
        const manualPower = parseFloat(powerInput.value);

        let truePower = 0;
        if (!isNaN(manualPower) && manualPower > 0) {
            truePower = manualPower;
        } else if (!isNaN(current) && !isNaN(voltage)) {
            truePower = current * voltage;
        }

        truePowerOutput.textContent = truePower > 0 ? `True Power: ${truePower.toFixed(2)} W` : "True Power: N/A";
        return truePower;
    }

    // Add event listeners for real-time calculation
    currentInput.addEventListener("input", calculateTruePower);
    voltageInput.addEventListener("input", calculateTruePower);
    powerInput.addEventListener("input", calculateTruePower);

    // Handle CSV file upload and power calculation
    csvInput.addEventListener("change", (event) => {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            const lines = e.target.result.split("\n").slice(1); // Skip header
            let totalPower = 0, count = 0;

            lines.forEach(line => {
                const [current, voltage, power] = line.split(",").map(Number);
                let rowPower = power || (current && voltage ? current * voltage : 0);
                if (rowPower > 0) {
                    totalPower += rowPower;
                    count++;
                }
            });

            const avgPower = count > 0 ? (totalPower / count).toFixed(2) : "N/A";
            truePowerOutput.textContent = `True Power: ${avgPower} W`;
        };
        reader.readAsText(file);
    });

    // Calculate efficiency and display recommendations
    function calculateEfficiency() {
        const expectedPowerText = expectedPowerOutput.textContent.replace("Expected Power: ", "").replace(" W", "");
        const truePowerText = truePowerOutput.textContent.replace("True Power: ", "").replace(" W", "");

        const expectedPower = parseFloat(expectedPowerText);
        const truePower = parseFloat(truePowerText);

        if (isNaN(expectedPower) || isNaN(truePower) || expectedPower === 0) {
            efficiencyOutput.textContent = "Efficiency: N/A";
            recommendationOutput.textContent = "Missing data.";
            recommendationOutput.className = "";
            return;
        }

        const efficiency = ((truePower / expectedPower) * 100).toFixed(2);
        efficiencyOutput.textContent = `Efficiency: ${efficiency}%`;

        if (efficiency >= 90) {
            recommendationOutput.textContent = "Panel is working optimally.";
            recommendationOutput.className = "optimal";
        } else if (efficiency < 90 && efficiency >= 60) {
            recommendationOutput.textContent = "Possible dust or debris affecting efficiency.";
            recommendationOutput.className = "dust-issue";
        } else {
            recommendationOutput.textContent = "Possible faulty wire.";
            recommendationOutput.className = "wire-issue";
        }
    }

    // Handle calculate button click event
    calculateButton.addEventListener("click", function () {
        const current = parseFloat(currentInput.value);
        const voltage = parseFloat(voltageInput.value);
        const power = parseFloat(powerInput.value);
        const lat = latitudeInput.value;
        const lon = longitudeInput.value;

        let formData = new FormData();
        let requestUrl = "http://localhost:5000/manual_data";
        let isCSV = csvInput.files.length > 0;

        if (isCSV) {
            formData.append('file', csvInput.files[0]);
            requestUrl = "http://localhost:5000/upload_csv";
        } else {
            formData.append('current', current);
            formData.append('voltage', voltage);
            formData.append('power', power);
        }

        fetch(requestUrl, { method: "POST", body: formData })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error: " + data.error);
                } else {
                    document.getElementById("true-power").innerText = `True Power: ${data.true_power} W`;

                    // Fetch expected power and then calculate efficiency
                    fetchExpectedPower(lat, lon);
                    setTimeout(calculateEfficiency, 500);
                }
            });
    });
});
