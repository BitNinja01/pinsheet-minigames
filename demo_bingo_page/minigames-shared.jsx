// PinSheet Minigames — Shared Data, Styles & Components

/* ── Data ──────────────────────────────────────────── */

const MG_GAME = {
  name: "Thursday Night Crew",
  type: "Par Bingo",
  buyIn: 20,
  playerCount: 6,
  pot: 120,
  round: 3,
  daysLeft: 14,
};

const MG_PLAYERS = [
  { name: "Marcus Chen", initials: "MC", pars: 10, birdies: 4 },
  { name: "Sam O'Brien", initials: "SO", pars: 9, birdies: 3 },
  { name: "Jordan Park", initials: "JP", pars: 8, birdies: 3, you: true },
  { name: "Taylor Kim", initials: "TK", pars: 7, birdies: 1 },
  { name: "Alex Rivera", initials: "AR", pars: 6, birdies: 2 },
  { name: "Chris Walsh", initials: "CW", pars: 5, birdies: 2 },
];

const MG_HOLE_PARS = [4,4,3,5,4,3,4,5,4, 4,3,5,4,4,3,4,5,4];

const MG_CARD = {};
[
  [1,1,0],[2,0,0],[3,1,1],[4,0,0],[5,1,0],[6,0,0],
  [7,1,1],[8,0,0],[9,1,0],[10,1,0],[11,0,0],[12,0,0],
  [13,0,0],[14,1,1],[15,0,0],[16,1,0],[17,0,0],[18,0,0]
].forEach(([h,p,b]) => { MG_CARD[h] = { par: !!p, birdie: !!b }; });

const MG_MY_PARS = Object.values(MG_CARD).filter(c => c.par).length;
const MG_MY_BIRDS = Object.values(MG_CARD).filter(c => c.birdie).length;

/* ── Styles ────────────────────────────────────────── */

const MG_STYLES = `
.mg {
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
.mg *, .mg *::before, .mg *::after { box-sizing: border-box; }

/* Sidebar */
.mg .side { border-right: 1px solid var(--rule); padding: 28px 24px; display: flex; flex-direction: column; gap: 22px; }
.mg .logo { font-size: 22px; font-weight: 500; letter-spacing: -0.03em; display: flex; align-items: baseline; gap: 6px; }
.mg .logo::before { content: ""; width: 8px; height: 8px; background: var(--accent); border-radius: 50%; display: inline-block; align-self: center; }
.mg .side-nav { display: flex; flex-direction: column; gap: 10px; font-size: 13px; }
.mg .side-nav span { color: var(--ink-2); padding-left: 14px; border-left: 1px solid transparent; display: block; }
.mg .side-nav span.active { color: var(--ink); border-left-color: var(--accent); font-weight: 500; }

/* Typography */
.mg .ey { font: 500 10px/1.45 'IBM Plex Mono', monospace; letter-spacing: 0.16em; text-transform: uppercase; color: var(--ink-3); }
.mg h1 { font: 400 32px/1.05 'IBM Plex Mono', monospace; margin: 4px 0 0; letter-spacing: -0.025em; }
.mg h1 em { font-style: italic; color: var(--accent); font-weight: 400; }

/* Chips & buttons */
.mg .chip { display: inline-flex; padding: 5px 10px; font: 500 10px/1 'IBM Plex Mono', monospace; letter-spacing: 0.12em; text-transform: uppercase; border: 1px solid var(--rule); color: var(--ink-2); }
.mg .chip.on { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.mg .chip.mint { border-color: var(--accent); color: var(--accent); }
.mg .btn { font: 500 11px/1 'IBM Plex Mono', monospace; padding: 8px 16px; border: 1px solid var(--ink); background: var(--ink); color: var(--paper); letter-spacing: 0.06em; text-transform: uppercase; }
.mg .btn.ghost { background: transparent; color: var(--ink); }

/* Bingo grid */
.mg .bingo { display: grid; grid-template-columns: repeat(3, 1fr); border-top: 1px solid var(--rule); border-left: 1px solid var(--rule); }
.mg .bcell { border-right: 1px solid var(--rule); border-bottom: 1px solid var(--rule); padding: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; aspect-ratio: 1; }
.mg .bcell .hole { font-size: 22px; color: var(--ink-2); display: flex; flex-direction: column; align-items: center; gap: 2px; }
.mg .bcell .hole .pl { font-size: 10px; color: var(--ink-3); letter-spacing: 0.08em; }
.mg .bcell .checks { display: flex; gap: 6px; width: 100%; }
.mg .bx { flex: 1; height: 28px; border: 1px solid var(--rule); display: flex; align-items: center; justify-content: center; font: 500 9px/1 'IBM Plex Mono', monospace; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-3); }
.mg .bx.p { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.mg .bx.b { background: var(--accent); color: #131312; border-color: var(--accent); }

/* Stat strip */
.mg .strip { display: grid; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); padding: 14px 0; }
.mg .strip > div { padding: 0 24px; border-right: 1px solid var(--rule); }
.mg .strip > div:last-child { border-right: none; }
.mg .sv { font: 300 38px/1 'IBM Plex Mono', monospace; letter-spacing: -0.03em; margin-top: 4px; }

/* Table */
.mg .tbl { width: 100%; border-collapse: collapse; }
.mg .tbl th { font: 500 10px/1 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.14em; color: var(--ink-3); text-align: left; padding: 0 12px 10px; border-bottom: 1px solid var(--ink); }
.mg .tbl th.r { text-align: right; }
.mg .tbl td { padding: 10px 12px; border-bottom: 1px solid var(--rule); font-size: 13px; vertical-align: middle; }
.mg .tbl td.r { text-align: right; }

/* Hero number */
.mg .hero-num { font-family: 'Barlow Condensed', 'Oswald', sans-serif; font-weight: 200; line-height: 0.85; letter-spacing: -0.04em; }

/* Progress bar */
.mg .pbar { height: 3px; background: var(--rule); }
.mg .pfill { height: 100%; background: var(--accent); }
`;

/* ── Components ────────────────────────────────────── */

function MGSidebar() {
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

function MGBingoCard({ data, style }) {
  const pars = MG_HOLE_PARS;
  return (
    <div className="bingo" style={style}>
      {Array.from({ length: 18 }, (_, i) => {
        const h = i + 1;
        const s = data[h] || { par: false, birdie: false };
        const complete = s.par && s.birdie;
        const divider = h >= 7 && h <= 9;
        return (
          <div key={h} className="bcell" style={{
            ...(complete ? { background: 'var(--accent-dim)' } : {}),
            ...(divider ? { borderBottomColor: 'var(--ink)' } : {}),
          }}>
            <div className="hole">
              <span>{String(h).padStart(2, '0')}</span>
              <span className="pl">p{pars[i]}</span>
            </div>
            <div className="checks">
              <div className={'bx' + (s.par ? ' p' : '')}>par</div>
              <div className={'bx' + (s.birdie ? ' b' : '')}>brd</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, {
  MG_GAME, MG_PLAYERS, MG_CARD, MG_HOLE_PARS,
  MG_MY_PARS, MG_MY_BIRDS, MG_STYLES,
  MGSidebar, MGBingoCard,
});
