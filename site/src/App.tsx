import { useMemo, useState } from 'react'

type PlayerMappingRow = {
  player_id: string
  nickname: string
  player_id_new?: string | null
}

type MatchRow = {
  year: number
  phase?: 'Regular' | 'Semi-Final' | 'Final'
  round_name: string
  table_name: string
  match_no: number
  e_player_id: string
  e_score: number
  e_penalty: number
  e_rank?: number
  s_player_id: string
  s_score: number
  s_penalty: number
  s_rank?: number
  w_player_id: string
  w_score: number
  w_penalty: number
  w_rank?: number
  n_player_id: string
  n_score: number
  n_penalty: number
  n_rank?: number
}

type DataFile = {
  generated_at: string
  years: number[]
  player_mapping: PlayerMappingRow[]
  matches: MatchRow[]
}

type PlayerStats = {
  player_id: string
  nickname: string
  matches: number
  total_score: number
  total_penalty: number
  first: number
  second: number
  third: number
  fourth: number
  tie_first: number
  tie_second: number
  tie_third: number
}

function formatNumber(n: number): string {
  const fixed = n.toFixed(2)
  if (fixed.endsWith('.00')) return fixed.slice(0, -3)
  if (fixed.endsWith('0')) return fixed.slice(0, -1)
  return fixed
}

function formatPercent(value: number): string {
  return `${value.toFixed(2)}%`
}

function percent(numerator: number, denominator: number): number {
  if (!denominator) return 0
  return (numerator / denominator) * 100
}

function formatRankCount(total: number, tied: number, splitTies: boolean): string {
  if (!splitTies) return String(total)
  if (tied <= 0) return String(total)
  return `${total - tied}+${tied}`
}

function computeRankPoints(s: PlayerStats): number {
  return (
    45 * (s.first - s.tie_first) +
    25 * s.tie_first +
    5 * (s.second - s.tie_second) +
    -5 * s.tie_second +
    -15 * (s.third - s.tie_third) +
    -25 * s.tie_third +
    -35 * s.fourth
  )
}

function computeRanks(e: number, s: number, w: number, n: number): [1 | 2 | 3 | 4, 1 | 2 | 3 | 4, 1 | 2 | 3 | 4, 1 | 2 | 3 | 4] {
  const scores = [e, s, w, n]
  const ranks = scores.map((si, i) => 1 + scores.reduce((acc, sj, j) => (i !== j && sj > si ? acc + 1 : acc), 0))
  return [ranks[0] as 1 | 2 | 3 | 4, ranks[1] as 1 | 2 | 3 | 4, ranks[2] as 1 | 2 | 3 | 4, ranks[3] as 1 | 2 | 3 | 4]
}

