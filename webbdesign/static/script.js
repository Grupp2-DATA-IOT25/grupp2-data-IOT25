const API_URL = CONFIG.apiUrls[CONFIG.environment];
let updating = false;

function safeText(value) {
    return String(value).replace(/[&<>"']/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[character]);
}

function showNumber(value, digits = 1) {
    return typeof value === "number" && Number.isFinite(value)
        ? value.toFixed(digits) : "--";
}

function renderSensors(sensors) {
    const online = sensors.filter(sensor => sensor.connected);
    const temperatures = online.map(sensor => sensor.temperature).filter(Number.isFinite);
    const humidities = online.map(sensor => sensor.humidity).filter(Number.isFinite);

    const average = (values, digits, unit) => values.length
        ? `${(values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(digits)} ${unit}`
        : `-- ${unit}`;

    document.getElementById("avg-temp").textContent = average(temperatures, 1, "°C");
    document.getElementById("avg-humidity").textContent = average(humidities, 0, "%");
    document.getElementById("total-devices").textContent = online.length;
    document.getElementById("active-device-count").textContent = `${online.length} aktiva av ${sensors.length}`;
    document.getElementById("temp-device-count").textContent = `${temperatures.length} enheter`;
    document.getElementById("humidity-device-count").textContent = `${humidities.length} enheter`;

    document.getElementById("sensor-list").innerHTML = sensors.map(sensor => {
        const status = sensor.connected ? "Online" : "Offline";
        const color = sensor.connected ? "#10b981" : "#ef4444";
        const temperature = sensor.connected ? showNumber(sensor.temperature) : "--";
        const humidity = sensor.connected ? showNumber(sensor.humidity) : "--";
        return `
            <article class="device-card">
                <div class="device-header">
                    <div>
                        <span class="device-id">${safeText(sensor.serverKey)}</span>
                        <h3>${safeText(sensor.name)}</h3>
                    </div>
                    <span class="online" style="color:${color}">
                        <span class="status-dot" style="background:${color}"></span>${status}
                    </span>
                </div>
                <div class="metric"><span>🌡️ Temperatur</span><strong>${temperature} <small>°C</small></strong></div>
                <div class="metric"><span>💧 Luftfuktighet</span><strong>${humidity} <small>%</small></strong></div>
                <div class="device-footer">Senast: ${safeText(sensor.lastUpdate || "Ingen uppdatering")}</div>
            </article>`;
    }).join("");
}

async function updateSensors() {
    if (updating) return;
    updating = true;
    const status = document.getElementById("data-status");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 3000);

    try {
        const response = await fetch(API_URL, { signal: controller.signal, cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const result = await response.json();
        if (!result || typeof result !== "object" || Array.isArray(result)) {
            throw new Error("Felaktigt format från API");
        }

        const sensors = Object.entries(result).map(([serverKey, server]) => {
            const data = server && server.Data ? server.Data : {};
            return {
                serverKey,
                name: data.DeviceId || serverKey,
                temperature: typeof data.Temperature === "number" ? data.Temperature : null,
                humidity: typeof data.Humidity === "number" ? data.Humidity : null,
                connected: server?.connected === true,
                lastUpdate: server?.last_update || null
            };
        });

        renderSensors(sensors);
        status.textContent = CONFIG.environment === "test" ? "Testdata hämtad" : "API-data hämtad";
        status.style.color = "#cbd5e1";
    } catch (error) {
        status.textContent = "Kunde inte hämta data från API:et";
        status.style.color = "#fbbf24";
        renderSensors([]);
        console.error("Fel vid hämtning:", error);
    } finally {
        clearTimeout(timeout);
        updating = false;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    updateSensors();
    setInterval(updateSensors, 2000);
});
