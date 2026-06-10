// PinSheet Minigames — Main Menu / Hub

/* ── Active Games Data ─────────────────────────────── */

const ACTIVE_GAMES = [
  {
    id: 1,
    type: "Par Bingo",
    name: "Thursday Night Crew",
    players: 6,
    pot: 120,
    buyIn: 20,
    round: 3,
    daysLeft: 14,
    yourRank: 3,
    yourProgress: { pars: 8, birdies: 3, total: 11, of: 36 },
    leaderProgress: { name: "Marcus Chen", initials: "MC", total: 14, of: 36 },
    status: "in-progress",
  },
  {
    id: 2,
    type: "Skins",
    name: "Weekend Warriors",
    players: 4,
    pot: 80,
    buyIn: 20,
    round: 5,
    daysLeft: 7,
    yourRank: 1,
    yourProgress: { skins: 6, value: 34 },
    leaderProgress: { name: "You", initials: "JP", total: 6 },
    status: "in-progress",
  },
  {
    id: 3,
    type: "Nassau",
    name: "Sunday Singles",
    players: 2,
    pot: 30,
    buyIn: 15,
    round: 1,
    daysLeft: 3,
    yourRank: 2,
    yourProgress: { front: "1 dn", back: "—", overall: "1 dn" },
    leaderProgress: { name: "Sam O'Brien", initials: "SO" },
    status: "in-progress",
  },
];

const FINISHED_GAMES = [
  {
    id: 10,
    type: "Closest to Pin",
    name: "Par 3 Shootout",
    players: 8,
    pot: 40,
    result: "+$12",
    resultPositive: true,
    date: "May 28",
  },
  {
    id: 11,
    type: "Skins",
    name: "Spring Classic",
    players: 5,
    pot: 100,
    result: "−$20",
    resultPositive: false,
    date: "May 14",
  },
];

/* ── Available Game Types ──────────────────────────── */

const GAME_TYPES = [
  {
    id: "par-bingo",
    name: "Par Bingo",
    desc: "Cross off pars and birdies on your 18-hole card. First to fill it wins the pot.",
    players: "2–8",
    duration: "Multi-round",
    complexity: "Simple",
  },
  {
    id: "skins",
    name: "Skins",
    desc: "Lowest score on each hole wins that skin. Ties carry over to the next hole.",
    players: "2–6",
    duration: "Per round",
    complexity: "Simple",
  },
  {
    id: "nassau",
    name: "Nassau",
    desc: "Three bets in one — front nine, back nine, and overall. Press to double the stakes.",
    players: "2–4",
    duration: "Per round",
    complexity: "Moderate",
  },
  {
    id: "closest-pin",
    name: "Closest to Pin",
    desc: "Par 3 contest. Closest tee shot to the pin on designated holes wins.",
    players: "2–12",
    duration: "Per round",
    complexity: "Simple",
  },
  {
    id: "wolf",
    name: "Wolf",
    desc: "Rotating picker chooses a partner or goes lone wolf each hole. High risk, high reward.",
    players: "4",
    duration: "Per round",
    complexity: "Advanced",
  },
  {
    id: "stroke-match",
    name: "Stroke Play Showdown",
    desc: "Head-to-head net stroke play over a set number of rounds. Lowest cumulative wins.",
    players: "2–4",
    duration: "Multi-round",
    complexity: "Simple",
  },
];

/* ── Styles ────────────────────────────────────────── */