export default function App({ data }: { data: DataFile }) {
  const [selectedYears, setSelectedYears] = useState<number[]>([...data.years].sort((a, b) => b - a))
  const [selectedPhases, setSelectedPhases] = useState<Array<'Regular' | 'Semi-Final' | 'Final'>>([
    'Regular',
    'Semi-Final',
    'Final',
  ])
  const [splitTies, setSplitTies] = useState<boolean>(false)

  const canonicalIdByNewId = useMemo(() => {
    const m = new Map<string, string>()
    for (const row of data.player_mapping) {
      if (row.player_id_new && row.player_id_new.startsWith('#')) {
        m.set(row.player_id_new, row.player_id)
      }
    }
    return m
  }, [data.player_mapping])

  const nicknameByCanonicalId = useMemo(() => {
    const m = new Map<string, string>()
    for (const row of data.player_mapping) m.set(row.player_id, row.nickname)
    return m
  }, [data.player_mapping])

  function canonicalizeId(player_id: string): string {
    return canonicalIdByNewId.get(player_id) ?? player_id
  }

  const filteredMatches = useMemo(() => {
    const years = new Set(selectedYears)
    const phases = new Set(selectedPhases)
    return data.matches.filter((m) => years.has(m.year) && phases.has(m.phase ?? 'Regular'))
  }, [data.matches, selectedPhases, selectedYears])

  const stats = useMemo(() => {
    const acc = new Map<string, PlayerStats>()

    function ensure(player_id: string): PlayerStats {
      const existing = acc.get(player_id)
      if (existing) return existing
      const nickname = nicknameByCanonicalId.get(player_id) ?? player_id
      const fresh: PlayerStats = {
        player_id,
        nickname,
        matches: 0,
        total_score: 0,
        total_penalty: 0,
        first: 0,
        second: 0,
        third: 0,
        fourth: 0,
        tie_first: 0,
        tie_second: 0,
        tie_third: 0,
      }
      acc.set(player_id, fresh)
      return fresh
    }

    for (const match of filteredMatches) {
      const [eRank, sRank, wRank, nRank] =
        typeof match.e_rank === 'number' &&
        typeof match.s_rank === 'number' &&
        typeof match.w_rank === 'number' &&
        typeof match.n_rank === 'number'
          ? [match.e_rank, match.s_rank, match.w_rank, match.n_rank]
          : computeRanks(match.e_score, match.s_score, match.w_score, match.n_score)

      const seats = [
        { player_id: match.e_player_id, score: match.e_score, penalty: match.e_penalty, rank: eRank },
        { player_id: match.s_player_id, score: match.s_score, penalty: match.s_penalty, rank: sRank },
        { player_id: match.w_player_id, score: match.w_score, penalty: match.w_penalty, rank: wRank },
        { player_id: match.n_player_id, score: match.n_score, penalty: match.n_penalty, rank: nRank },
      ]

      const rankCounts = new Map<number, number>()
      for (const p of seats) rankCounts.set(p.rank, (rankCounts.get(p.rank) ?? 0) + 1)

      for (const p of seats) {
        if (!p.player_id?.startsWith('#')) continue
        const canonical_id = canonicalizeId(p.player_id)
        const s = ensure(canonical_id)
        s.matches += 1
        s.total_score += p.score
        s.total_penalty += p.penalty
        const tied = (rankCounts.get(p.rank) ?? 0) > 1
        if (p.rank === 1) {
          s.first += 1
          if (tied) s.tie_first += 1
        }
        if (p.rank === 2) {
          s.second += 1
          if (tied) s.tie_second += 1
        }
        if (p.rank === 3) {
          s.third += 1
          if (tied) s.tie_third += 1
        }
        if (p.rank === 4) s.fourth += 1
      }
    }

    const list = Array.from(acc.values())
    list.sort((a, b) => {
      if (b.total_score !== a.total_score) return b.total_score - a.total_score
      if (b.first !== a.first) return b.first - a.first
      if (b.second !== a.second) return b.second - a.second
      return a.player_id.localeCompare(b.player_id)
    })

    return list
  }, [canonicalIdByNewId, filteredMatches, nicknameByCanonicalId])

  const yearsSorted = useMemo(() => [...data.years].sort((a, b) => b - a), [data.years])

  return (
    <div className="page">
      <header className="header">
        <div className="title">香港鳳凰位戰通算成績</div>
        <div className="sub">
          Generated: {data.generated_at} · Matches: {filteredMatches.length}
        </div>
      </header>

      <section className="panel">
        <div className="panelTitle">按年份篩選</div>
        <div className="yearGrid">
          {yearsSorted.map((y) => {
            const checked = selectedYears.includes(y)
            return (
              <label key={y} className="yearChip">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedYears((prev) => [...prev, y].sort((a, b) => b - a))
                    } else {
                      setSelectedYears((prev) => prev.filter((x) => x !== y))
                    }
                  }}
                />
                <span>{y}</span>
              </label>
            )
          })}
        </div>
      </section>

      <section className="panel">
        <div className="panelTitle">按賽程篩選</div>
        <div className="yearGrid">
          {(['Regular', 'Semi-Final', 'Final'] as const).map((p) => {
            const checked = selectedPhases.includes(p)
            return (
              <label key={p} className="yearChip">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      setSelectedPhases((prev) => Array.from(new Set([...prev, p])))
                    } else {
                      setSelectedPhases((prev) => prev.filter((x) => x !== p))
                    }
                  }}
                />
                <span>{p}</span>
              </label>
            )
          })}
        </div>
      </section>

      <section className="panel">
        <div className="panelTitle">排行榜</div>
        <div className="yearGrid">
          <label className="yearChip">
            <input type="checkbox" checked={splitTies} onChange={(e) => setSplitTies(e.target.checked)} />
            <span>分開顯示同點名次</span>
          </label>
        </div>
        <div className="sub">順位點：1位 +45，2位 +5，3位 -15，4位 -35</div>
        <div className="tableWrap">
          <table className="table">
            <thead>
              <tr>
                <th>排名</th>
                <th>名稱</th>
                <th className="num">總分</th>
                <th className="num">順位點</th>
                <th className="num">素點</th>
                <th className="num">對局數</th>
                <th className="num">1位</th>
                <th className="num">2位</th>
                <th className="num">3位</th>
                <th className="num">4位</th>
                <th className="num">top率</th>
                <th className="num">連對率</th>
                <th className="num">避四率</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((s, idx) => (
                <tr key={s.player_id}>
                  <td>{idx + 1}</td>
                  <td>{s.nickname}</td>
                  <td className="num">{formatNumber(s.total_score)}</td>
                  <td className="num">{formatNumber(computeRankPoints(s))}</td>
                  <td className="num">{formatNumber(s.total_score - computeRankPoints(s) + s.total_penalty)}</td>
                  <td className="num">{s.matches}</td>
                  <td className="num">{formatRankCount(s.first, s.tie_first, splitTies)}</td>
                  <td className="num">{formatRankCount(s.second, s.tie_second, splitTies)}</td>
                  <td className="num">{formatRankCount(s.third, s.tie_third, splitTies)}</td>
                  <td className="num">{s.fourth}</td>
                  <td className="num">{formatPercent(percent(s.first, s.matches))}</td>
                  <td className="num">{formatPercent(percent(s.first + s.second, s.matches))}</td>
                  <td className="num">{formatPercent(percent(s.first + s.second + s.third, s.matches))}</td>
                </tr>
              ))}
              {stats.length === 0 ? (
                <tr>
                  <td colSpan={13} className="empty">
                    No data for selected years.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
