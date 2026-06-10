/* ═══════════════════════════════════════════════════════
   D · COMBINED
   A's left info rail (pot, your card, exposure, status)
   + C's bingo card + C's race leaderboard.
   ═══════════════════════════════════════════════════════ */

function LayoutD() {
  return (
    <div className="mg">
      <MGSidebar />
      <div style={{ padding: '28px 48px 32px', display: 'flex', flexDirection: 'column', gap: 24, overflow: 'hidden' }}>

        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingBottom: 12, borderBottom: '1px solid var(--rule)' }}>
          <div>
            <div className="ey">Par Bingo · Minigames</div>
            <h1><em>Thursday Night Crew</em></h1>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <span className="btn ghost">← Games</span>
            <span className="btn ghost">Rules</span>
            <span className="btn">Log round</span>
          </div>
        </div>

        {/* 3-column: info rail | bingo card | the race */}
        <div style={{ display: 'grid', gridTemplateColumns: '220px 450px 1fr', gap: 36, flex: 1, minHeight: 0 }}>

          {/* ── Left: info rail (from A) ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
            <div>
              <div className="ey">The pot</div>
              <div className="hero-num" style={{ fontSize: 96, marginTop: 8 }}>
                <span style={{ color: 'var(--ink-3)' }}>$</span>120
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 8 }}>
                6 players · $20 buy-in
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--rule)', paddingTop: 20 }}>
              <div className="ey">Your card</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 12 }}>
                <div>
                  <div style={{ fontSize: 32, fontWeight: 300, letterSpacing: '-0.03em' }}>
                    {MG_MY_PARS}<span style={{ fontSize: 14, color: 'var(--ink-3)' }}>/18</span>
                  </div>
                  <div className="ey" style={{ marginTop: 4 }}>Pars</div>
                </div>
                <div>
                  <div style={{ fontSize: 32, fontWeight: 300, letterSpacing: '-0.03em', color: 'var(--accent)' }}>
                    {MG_MY_BIRDS}<span style={{ fontSize: 14, color: 'var(--ink-3)' }}>/18</span>
                  </div>
                  <div className="ey" style={{ marginTop: 4 }}>Birdies</div>
                </div>
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--rule)', paddingTop: 20 }}>
              <div className="ey">Exposure</div>
              <div style={{ fontSize: 24, fontWeight: 300, marginTop: 8, letterSpacing: '-0.02em' }}>
                <span style={{ color: 'var(--ink-3)' }}>$</span>38
                <span style={{ fontSize: 12, color: 'var(--ink-3)', marginLeft: 6 }}>max</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 4 }}>
                $20 buy-in + $18 birdie risk
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--rule)', paddingTop: 20 }}>
              <div className="ey">Status</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                <span className="chip mint">In progress</span>
                <span className="chip">Round 3</span>
                <span className="chip">14d left</span>
              </div>
            </div>
          </div>

          {/* ── Center: bingo card (from C) ── */}
          <div>
            <div className="ey" style={{ marginBottom: 10 }}>Your bingo card · holes 1–18</div>
            <MGBingoCard data={MG_CARD} />
          </div>

          {/* ── Right: the race (from C) ── */}
          <div style={{ borderLeft: '1px solid var(--rule)', paddingLeft: 32, display: 'flex', flexDirection: 'column' }}>
            <div className="ey" style={{ marginBottom: 20 }}>The race</div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {MG_PLAYERS.map((p, i) => {
                const total = p.pars + p.birdies;
                return (
                  <div key={p.initials} style={{
                    display: 'grid', gridTemplateColumns: '24px 1fr 1.4fr 50px',
                    gap: 14, alignItems: 'center',
                    padding: '14px 0', borderBottom: '1px solid var(--rule)',
                  }}>
                    <span style={{
                      fontSize: 22, fontWeight: 200,
                      fontFamily: "'Barlow Condensed', sans-serif",
                      color: 'var(--ink-3)',
                    }}>{i + 1}</span>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: p.you ? 500 : 400, color: p.you ? 'var(--ink)' : 'var(--ink-2)' }}>
                        {p.name}
                        {p.you && <span style={{ color: 'var(--accent)', fontSize: 9, marginLeft: 6, letterSpacing: '0.14em', textTransform: 'uppercase' }}>you</span>}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--ink-3)', marginTop: 2 }}>
                        {p.pars}p · {p.birdies}b
                      </div>
                    </div>
                    <div style={{ height: 18, background: 'var(--paper-2)', border: '1px solid var(--rule)', display: 'flex', overflow: 'hidden' }}>
                      <div style={{
                        width: `${(p.pars / 36) * 100}%`,
                        background: p.you ? 'var(--ink)' : 'var(--ink-3)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {p.pars >= 5 && <span style={{ fontSize: 8, color: 'var(--paper)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>{p.pars}p</span>}
                      </div>
                      <div style={{
                        width: `${(p.birdies / 36) * 100}%`,
                        background: 'var(--accent)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                      }}>
                        {p.birdies >= 3 && <span style={{ fontSize: 8, color: '#131312', letterSpacing: '0.08em' }}>{p.birdies}b</span>}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right', fontSize: 16, fontWeight: 300, letterSpacing: '-0.02em' }}>
                      {total}<span style={{ fontSize: 11, color: 'var(--ink-3)' }}>/36</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Rules box */}
            <div style={{ marginTop: 'auto', padding: 20, background: 'var(--paper-2)', border: '1px solid var(--rule)' }}>
              <div className="ey" style={{ marginBottom: 8 }}>How it works</div>
              <div style={{ fontSize: 12, color: 'var(--ink-2)', lineHeight: 1.6 }}>
                Play rounds and cross off pars and birdies as you earn them. First to fill the card wins the $120 pot. Each birdie earns $1 from every other player. Max exposure per player: $38.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { LayoutD });