const MG_MENU_STYLES = `
  .mg-menu {
    --paper: #131312; --paper-2: #1c1c1a;
    --ink: #ecebe6; --ink-2: #a8a59d; --ink-3: #6c685f;
    --rule: #2a2925; --accent: #5db49a;
    --accent-dim: rgba(93,180,154,0.16); --warn: #d96a6a;
    width: 1920px; height: 1080px; background: var(--paper); color: var(--ink);
    font-family: 'IBM Plex Mono', 'JetBrains Mono', monospace;
    font-size: 13px; line-height: 1.45; font-variant-numeric: tabular-nums;
    display: grid; grid-template-columns: 200px 1fr;
    overflow: hidden; box-sizing: border-box;
  }
  .mg-menu *, .mg-menu *::before, .mg-menu *::after { box-sizing: border-box; }

  /* Sidebar */
  .mg-menu .side { border-right: 1px solid var(--rule); padding: 28px 24px; display: flex; flex-direction: column; gap: 22px; }
  .mg-menu .logo { font-size: 22px; font-weight: 500; letter-spacing: -0.03em; display: flex; align-items: baseline; gap: 6px; }
  .mg-menu .logo::before { content: ""; width: 8px; height: 8px; background: var(--accent); border-radius: 50%; display: inline-block; align-self: center; }
  .mg-menu .side-nav { display: flex; flex-direction: column; gap: 10px; font-size: 13px; }
  .mg-menu .side-nav span { color: var(--ink-2); padding-left: 14px; border-left: 1px solid transparent; display: block; cursor: default; }
  .mg-menu .side-nav span.active { color: var(--ink); border-left-color: var(--accent); font-weight: 500; }

  /* Typography */
  .mg-menu .ey { font: 500 10px/1.45 'IBM Plex Mono', monospace; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-3); }
  .mg-menu h1 { font: 400 32px/1.05 'IBM Plex Mono', monospace; margin: 4px 0 0; letter-spacing: -0.025em; }
  .mg-menu h1 em { font-style: italic; color: var(--accent); font-weight: 400; }
  .mg-menu h2 { font: 400 18px/1.2 'IBM Plex Mono', monospace; margin: 0; }

  /* Chips & buttons */
  .mg-menu .chip { display: inline-flex; padding: 5px 10px; font: 500 10px/1 'IBM Plex Mono', monospace; letter-spacing: 0.12em; text-transform: uppercase; border: 1px solid var(--rule); color: var(--ink-2); }
  .mg-menu .chip.on { background: var(--ink); color: var(--paper); border-color: var(--ink); }
  .mg-menu .chip.mint { border-color: var(--accent); color: var(--accent); }
  .mg-menu .btn { font: 500 11px/1 'IBM Plex Mono', monospace; padding: 8px 16px; border: 1px solid var(--ink); background: var(--ink); color: var(--paper); letter-spacing: 0.06em; text-transform: uppercase; cursor: default; }
  .mg-menu .btn.ghost { background: transparent; color: var(--ink); }

  /* Hero number */
  .mg-menu .hero-num { font-family: 'Barlow Condensed', 'Oswald', sans-serif; font-weight: 200; line-height: 0.85; letter-spacing: -0.04em; }

  /* Progress bar */
  .mg-menu .pbar { height: 3px; background: var(--rule); width: 100%; }
  .mg-menu .pfill { height: 100%; background: var(--accent); }

  /* Active game card */
  .mg-menu .game-card {
    background: var(--paper-2);
    border: 1px solid var(--rule);
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    cursor: default;
    transition: border-color 200ms;
  }
  .mg-menu .game-card:hover {
    border-color: var(--ink-3);
  }

  /* Available game type row */
  .mg-menu .type-row {
    display: grid;
    grid-template-columns: 200px 1fr 80px 100px 100px 90px;
    align-items: center;
    gap: 16px;
    padding: 16px 0;
    border-bottom: 1px solid var(--rule);
  }
  .mg-menu .type-row:last-child { border-bottom: none; }


`;

/* ── Components ────────────────────────────────────── */

function MenuSidebar() {
  return (
    <div className="side">
      <div className="logo">PinSheet</div>
      <div>
        <div className="ey" style={{ marginBottom: 6 }}>Player</div>
        <div style={{ fontSize: 20, lineHeight: 1.1 }}>Jordan Park</div>
        <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 2 }}>pac.coast.u / '27</div>
      </div>
      <div className="side-nav">
        <span>Dashboard</span>
        <span>Rounds</span>
        <span>Stats</span>
        <span>Goals</span>
        <span className="active">Minigames</span>
        <span>Courses</span>
        <span>Settings</span>
      </div>
    </div>
  );
}

