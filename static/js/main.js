let map;

// Initialize the map with default location (Edmonton) above the input fields
function initializeMap() {
    map = L.map('map').setView([53.5461, -113.4938], 10); // Edmonton coordinates
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    L.marker([53.5461, -113.4938]).addTo(map).bindPopup("Edmonton").openPopup();
}

// Function to handle geocoding address to lat/lng and auto-fill the fields
function geocodeAddress(address) {
    if (!address) return;

    const geocoder = L.Control.Geocoder.nominatim();
    geocoder.geocode(address, function(results) {
        if (results.length === 0) {
            alert("Address not found.");
            return;
        }

        const lat = results[0].center.lat;
        const lon = results[0].center.lng;

        // Auto-fill the latitude and longitude fields
        document.getElementById("latitude").value = lat.toFixed(4);
        document.getElementById("longitude").value = lon.toFixed(4);

        // Update map view and marker
        map.setView([lat, lon], 13);
        const marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup("Your Location").openPopup();
    });
}

// Function to fetch address suggestions
function fetchSuggestions(query) {
    fetch(`https://nominatim.openstreetmap.org/search?q=${query}&format=json&addressdetails=1`)
        .then(response => response.json())
        .then(data => {
            const suggestions = data.map(item => item.display_name);
            showSuggestions(suggestions);
        });
}

// Display address suggestions
function showSuggestions(suggestions) {
    const suggestionList = document.getElementById("address-suggestions");
    suggestionList.innerHTML = '';

    suggestions.forEach(suggestion => {
        const li = document.createElement("li");
        li.textContent = suggestion;
        li.onclick = function() {
            document.getElementById("address").value = suggestion;
            geocodeAddress(suggestion);
            suggestionList.innerHTML = '';
        };
        suggestionList.appendChild(li);
    });
}

// Event listeners
document.getElementById("address").addEventListener("input", function() {
    const address = document.getElementById("address").value;
    if (address.length > 3) { // Only fetch suggestions for addresses longer than 3 characters
        fetchSuggestions(address);
    }
});

// Trigger geocoding when "Enter" key is pressed
document.getElementById("address").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        const address = document.getElementById("address").value;
        geocodeAddress(address); // Trigger geocoding
    }
});

// Handle form submission for calculating true power
document.getElementById("calculate").addEventListener("click", function() {
    const current = document.getElementById("current").value;
    const voltage = document.getElementById("voltage").value;
    const power = document.getElementById("power").value;

    let formData = new FormData();
    let requestUrl = "http://localhost:5000/manual_data";
    let isCSV = document.getElementById("csv-upload").files.length > 0;

    if (isCSV) {
        // Handle CSV file upload
        formData.append('file', document.getElementById("csv-upload").files[0]);
        requestUrl = "http://localhost:5000/upload_csv";
    } else {
        // Handle manual data entry
        formData.append('current', current);
        formData.append('voltage', voltage);
        formData.append('power', power);
    }

    fetch(requestUrl, {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            alert("Error: " + data.error);
        } else {
            document.getElementById("true-power").innerText = `True Power: ${data.true_power} W`;
        }
    });

    // Fetch expected power based on lat/lng
    fetch(`http://localhost:5000/get_expected_power?lat=${document.getElementById("latitude").value}&lon=${document.getElementById("longitude").value}`)
    .then(response => response.json())
    .then(data => {
        const expectedPower = data.expected_power;
        const truePower = parseFloat(document.getElementById("true-power").innerText.split(": ")[1].replace(" W", ""));

        // Display expected power and efficiency
        document.getElementById("expected-power").innerText = `Expected Power: ${expectedPower} W`;
        const efficiency = (truePower / expectedPower) * 100;
        document.getElementById("efficiency").innerText = `Efficiency: ${efficiency.toFixed(2)}%`;
    });
});

// Initialize map on page load
initializeMap();
