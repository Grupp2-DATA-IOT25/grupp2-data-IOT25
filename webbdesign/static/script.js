const DEMO_SENSORS = [
    { serverKey: "server1", device: { id: "01", name: "ESP32-1" }, temperature: 23.6, humidity: 48, connected: true, lastUpdate: null },
    { serverKey: "server2", device: { id: "02", name: "ESP32-2" }, temperature: 21.9, humidity: 46, connected: true, lastUpdate: null },
    { serverKey: "server3", device: { id: "03", name: "ESP32-3" }, temperature: 24.1, humidity: 49, connected: true, lastUpdate: null }
];

let lastJson = "";

document.addEventListener("DOMContentLoaded", () => { 
    updateSensors(); 
    setInterval(updateSensors, 2000); 
});

async function updateSensors() {
    const info = document.getElementById("data-status");
    let sensors = []; 
    let isLive = false;

    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 3000);
        const response = await fetch("/api/servers", { signal: controller.signal });
        clearTimeout(timeout);

        if (!response.ok) throw new Error("Backend svarade inte");
        const result = await response.json();

        sensors = Object.entries(result).map(([serverKey, server]) => {
            const data = server && server.Data ? server.Data : {};
            return { 
                serverKey, 
                device: { id: serverKey.replace("server", ""), name: data.DeviceId || serverKey }, 
                temperature: typeof data.Temperature === "number" ? data.Temperature : null, 
                humidity: typeof data.Humidity === "number" ? data.Humidity : null, 
                connected: server.connected === true, 
                lastUpdate: server.last_update || null 
            };
        });

        isLive = true; 
        info.textContent = `Live-data synkad ${new Date().toLocaleTimeString()}`; 
        info.style.color = "#cbd5e1";
    } catch (error) {
        sensors = DEMO_SENSORS; 
        info.textContent = "Exempeldata visas (backend ej nådd)"; 
        info.style.color = "#fbbf24";
    }

    const json = JSON.stringify(sensors);
    if (json === lastJson && isLive) return; 
    lastJson = json;

    const temps = sensors.map(s => s.temperature).filter(v => typeof v === "number");
    const hums  = sensors.map(s => s.humidity).filter(v => typeof v === "number");

    document.getElementById("avg-temp").textContent = temps.length ? `${(temps.reduce((a,b)=>a+b,0)/temps.length).toFixed(1)} °C` : "-- °C";
    document.getElementById("avg-humidity").textContent = hums.length ? `${(hums.reduce((a,b)=>a+b,0)/hums.length).toFixed(0)} %` : "-- %";
    document.getElementById("total-devices").textContent = sensors.length;
    document.getElementById("active-device-count").textContent = `${sensors.length} enheter`;
    document.getElementById("temp-device-count").textContent = `${temps.length} enheter`;
    document.getElementById("humidity-device-count").textContent = `${hums.length} enheter`;

    document.getElementById("sensor-list").innerHTML = sensors.map(s => `
        <article class="device-card">
            <div class="device-header">
                <div>
                    <span class="device-id">SERVER ${s.device.id?.toUpperCase() ?? ""}</span>
                    <h3>${s.device.name}</h3>
                </div>
                <span class="online">
                    <span class="status-dot" style="background:${s.connected === false ? '#ef4444' : '#10b981'}"></span>
                    ${s.connected === false ? "Offline" : "Live"}
                </span>
            </div>
            <div class="metric">
                <span>🌡️ Temperatur</span>
                <strong>${s.temperature ?? "—"} <small>°C</small></strong>
            </div>
            <div class="metric">
                <span>💧 Luftfuktighet</span>
                <strong>${s.humidity ?? "—"} <small>%</small></strong>
            </div>
            <div class="device-footer">Senast: ${s.lastUpdate ?? "—"}</div>
        </article>
    `).join("");
}