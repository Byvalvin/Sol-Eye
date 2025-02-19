let map;
let geocodeTimeout; // Store timeout for debouncing input
const debounceDelay = 500; // Delay in ms after the user stops typing before triggering geocoding

// Function to handle geocoding address to lat/lng and auto-fill the fields
function geocodeAddress(address) {
    if (!address) return;

    const geocoder = L.Control.Geocoder.nominatim();

    // Fetch geocoding results from Nominatim API
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

        // Initialize map if not already done
        if (!map) {
            map = L.map('map').setView([lat, lon], 13);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
        } else {
            map.setView([lat, lon], 13);
        }

        // Add a marker for the geocoded location
        const marker = L.marker([lat, lon]).addTo(map);
        marker.bindPopup("Your Location").openPopup();
    });
}

// Handle address input with debounce to limit geocoding calls
document.getElementById("address").addEventListener("input", function() {
    const address = document.getElementById("address").value;
    clearTimeout(geocodeTimeout); // Clear the previous timeout to prevent multiple calls
    geocodeTimeout = setTimeout(function() {
        geocodeAddress(address); // Geocode address after delay
    }, debounceDelay);
});

// Function to fetch address suggestions and display them
document.getElementById("address").addEventListener("input", function() {
    const address = document.getElementById("address").value;
    if (address.length > 3) { // Fetch suggestions if the address is more than 3 characters
        fetch(`https://nominatim.openstreetmap.org/search?q=${address}&format=json&addressdetails=1`)
            .then(response => response.json())
            .then(data => {
                const suggestions = data.map(item => item.display_name);
                showSuggestions(suggestions);
            });
    }
});

// Display address suggestions in a dropdown
function showSuggestions(suggestions) {
    const suggestionList = document.getElementById("address-suggestions");
    suggestionList.innerHTML = ''; // Clear previous suggestions

    suggestions.forEach(suggestion => {
        const li = document.createElement("li");
        li.textContent = suggestion;
        li.onclick = function() {
            document.getElementById("address").value = suggestion;
            geocodeAddress(suggestion); // Geocode the selected suggestion
            suggestionList.innerHTML = ''; // Clear suggestions after selection
        };
        suggestionList.appendChild(li);
    });
}

// Handle pressing Enter to trigger geocoding directly
document.getElementById("address").addEventListener("keydown", function(event) {
    if (event.key === "Enter") {
        const address = document.getElementById("address").value;
        geocodeAddress(address); // Trigger geocoding on Enter key
    }
});

// Handle map click to select a location and update lat/lng fields
document.getElementById("show-map").addEventListener("click", function() {
    const lat = document.getElementById("latitude").value;
    const lon = document.getElementById("longitude").value;

    // Initialize Leaflet map if not already done
    if (!map) {
        map = L.map('map').setView([lat, lon], 13);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
    }

    // Add a marker at the provided lat/lon
    var customIcon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.7.1/dist/images/marker-shadow.png'
    });
    // Then apply it to your marker
    const marker = L.marker([lat, lon], { icon: customIcon }).addTo(map);
    marker.bindPopup("Your Location").openPopup();

    // Update coordinates based on map click
    map.on('click', function(e) {
        const lat = e.latlng.lat;
        const lon = e.latlng.lng;

        // Update the input fields with clicked coordinates
        document.getElementById("latitude").value = lat.toFixed(4);
        document.getElementById("longitude").value = lon.toFixed(4);

        // Update the marker position
        marker.setLatLng([lat, lon]);
    });
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

    // Send form data to backend for processing
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

    // Fetch expected power data based on lat/lng
    fetch(`http://localhost:5000/get_expected_power?lat=${document.getElementById("latitude").value}&lon=${document.getElementById("longitude").value}`)
    .then(response => response.json())
    .then(data => {
        const expectedPower = data.expected_power;
        const truePower = parseFloat(document.getElementById("true-power").innerText.split(": ")[1].replace(" W", ""));
       
        // Display expected power and calculate efficiency
        document.getElementById("expected-power").innerText = `Expected Power: ${expectedPower} W`;
        const efficiency = (truePower / expectedPower) * 100;
        document.getElementById("efficiency").innerText = `Efficiency: ${efficiency.toFixed(2)}%`;
    });
});