function ActiveGameCard({ game }) {
  const progressPct = game.type === "Par Bingo"
    ? (game.yourProgress.total / game.yourProgress.of) * 100
    : game.type === "Skins"
    ? (game.round / 8) * 100
    : (game.round / 3) * 100;

  const leaderPct = game.type === "Par Bingo"
    ? (game.leaderProgress.total / game.leaderProgress.of) * 100
    : progressPct;

  return (
    <div className="game-card">
      {/* Top: type + status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="ey">{game.type}</div>
        <div style={{ display: 'flex', gap: 6 }}>
          <span className="chip mint">{game.daysLeft}d left</span>
          <span className="chip">Rd {game.round}</span>
        </div>
      </div>

      {/* Name + players */}
      <div>
        <h2>{game.name}</h2>
        <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 4 }}>
          {game.players} players · ${game.buyIn} buy-in
        </div>
      </div>

      {/* Pot + rank */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
        <div>
          <div className="ey" style={{ marginBottom: 4 }}>Pot</div>
          <div className="hero-num" style={{ fontSize: 48 }}>
            <span style={{ color: 'var(--ink-3)' }}>$</span>{game.pot}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="ey" style={{ marginBottom: 4 }}>Your rank</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'flex-end', gap: 4 }}>
            <span className="hero-num" style={{
              fontSize: 48,
              color: game.yourRank === 1 ? 'var(--accent)' : 'var(--ink)',
            }}>{game.yourRank}</span>
            <span style={{ fontSize: 12, color: 'var(--ink-3)' }}>/{game.players}</span>
          </div>
        </div>
      </div>

      {/* Progress */}
      <div>
        {game.type === "Par Bingo" && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--ink-2)' }}>
                You · {game.yourProgress.pars}p {game.yourProgress.birdies}b
              </span>
              <span style={{ color: 'var(--ink-3)' }}>{game.yourProgress.total}/{game.yourProgress.of}</span>
            </div>
            <div className="pbar">
              <div className="pfill" style={{ width: `${progressPct}%` }}></div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--ink-3)' }}>
                Leader · {game.leaderProgress.name}
              </span>
              <span style={{ color: 'var(--ink-3)' }}>{game.leaderProgress.total}/{game.leaderProgress.of}</span>
            </div>
            <div className="pbar">
              <div className="pfill" style={{ width: `${leaderPct}%`, background: 'var(--ink-3)' }}></div>
            </div>
          </div>
        )}

        {game.type === "Skins" && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11 }}>
              <span style={{ color: 'var(--ink-2)' }}>
                {game.yourProgress.skins} skins won
              </span>
              <span style={{ color: 'var(--accent)' }}>${game.yourProgress.value}</span>
            </div>
            <div className="pbar">
              <div className="pfill" style={{ width: `${progressPct}%` }}></div>
            </div>
            <div style={{ fontSize: 11, color: 'var(--ink-3)' }}>
              Round {game.round} of 8
            </div>
          </div>
        )}

        {game.type === "Nassau" && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {[
              { label: "Front", val: game.yourProgress.front },
              { label: "Back", val: game.yourProgress.back },
              { label: "Overall", val: game.yourProgress.overall },
            ].map(s => (
              <div key={s.label}>
                <div className="ey" style={{ marginBottom: 4 }}>{s.label}</div>
                <div style={{
                  fontSize: 14,
                  fontWeight: 500,
                  color: s.val === "—" ? 'var(--ink-3)' : s.val.includes("dn") ? 'var(--warn)' : 'var(--accent)',
                }}>{s.val}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function GameTypeRow({ game, isLast }) {
  return (
    <div className="type-row" style={isLast ? { borderBottom: 'none' } : {}}>
      <div>
        <div style={{ fontSize: 14, fontWeight: 500 }}>{game.name}</div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--ink-2)', lineHeight: 1.5 }}>
        {game.desc}
      </div>
      <div style={{ fontSize: 11, color: 'var(--ink-3)', textAlign: 'center' }}>
        {game.players}
      </div>
      <div style={{ fontSize: 11, color: 'var(--ink-3)', textAlign: 'center' }}>
        {game.duration}
      </div>
      <div style={{ textAlign: 'center' }}>
        <span className="chip" style={{ fontSize: 9 }}>{game.complexity}</span>
      </div>
      <div style={{ textAlign: 'right' }}>
        <span className="btn" style={{ fontSize: 10, padding: '6px 12px' }}>Create</span>
      </div>
    </div>
  );
}

/* ── Main Layout ──────────────────────────────────── */

function MinigamesMenu() {
  return (
    <div className="mg-menu">
      <style>{MG_MENU_STYLES}</style>
      <MenuSidebar />
      <div style={{ padding: '28px 48px 32px', display: 'flex', flexDirection: 'column', gap: 0, overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingBottom: 12, borderBottom: '1px solid var(--rule)' }}>
          <div>
            <div className="ey">Games · Hub</div>
            <h1><em>Minigames</em></h1>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="btn ghost">History</span>
            <span className="btn">+ New game</span>
          </div>
        </div>

        {/* Scrollable content */}
        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 36, paddingTop: 24 }}>

          {/* ── Active Games ── */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <div className="ey">Active games</div>
                <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>{ACTIVE_GAMES.length}</span>
                <span style={{ fontSize: 11, color: 'var(--ink-2)', marginLeft: 6, cursor: 'default' }}>See all →</span>
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <span className="chip on">All</span>
                <span className="chip">Par Bingo</span>
                <span className="chip">Skins</span>
                <span className="chip">Nassau</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 20 }}>
              {ACTIVE_GAMES.map(g => (
                <ActiveGameCard key={g.id} game={g} />
              ))}
            </div>
          </div>

          {/* ── Available Games Catalog ── */}
          <div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginBottom: 16 }}>
              <div className="ey">Available game types</div>
              <span style={{ fontSize: 11, color: 'var(--ink-3)' }}>{GAME_TYPES.length}</span>
            </div>

            {/* Table header */}
            <div style={{
              display: 'grid', gridTemplateColumns: '200px 1fr 80px 100px 100px 90px',
              gap: 16, paddingBottom: 10, borderBottom: '1px solid var(--ink)',
            }}>
              <div className="ey">Game</div>
              <div className="ey">Description</div>
              <div className="ey" style={{ textAlign: 'center' }}>Players</div>
              <div className="ey" style={{ textAlign: 'center' }}>Duration</div>
              <div className="ey" style={{ textAlign: 'center' }}>Level</div>
              <div></div>
            </div>

            {GAME_TYPES.map((g, i) => (
              <GameTypeRow key={g.id} game={g} isLast={i === GAME_TYPES.length - 1} />
            ))}
          </div>

          {/* ── Your Stats ── */}
          <div style={{ borderTop: '1px solid var(--rule)', paddingTop: 24 }}>
            <div className="ey" style={{ marginBottom: 16 }}>Minigame stats · All time</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', borderTop: '1px solid var(--rule)', borderBottom: '1px solid var(--rule)', padding: '16px 0' }}>
              {[
                { label: "Games played", value: "14" },
                { label: "Win rate", value: "36%", accent: false },
                { label: "Net earnings", value: "+$87", accent: true },
                { label: "Best finish", value: "1st", accent: true },
                { label: "Active streak", value: "3W", accent: true },
              ].map((s, i, a) => (
                <div key={s.label} style={{
                  padding: '0 24px',
                  borderRight: i < a.length - 1 ? '1px solid var(--rule)' : 'none',
                }}>
                  <div className="ey">{s.label}</div>
                  <div style={{
                    font: '300 38px/1 "IBM Plex Mono", monospace',
                    letterSpacing: '-0.03em',
                    marginTop: 4,
                    color: s.accent ? 'var(--accent)' : 'var(--ink)',
                  }}>{s.value}</div>
                </div>
              ))}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

Object.assign(window, { MinigamesMenu, MG_MENU_STYLES });
