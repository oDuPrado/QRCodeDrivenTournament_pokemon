let totalTime = 1800; // 30 minutos em segundos
let countdownInterval = null;
let lastData = null;
let roundStartTime = null;
let playingTables = {};
let tournamentStarted = false;
let tournamentEnded = false;
let playingInterval = null;
let playerStats = {};
let processedMatches = {};

const setupSection = document.getElementById("setup-section");
const tournamentSection = document.getElementById("tournament-section");
const scoreboardSection = document.getElementById("scoreboard-section");

const startBtn = document.getElementById("start-btn");
const nextRoundBtn = document.getElementById("next-round-btn");
const statsBtn = document.getElementById("stats-btn");
const backToSetupBtn = document.getElementById("back-to-setup-btn");

const countdownTimer = document.getElementById("countdown-timer");
const tablesContainer = document.getElementById("tables-container");
const initialTablesContainer = document.getElementById(
  "initial-tables-container"
);
const turnosSection = document.getElementById("turnos-section");
const currentRoundSpan = document.getElementById("current-round");
const currentPlayersSpan = document.getElementById("current-players");
const roundInfoTitle = document.getElementById("round-info");
const playersCountInfo = document.getElementById("players-count");
const scoreboardBody = document.querySelector("#scoreboard tbody");

const socket = new WebSocket("ws://localhost:8765");
socket.onopen = () => console.log("Conexão estabelecida com o WebSocket.");
socket.onmessage = (event) => handleWebSocketMessage(event.data);
socket.onerror = (error) => console.log("Erro no WebSocket:", error);
socket.onclose = () => console.log("Conexão encerrada.");

startBtn.addEventListener("click", startTournament);
nextRoundBtn.addEventListener("click", resetTournament);
statsBtn.addEventListener("click", showStatistics);
backToSetupBtn.addEventListener("click", backToSetup);

function handleWebSocketMessage(dataStr) {
  try {
    const data = JSON.parse(dataStr);
    lastData = data;
    if (!tournamentStarted) {
      updateInitialView(data);
    } else if (!tournamentEnded) {
      updateTournamentView(data);
    }
  } catch (e) {
    console.error("Erro ao processar mensagem do WebSocket:", e);
  }
}

function startTournament() {
  if (!lastData) return;
  tournamentStarted = true;
  setupSection.classList.add("hidden");
  scoreboardSection.classList.add("hidden");
  tournamentSection.classList.remove("hidden");
  roundStartTime = Date.now();
  startCountdown();
  startPlayingInterval();
  updateTournamentView(lastData);
}

function resetTournament() {
  tournamentStarted = false;
  tournamentEnded = false;
  totalTime = 1800;
  playingTables = {};
  turnosSection.classList.add("hidden");
  tournamentSection.classList.add("hidden");
  scoreboardSection.classList.add("hidden");
  setupSection.classList.remove("hidden");
  initialTablesContainer.innerHTML = "";
  if (countdownInterval) clearInterval(countdownInterval);
  if (playingInterval) clearInterval(playingInterval);
  countdownInterval = null;
  playingInterval = null;

  playerStats = {};
  processedMatches = {};

  if (lastData) {
    updateInitialView(lastData);
  }
  // Scoreboard só é atualizado ao clicar em estatísticas agora
}

function showStatistics() {
  setupSection.classList.add("hidden");
  tournamentSection.classList.add("hidden");
  scoreboardSection.classList.remove("hidden");
  renderScoreboard();
}

function backToSetup() {
  scoreboardSection.classList.add("hidden");
  tournamentSection.classList.add("hidden");
  setupSection.classList.remove("hidden");
}

function startCountdown() {
  updateTimerDisplay();
  countdownInterval = setInterval(() => {
    totalTime--;
    if (totalTime <= 0) {
      clearInterval(countdownInterval);
      totalTime = 0;
      updateTimerDisplay();
      endTournamentPhase();
    } else {
      updateTimerDisplay();
    }
  }, 1000);
}

function updateTimerDisplay() {
  countdownTimer.textContent = formatTime(totalTime);
}

function startPlayingInterval() {
  if (playingInterval) clearInterval(playingInterval);
  playingInterval = setInterval(() => {
    updateAllPlayingTimes();
  }, 1000);
}

function endTournamentPhase() {
  tournamentEnded = true;
  turnosSection.classList.remove("hidden");
  if (playingInterval) clearInterval(playingInterval);
  const playingOnly = filterPlayingTables(lastData);
  renderTables(playingOnly, true);
}

function endRoundEarly() {
  tournamentEnded = true;
  turnosSection.classList.add("hidden");
  if (playingInterval) clearInterval(playingInterval);
  const { tablesData } = extractLatestRoundData(lastData);
  renderTables(tablesData, false);
}

