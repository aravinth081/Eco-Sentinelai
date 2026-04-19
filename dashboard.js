 // =========================================================
// EcoSentinel AI - Ultra Cognitive Digital Twin Engine
// =========================================================

let isManualMode = false;
let timeStep = 0;
let currentSimType = null;
const API_BASE_URL = "http://localhost:8000/api";

// Global data states for PDF reporting
let currentMetrics = { pm25: 15, ecoli: 0, ph: 7.2, threat: 'LOW', riskScore: 92, summary: '', impactPop: 0, impactEcon: 0 };
let lastGeneratedPDF = null; 

// --- Leaflet Map & Satellite Setup ---
let map, cvMap, droneMarker, selectedRegionHighlight = null;
let zoneCircles = {}, swarmMarkers = []; 

function initMap() {
    const mapEl = document.getElementById('city-map');
    if(!mapEl) return;

    map = L.map('city-map').setView([40.7128, -74.0060], 12); 
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', { attribution: '&copy; Sentinel Core', maxZoom: 19 }).addTo(map);

    const geocoder = L.Control.geocoder({ defaultMarkGeocode: false, placeholder: "Search Target Zone..." }).addTo(map);
    geocoder.on('markgeocode', function(e) { let latlng = e.geocode.center; map.setView(latlng, 13); focusTargetZone(latlng, e.geocode.name); });

    map.on('click', function(e) {
        fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${e.latlng.lat}&lon=${e.latlng.lng}`)
        .then(res => res.json())
        .then(data => {
            let placeName = data.address.city || data.address.town || data.address.state || "UNKNOWN SECTOR";
            focusTargetZone(e.latlng, placeName);
        }).catch(() => { focusTargetZone(e.latlng, "CUSTOM TARGET SECTOR"); });
    });

    const cvMapContainer = document.getElementById('cv-map-container');
    if (cvMapContainer) {
        cvMap = L.map('cv-map-container', { zoomControl: false, dragging: false, scrollWheelZoom: false }).setView([40.7128, -74.0060], 15);
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}').addTo(cvMap);
    }

    zoneCircles['zone_0'] = L.circle([40.7306, -73.9352], { color: '#00E676', fillColor: '#00E676', fillOpacity: 0.2, radius: 2000 }).addTo(map);
    zoneCircles['zone_1'] = L.circle([40.7128, -74.0060], { color: '#00E676', fillColor: '#00E676', fillOpacity: 0.2, radius: 2500 }).addTo(map);

    const droneIcon = L.divIcon({ className: 'drone-icon', html: '<div style="font-size: 24px; text-shadow: 0 0 10px #00E5FF;">🚁</div>', iconSize: [30, 30] });
    droneMarker = L.marker([40.7128, -74.0060], {icon: droneIcon, opacity: 0}).addTo(map);
}

function focusTargetZone(latlng, placeName) {
    if(selectedRegionHighlight) map.removeLayer(selectedRegionHighlight);
    selectedRegionHighlight = L.circle(latlng, { color: '#D500F9', fillColor: '#D500F9', fillOpacity: 0.3, radius: 1500, className: 'pulse-safe' }).addTo(map);
    let shortName = placeName.split(',')[0].toUpperCase();
    if(document.getElementById('cv-location-name')) document.getElementById('cv-location-name').textContent = shortName;
    if(cvMap) cvMap.setView(latlng, 15);
}

function deployBioSwarm(lat, lng) {
    clearSwarm();
    for(let i=0; i<20; i++) {
        let offsetLat = lat + (Math.random() - 0.5) * 0.015; let offsetLng = lng + (Math.random() - 0.5) * 0.015;
        let bot = L.circleMarker([offsetLat, offsetLng], { radius: 3, color: '#D500F9', fillColor: '#00E5FF', fillOpacity: 0.8, weight: 1 }).addTo(map);
        swarmMarkers.push(bot);
    }
}
function clearSwarm() { swarmMarkers.forEach(m => map.removeLayer(m)); swarmMarkers = []; }

// --- Chart Setup ---
const chartData = { labels: [], pm25: [], co2: [], ph: [], turbidity: [] };
const MAX_POINTS = 15;
let airChart, waterChart;
let graphCounter = 0; // Ithu thaan number-a track panna poguthu

function initCharts() {
    const airCtx = document.getElementById('airChart');
    const waterCtx = document.getElementById('waterChart');
    if(!airCtx || !waterCtx) return;

    Chart.defaults.color = '#8BA4DF'; Chart.defaults.font.family = "'Rajdhani', sans-serif";

    airChart = new Chart(airCtx.getContext('2d'), {
        type: 'line', data: { labels: chartData.labels, datasets: [
            { label: 'PM2.5 (µg/m³)', data: chartData.pm25, borderColor: '#00E5FF', backgroundColor: 'rgba(0, 229, 255, 0.1)', fill: true, tension: 0.4 },
            { label: 'CO2 (ppm/10)', data: chartData.co2, borderColor: '#FF1744', borderDash: [5, 5], tension: 0.4 }
        ]}, options: { responsive: true, maintainAspectRatio: false, animation: { duration: 500 }, scales: { y: { min: 0 } } }
    });

    waterChart = new Chart(waterCtx.getContext('2d'), {
        type: 'line', data: { labels: chartData.labels, datasets: [
            { label: 'pH Level', data: chartData.ph, borderColor: '#00E676', backgroundColor: 'rgba(0, 230, 118, 0.1)', fill: true, tension: 0.4 },
            { label: 'Turbidity (NTU)', data: chartData.turbidity, borderColor: '#D500F9', tension: 0.4 }
        ]}, options: { responsive: true, maintainAspectRatio: false, animation: { duration: 500 }, scales: { y: { min: 0 } } }
    });
}

// --- System Engine Simulator ---
let timelineEvents = []; let lastThreatLevel = "LOW";

function generateData() {
    timeStep += 0.2;
    if(document.getElementById('current-time')) document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
    
    let pm25 = 20 + Math.sin(timeStep) * 12 + (Math.random() * 5);
    let ecoli = 1.5 + Math.abs(Math.cos(timeStep * 0.5)) * 3;
    let ph = 7.2 + Math.sin(timeStep * 0.3) * 0.4;
    let turb = 4 + Math.sin(timeStep * 0.8) * 2; let co2 = 40 + Math.random() * 5;
    
    let threat = "LOW"; let score = 92 - Math.floor(Math.random() * 5);
    let summary = "System metrics within nominal range. City is secure."; let rootCause = "Stable environment.";

    // Sim Buttons Override
    if (currentSimType === 'SMOG') {
        pm25 = 150 + Math.random() * 20; co2 = 80 + Math.random() * 10;
        threat = "CRITICAL"; score = 15; summary = "Severe smog anomaly detected. Rerouting traffic."; rootCause = "Industrial emission spike detected by Orbital CV.";
    } else if (currentSimType === 'BIO') {
        ecoli = 85 + Math.random() * 10; ph = 4.2;
        threat = "CRITICAL"; score = 12; summary = "Critical bio-hazard detected. Isolating water supply."; rootCause = "Bacterial contamination tracked in Reservoir.";
    } 
    // INLINE MANUAL OVERRIDE
    else if (isManualMode) {
        const mPm25 = parseFloat(document.getElementById('inline-pm25')?.value);
        const mEcoli = parseFloat(document.getElementById('inline-ecoli')?.value);
        const mPh = parseFloat(document.getElementById('inline-ph')?.value);
        
        if (!isNaN(mPm25)) pm25 = mPm25;
        if (!isNaN(mEcoli)) ecoli = mEcoli;
        if (!isNaN(mPh)) ph = mPh;

        if (pm25 > 100 || ecoli > 40 || ph < 5 || ph > 9) {
            threat = "CRITICAL"; score = 10 + Math.floor(Math.random() * 5);
            summary = "Critical anomaly detected via Analyst Console."; rootCause = "Manual Edge Injection Confirmed.";
        }
    }

    currentMetrics = { pm25, ecoli, ph, threat, riskScore: score, summary };

    const bbox = document.getElementById('cv-bounding-box');
    if (bbox) bbox.style.display = (threat === 'CRITICAL' && pm25 > 100) ? 'block' : 'none';

    if (threat !== lastThreatLevel) { logTimelineEvent(`Threat Level Shift: ${threat}`, summary); lastThreatLevel = threat; }

    updateDashboardUI(pm25, ecoli, ph, turb, co2, threat, score, summary, rootCause);
    updateCognitivePanels(pm25, ecoli, threat);
    updateAgroNode(currentSimType || (isManualMode && threat === 'CRITICAL' ? 'BIO' : null));
    updateMultiTierWorkflow(threat);
    updateGraphs(pm25, ph, turb, co2);
}

 function updateDashboardUI(pm25, ecoli, ph, turb, co2, threat, score, summary, rootCause) {
    const ecoliEl = document.getElementById('bio-ecoli');
    if(ecoliEl) { ecoliEl.textContent = `${ecoli.toFixed(2)} ppm`; ecoliEl.className = ecoli > 40 ? "value critical" : "value ok"; }
    if(document.getElementById('risk-value')) { document.getElementById('risk-value').textContent = score; document.getElementById('risk-value').style.color = threat === "CRITICAL" ? "#FF1744" : "#00E676"; }
    if(document.getElementById('threat-level')) { document.getElementById('threat-level').textContent = `THREAT LEVEL: ${threat}`; document.getElementById('threat-level').className = `level ${threat === "CRITICAL" ? "high" : "low"}`; }
    if(document.getElementById('ai-summary')) document.getElementById('ai-summary').textContent = summary;
    if(document.getElementById('explain-reason')) document.getElementById('explain-reason').textContent = rootCause;

    const infraList = document.getElementById('infra-list'); 
    const drone = document.getElementById('drone-manifest');
    const auditHash = document.getElementById('audit-hash'); // <-- Puthu Hash Logic Inga Irukku

    if (threat === "CRITICAL") {
        if(infraList) infraList.innerHTML = `<div class="infra-item" style="border-left-color:#FF1744;"><span class="name">[SYSTEM] Isolate Sector</span><span class="status pulse-crit">ENGAGED</span></div>`;
        if(drone) drone.innerHTML = `<div style="color:#00E5FF; font-size:0.9rem;">> DISPATCH ID: DS-9914</div><div style="color:#FF1744; font-size: 0.9rem;">TARGET: SECTOR ANOMALY</div>`;
        
        // HASH GENERATOR EFFECT
        if(auditHash) {
            const randomHash = Math.random().toString(16).substr(2, 10).toUpperCase();
            auditHash.innerHTML = `<span style="color:#FF1744;">> AI DECISION HASH LOGGED:</span> <br> <span style="color:#00E5FF;">0x${randomHash}A9F...</span>`;
        }

        Object.values(zoneCircles).forEach(c => c.setStyle({color: '#FF1744', fillColor: '#FF1744'}));
        if(droneMarker) droneMarker.setOpacity(1);
        if(currentSimType === 'BIO' || ecoli > 40) deployBioSwarm(40.7128, -74.0060);
    } else {
        if(infraList) infraList.innerHTML = `<div class="infra-item"><span class="name">All Systems Nominal</span><span class="status pulse-safe">STANDBY</span></div>`;
        if(drone) drone.innerHTML = `<div class="no-dispatch">NO ACTIVE DISPATCHES</div>`;
        
        // RESET HASH
        if(auditHash) {
            auditHash.innerHTML = `> WAITING FOR AI DECISION HASH...`;
        }

        Object.values(zoneCircles).forEach(c => c.setStyle({color: '#00E676', fillColor: '#00E676'}));
        if(droneMarker) droneMarker.setOpacity(0); clearSwarm();
    }
}
function updateCognitivePanels(pm25, ecoli, threat) {
    let popRisk = threat === "CRITICAL" ? Math.floor(45000 + Math.random() * 5000) : 0;
    let econDamage = threat === "CRITICAL" ? Math.floor(1200000 + Math.random() * 100000) : 0;
    let aqi = Math.floor((pm25 / 15) * 50); if (aqi > 500) aqi = 500;
    
    currentMetrics.impactPop = popRisk; currentMetrics.impactEcon = econDamage; 

    if(document.getElementById('impact-pop')) document.getElementById('impact-pop').textContent = popRisk.toLocaleString();
    if(document.getElementById('impact-econ')) document.getElementById('impact-econ').textContent = `$${econDamage.toLocaleString()}`;
    if(document.getElementById('impact-aqi')) document.getElementById('impact-aqi').textContent = aqi;
    if(document.getElementById('impact-rec')) document.getElementById('impact-rec').textContent = threat === "CRITICAL" ? "4.5 hrs" : "0 hrs";

    const tFeed = document.getElementById('timeline-feed');
    if(tFeed) tFeed.innerHTML = timelineEvents.map(t => `<div style="display:flex; gap:10px;"><span style="color:var(--accent-cyan)">[${t.time}]</span><span style="color:#fff">${t.event}</span><span style="color:var(--text-dim)">- ${t.action}</span></div>`).join('');
}

function updateAgroNode(simType) {
    const soilEl = document.getElementById('agro-soil'); const yieldEl = document.getElementById('agro-yield'); const alertEl = document.getElementById('agro-alert');
    if(!soilEl) return;
    if (simType === 'BIO') { soilEl.textContent = 'HIGH TOXICITY'; soilEl.style.color = '#FF1744'; yieldEl.textContent = '45% EST. DROP'; yieldEl.style.color = '#FF1744'; } 
    else if (simType === 'SMOG') { soilEl.textContent = 'MODERATE ACIDITY'; soilEl.style.color = '#ff9d00'; yieldEl.textContent = '12% EST. DROP'; yieldEl.style.color = '#ff9d00'; } 
    else { soilEl.textContent = 'MINIMAL'; soilEl.style.color = '#00E676'; yieldEl.textContent = '0% DROP'; yieldEl.style.color = '#00E5FF'; }
}

function updateMultiTierWorkflow(threat) {
    const wFeed = document.getElementById('workflow-feed'); if(!wFeed) return;
    if(threat === 'CRITICAL') wFeed.innerHTML = `<div style="display:flex; align-items:center; gap:10px;"><span style="width:10px; height:10px; border-radius:50%; background:#FF1744; animation: blink 1s infinite;"></span><span style="color:#FF1744; font-size:0.85rem; font-weight:bold;">Auto-Containment Engaged</span></div>`;
    else wFeed.innerHTML = `<div style="display:flex; align-items:center; gap:10px;"><span style="width:12px; height:12px; border-radius:50%; background:var(--accent-green);"></span><span style="color:#fff; font-family:var(--font-head);">Monitoring Sensors (Nominal)</span></div>`;
}

function updateGraphs(pm25, ph, turb, co2) {
    // BUG FIX: Removed 'time' and added 'number counter'
    graphCounter++;
    const xLabel = graphCounter.toString(); // Shows 1, 2, 3...
    
    chartData.labels.push(xLabel); chartData.pm25.push(pm25); chartData.co2.push(co2); chartData.ph.push(ph); chartData.turbidity.push(turb);
    if (chartData.labels.length > MAX_POINTS) { chartData.labels.shift(); chartData.pm25.shift(); chartData.co2.shift(); chartData.ph.shift(); chartData.turbidity.shift(); }
    if(airChart) airChart.update(); if(waterChart) waterChart.update();
}

function logTimelineEvent(event, action) { timelineEvents.unshift({ time: new Date().toLocaleTimeString(), event: event, action: action }); if (timelineEvents.length > 6) timelineEvents.pop(); }

// --- INLINE MANUAL TRIGGERS & PDF ---
window.injectAirSpike = function() {
    isManualMode = true; document.getElementById('btn-resume-air').style.display = 'block';
    logTimelineEvent(`AIR QUALITY ANALYST`, "Manual PM2.5 parameters injected."); generateData();
};
window.injectWaterSpike = function() {
    isManualMode = true; document.getElementById('btn-resume-water').style.display = 'block';
    logTimelineEvent(`HYDRO ANALYST`, "Manual Water parameters injected."); generateData();
};
window.resumeAuto = function() {
    isManualMode = false;
    document.getElementById('btn-resume-air').style.display = 'none'; document.getElementById('btn-resume-water').style.display = 'none';
    if(document.getElementById('inline-pm25')) document.getElementById('inline-pm25').value = '';
    if(document.getElementById('inline-ecoli')) document.getElementById('inline-ecoli').value = '';
    if(document.getElementById('inline-ph')) document.getElementById('inline-ph').value = '';
    logTimelineEvent(`OVERRIDE CLEARED`, "Resuming autonomous monitoring."); generateData();
};

window.triggerSim = function(type) {
    currentSimType = type; logTimelineEvent(`SIMULATOR: ${type}`, "Injecting critical anomalies..."); generateData();
    setTimeout(() => { currentSimType = null; logTimelineEvent(`OVERRIDE CLEARED`, "System returning to nominal state."); }, 15000); 
};

// --- DYNAMIC PDF GENERATION (PREVIEW MODAL & DOWNLOAD) ---
window.previewReport = function(type) {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();
    const ts = new Date().toLocaleString();

    doc.setFillColor(3, 5, 8); doc.rect(0, 0, 210, 297, 'F'); 
    doc.setTextColor(0, 229, 255); doc.setFontSize(26); doc.text("ECOSENTINEL AI - INTELLIGENCE REPORT", 15, 25);
    doc.setFontSize(10); doc.setTextColor(150, 150, 150);
    doc.text(`REPORTED BY: ARAVINTH S | DATE: ${ts}`, 15, 32);
    
    doc.setDrawColor(0, 229, 255); doc.line(15, 38, 195, 38);
    
    doc.setFontSize(16); doc.setTextColor(255, 255, 255);
    doc.text(`REPORT TARGET: ${type} QUALITY ANALYSIS`, 15, 55);
    
    doc.setFontSize(12);
    doc.text(`CURRENT THREAT LEVEL: ${currentMetrics.threat}`, 15, 75);
    doc.text(`CITY RISK SCORE: ${currentMetrics.riskScore} / 100`, 15, 85);
    
    if(type === 'AIR') {
        doc.text(`DETECTED PM2.5 LEVEL: ${currentMetrics.pm25.toFixed(2)} ug/m3`, 15, 95);
        if(currentMetrics.pm25 > 100) { doc.setTextColor(255, 23, 68); doc.text("CRITICAL: Air quality exceeds safe limits. Industrial emissions suspected.", 15, 105); doc.setTextColor(255, 255, 255); }
    } else {
        doc.text(`DETECTED E.COLI PATHOGEN: ${currentMetrics.ecoli.toFixed(2)} ppm`, 15, 95);
        if(currentMetrics.ecoli > 40) { doc.setTextColor(255, 23, 68); doc.text("CRITICAL: Severe biological contamination in water supply.", 15, 105); doc.setTextColor(255, 255, 255); }
    }

    doc.setTextColor(0, 229, 255);
    doc.text(`ESTIMATED ECONOMIC DAMAGE: $${currentMetrics.impactEcon.toLocaleString()}`, 15, 125);
    doc.text(`CITIZENS AT RISK: ${currentMetrics.impactPop.toLocaleString()}`, 15, 135);
    
    doc.text("AI CORE DECISION: " + (currentMetrics.threat === "CRITICAL" ? "AUTO-CONTAINMENT PROTOCOLS ENGAGED." : "ALL SYSTEMS AUTONOMOUSLY SECURED."), 15, 155);

    const pdfBlob = doc.output('blob');
    const pdfURL = URL.createObjectURL(pdfBlob);
    
    document.getElementById('pdf-preview-frame').src = pdfURL;
    document.getElementById('pdf-modal').style.display = 'flex';
    
    lastGeneratedPDF = { blob: pdfBlob, name: `EcoSentinel_${type}_Report.pdf` };
};

window.downloadReport = function() {
    if(lastGeneratedPDF) {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(lastGeneratedPDF.blob);
        link.download = lastGeneratedPDF.name;
        link.click();
    }
};

window.closePreview = function() {
    document.getElementById('pdf-modal').style.display = 'none';
};

 // --- FLOATING CHATBOT (FIXED VISIBILITY & BRAIN) ---
const chatBtn = document.getElementById('floating-chat-btn'); 
const chatWindow = document.getElementById('floating-chat-window');

if (chatBtn && chatWindow) {
    chatBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isActive = chatWindow.classList.toggle('active');

        if (isActive) {
            chatWindow.style.display = 'flex';
            setTimeout(() => {
                chatWindow.style.opacity = '1';
                chatWindow.style.pointerEvents = 'all';
                chatWindow.style.transform = 'translateY(0) scale(1)';
            }, 10);
            
            chatBtn.innerHTML = '<svg width="28" height="28" fill="none" stroke="#000" stroke-width="2.5" viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"></path></svg>';
        } else {
            chatWindow.style.opacity = '0';
            chatWindow.style.pointerEvents = 'none';
            chatWindow.style.transform = 'translateY(30px) scale(0.95)';
            setTimeout(() => {
                chatWindow.style.display = 'none';
            }, 400);
            
            chatBtn.innerHTML = '<svg width="30" height="30" fill="none" stroke="#000" stroke-width="2.5" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>';
        }
    });
}

function getProjectContextResponse(query) {
    const q = query.toLowerCase();

    if (q.includes("aravinth") || q.includes("creator") || q.includes("who is created") || q.includes("who created") || q.includes("who made") || q.includes("developer") || q.includes("engineered by")) {
        return "EcoSentinel AI was exclusively engineered and developed by Aravinth S, He designed the Multi-Agent logic and the Digital Twin architecture.";
    }

    if (q.includes("anomaly") || q.includes("status") || q.includes("threat") || q.includes("current")) {
        const threatVal = document.getElementById('threat-level')?.textContent || "LOW";
        return `System current status is ${threatVal}. All telemetry nodes are active and monitoring real-time data.`;
    }

    if (q.includes("hi") || q.includes("hello") || q.includes("hey")) {
        return "Greetings! I am the EcoSentinel AI Core. Ask me about my developer Aravinth S, our project features, or the current city environment.";
    }

    const knowledgeBase = [
        {
            keywords: ["ecosentinel", "what is this", "about the project", "mission", "goal"],
            answer: "EcoSentinel AI is a Cognitive Digital Twin designed for urban risk management. It uses Multi-Agent AI to monitor water and air quality autonomously."
        },
        {
            keywords: ["air", "pm2.5", "pm 2.5", "co2", "smog", "pollution"],
            answer: "For Air Quality, I monitor PM2.5 and CO2 levels in real-time. If critical smog is detected, the AI calculates the AQI and prepares autonomous mitigation."
        },
        {
            keywords: ["water", "ph", "turbidity", "hydro"],
            answer: "For Water Safety, I track pH levels and Turbidity. Deviations from the baseline automatically trigger contamination alerts."
        },
        {
            keywords: ["e.coli", "ecoli", "biohazard", "pathogen", "bacteria", "bio-hazard"],
            answer: "E.coli is a critical bio-hazard metric. If microbial biosensors detect E.coli levels above safe limits, the system triggers a containment alert and prepares Bio-bot deployment."
        },
        {
            keywords: ["agro", "agriculture", "farm", "crop", "soil", "yield"],
            answer: "The Agro-Intelligence Node analyzes how urban pollution impacts farming. It calculates soil toxicity risks and predicts potential drops in crop yields."
        },
        {
            keywords: ["economic", "damage", "cost", "citizen", "risk", "impact"],
            answer: "The Impact Agent calculates estimated financial losses and citizen risk levels in real-time by analyzing healthcare costs and pollution exposure."
        },
        {
            keywords: ["event", "retrofest", "explorer thesis", "hackathon"],
            answer: "This platform is being presented as part of the Explorer Thesis session. It showcases advanced environmental telemetry and AI governance."
        },
        {
            keywords: ["how does it work", "technology", "tech stack", "backend", "frontend", "architecture"],
            answer: "[ADVANCED]: It operates on a FastAPI backend with Leaflet JS for spatial mapping. It features an asynchronous core for handling high-frequency telemetry from simulated IoT nodes."
        },
        {
            keywords: ["multi-agent", "agent", "decision making", "workflow"],
            answer: "[ADVANCED]: The system utilizes a Multi-Agent architecture. Distinct AI models process data in parallel (Monitoring, Predictive, Economic) to execute rapid, autonomous workflow decisions."
        },
        {
            keywords: ["blockchain", "ledger", "immutable", "hash", "audit", "security"],
            answer: "[ADVANCED]: To ensure Zero-Trust accountability, every autonomous decision made by the AI Core generates a cryptographic hash. This Immutable Audit Ledger prevents unauthorized data manipulation."
        },
        {
            keywords: ["orbital", "cv", "computer vision", "satellite", "vision"],
            answer: "[ADVANCED]: Orbital Vision uses Computer Vision algorithms to detect physical emission sources. When a PM2.5 spike occurs, the CV module isolates the exact origin sector."
        }
    ];

    let bestMatch = null;
    let highestScore = 0;

    for (let item of knowledgeBase) {
        let score = 0;
        for (let kw of item.keywords) {
            if (q.includes(kw)) {
                score++;
            }
        }
        if (score > highestScore) {
            highestScore = score;
            bestMatch = item.answer;
        }
    }

    return highestScore > 0 ? bestMatch : null; 
}

document.getElementById('send-btn')?.addEventListener('click', async () => {
    const msgBox = document.getElementById('chat-messages'); 
    const input = document.getElementById('chat-input');
    const msg = input.value.trim(); 
    if (!msg) return;
    
    msgBox.innerHTML += `<div class="msg user">${msg}</div>`; 
    input.value = ""; 
    msgBox.scrollTop = msgBox.scrollHeight;
    
    const loadingId = "load-" + Date.now(); 
    msgBox.innerHTML += `<div id="${loadingId}" class="msg system" style="opacity: 0.5;">> Analysing...</div>`; 
    msgBox.scrollTop = msgBox.scrollHeight;

    setTimeout(async () => {
        let smartReply = getProjectContextResponse(msg);
        if (smartReply) {
            document.getElementById(loadingId).outerHTML = `<div class="msg system console-response">> [KNOWLEDGE BASE]: ${smartReply}</div>`;
        } else {
            document.getElementById(loadingId).outerHTML = `<div class="msg system console-response">> [EDGE AI]: System is operating in localized mode. Please ask about EcoSentinel, Aravinth S, or system status.</div>`;
        }
        msgBox.scrollTop = msgBox.scrollHeight;
    }, 800); 
});

document.getElementById('chat-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('send-btn').click();
});

window.onload = () => { 
    const headerElement = document.querySelector('.main-header');
    if(headerElement) {
        headerElement.style.setProperty('position', 'relative', 'important');
        headerElement.style.setProperty('margin-bottom', '25px', 'important');
    }
    
    initMap(); 
    initCharts(); 
    generateData(); 
    setInterval(generateData, 2500); 
};