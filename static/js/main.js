document.addEventListener("DOMContentLoaded", () => {
    const addressInput = document.getElementById("address");
    const suggestionList = document.getElementById("address-suggestions");
    const latitudeInput = document.getElementById("latitude");
    const longitudeInput = document.getElementById("longitude");
    const fetchDataButton = document.getElementById("fetch-data");
    const ctx = document.getElementById("solarChart").getContext("2d");
    let solarChart;
    let debounceTimeout;
    let lastSelectedAddress = "";
    let addressCache = JSON.parse(localStorage.getItem("addressCache")) || {};

    function fetchSuggestions(query) {
        if (addressCache[query]) {
            updateSuggestions(addressCache[query]);
            return;
        }

        fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=json&addressdetails=1`)
            .then(response => response.json())
            .then(data => {
                if (data.length === 0) return;
                addressCache[query] = data.slice(0, 3);
                localStorage.setItem("addressCache", JSON.stringify(addressCache));
                updateSuggestions(addressCache[query]);
            });
    }

    function updateSuggestions(data) {
        suggestionList.innerHTML = "";
        data.slice(0, 3).forEach(item => {
            const li = document.createElement("li");
            li.textContent = item.display_name;
            li.onclick = () => {
                selectAddress(item);
            };
            suggestionList.appendChild(li);
        });
        suggestionList.style.display = "block";
    }

    function selectAddress(item) {
        if (lastSelectedAddress === item.display_name) return;
        lastSelectedAddress = item.display_name;
        addressInput.value = item.display_name;
        latitudeInput.value = item.lat;
        longitudeInput.value = item.lon;
        suggestionList.innerHTML = "";
    }

    addressInput.addEventListener("input", () => {
        clearTimeout(debounceTimeout);
        const address = addressInput.value;
        if (address.length >= 10) {
            debounceTimeout = setTimeout(() => fetchSuggestions(address), 1000);
        } else {
            suggestionList.innerHTML = "";
            suggestionList.style.display = "none";
        }
    });

    addressInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter" && suggestionList.firstChild) {
            selectAddress(addressCache[addressInput.value][0]);
        }
    });

    document.addEventListener("click", (event) => {
        if (!addressInput.contains(event.target) && !suggestionList.contains(event.target)) {
            suggestionList.style.display = "none";
        }
    });

    fetchDataButton.addEventListener("click", () => {
        const lat = latitudeInput.value;
        const lon = longitudeInput.value;
        if (!lat || !lon) {
            alert("Please enter valid latitude and longitude");
            return;
        }

        fetch(`/get_solar_data?lat=${lat}&lon=${lon}`)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert("Error fetching data: " + data.error);
                    return;
                }
                updateChart(data.solar_data);
            });
    });

    function updateChart(data) {
        const labels = data.map(entry => `${entry.HR}:00`);
        const values = data.map(entry => entry["Horas Solares"]);

        if (solarChart) {
            solarChart.destroy();
        }

        solarChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [{
                    label: "Horas Solares",
                    data: values,
                    borderColor: "#FFA500",
                    backgroundColor: "rgba(255, 165, 0, 0.5)",
                    fill: true,
                }]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Hour of the Day"
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: "Solar Hours"
                        }
                    }
                }
            }
        });
    }
});