function updateInitialView(data) {
  const { tablesData, latestRound } = extractLatestRoundData(data);
  const playerCount = Object.keys(data?.players ?? {}).length;
  roundInfoTitle.textContent = `Rodada Atual: ${latestRound}`;
  playersCountInfo.textContent = `Número de Jogadores: ${playerCount}`;
  renderInitialTables(tablesData);
}

function updateTournamentView(data) {
  if (!data?.round) return;
  const { tablesData, latestRound } = extractLatestRoundData(data);
  const playerCount = Object.keys(data?.players ?? {}).length;
  updateUIRoundInfo(latestRound, playerCount);
  processAndRenderData(data, tablesData);
}

function updateUIRoundInfo(latestRound, playerCount) {
  currentRoundSpan.textContent = `Rodada: ${latestRound}`;
  currentPlayersSpan.textContent = `Jogadores: ${playerCount}`;
}

function processAndRenderData(data, tablesData) {
  updatePlayerStats(data);
  const hasPlaying = renderTables(tablesData, false);
  checkEarlyEnd(hasPlaying);
}

function checkEarlyEnd(hasPlaying) {
  if (!hasPlaying && !tournamentEnded && totalTime > 0) {
    endRoundEarly();
  }
}

function extractLatestRoundData(data) {
  if (!data?.round) return { tablesData: {}, latestRound: 0 };
  const rounds = data.round;
  const roundNumbers = Object.keys(rounds).map((r) => parseInt(r, 10));
  const latestRound = Math.max(...roundNumbers);
  const divisions = rounds[latestRound];
  const divisionKeys = Object.keys(divisions);
  const currentDivision = divisionKeys[0];
  const tablesData = divisions[currentDivision].table;
  return { tablesData, latestRound };
}

function filterPlayingTables(data) {
  const { tablesData } = extractLatestRoundData(data);
  const playingOnly = {};
  for (let t in tablesData) {
    if (tablesData[t].outcome === "Jogando") {
      playingOnly[t] = tablesData[t];
    }
  }
  return playingOnly;
}

function renderInitialTables(tablesData) {
  initialTablesContainer.innerHTML = "";
  const tableEntries = Object.entries(tablesData ?? {}).slice(0, 20);
  tableEntries.forEach(([t, tableInfo]) => {
    const card = createTableCard(t, tableInfo, false, false);
    initialTablesContainer.appendChild(card);
  });
}

function renderTables(tablesData, showOnlyPlaying) {
  tablesContainer.innerHTML = "";
  const tableEntries = Object.entries(tablesData ?? {}).slice(0, 20);

  const filteredEntries = showOnlyPlaying
    ? tableEntries.filter(([_, tInfo]) => tInfo.outcome === "Jogando")
    : tableEntries;

  let hasPlaying = false;
  filteredEntries.forEach(([t, tableInfo]) => {
    if (tableInfo.outcome === "Jogando") hasPlaying = true;
    const card = createTableCard(
      t,
      tableInfo,
      true,
      tableInfo.outcome !== "Jogando"
    );
    tablesContainer.appendChild(card);
  });
  return hasPlaying;
}

function createTableCard(tableId, tableInfo, showStatus, ended) {
  const { player1, player2, outcome } = tableInfo;
  const card = document.createElement("div");
  card.classList.add("table-card");

  const h2 = document.createElement("h2");
  h2.textContent = `Mesa ${tableId}`;
  card.appendChild(h2);

  const playersP = document.createElement("p");
  playersP.classList.add("players");
  playersP.textContent = `${player1} vs ${player2}`;
  card.appendChild(playersP);

  if (tournamentStarted && showStatus) {
    const statusP = document.createElement("p");
    statusP.classList.add("status");
    statusP.textContent = `Status: ${outcome}`;
    card.appendChild(statusP);

    if (outcome === "Jogando") {
      ensurePlayingTable(tableId);
      const elapsedTimeP = document.createElement("p");
      elapsedTimeP.classList.add("elapsed-time");
      elapsedTimeP.setAttribute("data-table", tableId);
      elapsedTimeP.textContent = "Tempo jogado: 00:00";
      card.appendChild(elapsedTimeP);
    } else {
      if (playingTables[tableId] && !playingTables[tableId].endTime) {
        playingTables[tableId].endTime = Date.now();
      }
      if (playingTables[tableId] && ended) {
        const duration = calculateMatchDuration(playingTables[tableId]);
        const durationP = document.createElement("p");
        durationP.classList.add("elapsed-time");
        durationP.textContent = `Duração da partida: ${formatTime(duration)}`;
        card.appendChild(durationP);
      }
    }
  }

  return card;
}

function ensurePlayingTable(tableId) {
  if (!playingTables[tableId]) {
    playingTables[tableId] = { startTime: roundStartTime, endTime: null };
  }
}

function updateAllPlayingTimes() {
  const elapsedElements = tablesContainer.querySelectorAll(
    ".elapsed-time[data-table]"
  );
  elapsedElements.forEach((el) => {
    const tableId = el.getAttribute("data-table");
    updateElapsedTimeForTable(tableId, el);
  });
}

function updateElapsedTimeForTable(tableId, element) {
  const tableData = playingTables[tableId];
  if (!tableData?.startTime) return;
  const elapsedSeconds = Math.floor((Date.now() - tableData.startTime) / 1000);
  element.textContent = `Tempo jogado: ${formatTime(elapsedSeconds)}`;
}

function calculateMatchDuration(tableData) {
  if (!tableData?.startTime || !tableData?.endTime) return 0;
  return Math.floor((tableData.endTime - tableData.startTime) / 1000);
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  const mm = m < 10 ? `0${m}` : m;
  const ss = s < 10 ? `0${s}` : s;
  return `${mm}:${ss}`;
}

function updatePlayerStats(data) {
  const { tablesData, latestRound } = extractLatestRoundData(data);
  if (!tablesData) return;

  for (const [tableId, table] of Object.entries(tablesData)) {
    processTableResult(table, latestRound, tableId);
  }
}

function processTableResult(table, latestRound, tableId) {
  const { player1: p1, player2: p2, outcome } = table;
  initializePlayerIfNeeded(p1);
  initializePlayerIfNeeded(p2);

  if (outcome === "Jogando") return;

  const matchId = `${latestRound}#${tableId}`;
  if (processedMatches[matchId] === outcome) return;

  applyOutcomeToStats(outcome, p1, p2);
  processedMatches[matchId] = outcome;
}

function applyOutcomeToStats(outcome, p1, p2) {
  if (outcome.startsWith("Vitória de")) {
    applyVictoryOutcome(outcome, p1, p2);
  } else if (outcome === "Empate") {
    applyDrawOutcome(p1, p2);
  } else if (outcome === "Derrota dupla") {
    applyDoubleLossOutcome(p1, p2);
  }
}

function applyVictoryOutcome(outcome, p1, p2) {
  const winnerName = outcome.replace("Vitória de", "").trim();
  const winner = winnerName === p1 ? p1 : p2;
  const loser = winner === p1 ? p2 : p1;
  playerStats[winner].wins++;
  playerStats[winner].outcomes.unshift("V");
  playerStats[loser].losses++;
  playerStats[loser].outcomes.unshift("D");
  limitStreakSize(p1, p2);
}

function applyDrawOutcome(p1, p2) {
  playerStats[p1].draws++;
  playerStats[p1].outcomes.unshift("E");
  playerStats[p2].draws++;
  playerStats[p2].outcomes.unshift("E");
  limitStreakSize(p1, p2);
}

function applyDoubleLossOutcome(p1, p2) {
  playerStats[p1].losses++;
  playerStats[p1].outcomes.unshift("D");
  playerStats[p2].losses++;
  playerStats[p2].outcomes.unshift("D");
  limitStreakSize(p1, p2);
}

function limitStreakSize(p1, p2) {
  playerStats[p1].outcomes = playerStats[p1].outcomes.slice(0, 5);
  playerStats[p2].outcomes = playerStats[p2].outcomes.slice(0, 5);
}

function initializePlayerIfNeeded(playerName) {
  if (!playerStats[playerName]) {
    playerStats[playerName] = {
      name: playerName,
      wins: 0,
      draws: 0,
      losses: 0,
      outcomes: [],
    };
  }
}

function renderScoreboard() {
  scoreboardBody.innerHTML = "";
  const statsArray = Object.values(playerStats);

  statsArray.sort((a, b) => {
    if (b.wins !== a.wins) return b.wins - a.wins;
    return a.losses - b.losses;
  });

  statsArray.forEach((player) => {
    const tr = document.createElement("tr");

    const nameTd = document.createElement("td");
    nameTd.textContent = player.name;

    const wTd = document.createElement("td");
    wTd.textContent = player.wins;

    const dTd = document.createElement("td");
    dTd.textContent = player.draws;

    const lTd = document.createElement("td");
    lTd.textContent = player.losses;

    const streakTd = document.createElement("td");
    streakTd.textContent = player.outcomes.join(" / ");

    tr.appendChild(nameTd);
    tr.appendChild(wTd);
    tr.appendChild(dTd);
    tr.appendChild(lTd);
    tr.appendChild(streakTd);

    scoreboardBody.appendChild(tr);
  });

  scoreboardSection.classList.remove("hidden");
}
