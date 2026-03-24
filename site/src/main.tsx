import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'
import './style.css'
import { createClient } from '@supabase/supabase-js'

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

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL as string | undefined
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined

async function loadFromSupabase(): Promise<DataFile> {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    throw new Error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY')
  }

  const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

  const { data: player_mapping, error: pmError } = await supabase
    .from('player_mapping')
    .select('player_id,nickname,player_id_new')
    .order('player_id', { ascending: true })

  if (pmError) throw new Error(`Supabase player_mapping error: ${pmError.message}`)

  const matches: MatchRow[] = []
  const pageSize = 1000
  let offset = 0

  while (true) {
    const { data, error } = await supabase
      .from('match_result')
      .select(
        'year,phase,round_name,table_name,match_no,e_player_id,e_score,e_penalty,e_rank,s_player_id,s_score,s_penalty,s_rank,w_player_id,w_score,w_penalty,w_rank,n_player_id,n_score,n_penalty,n_rank',
      )
      .order('year', { ascending: true })
      .order('round_name', { ascending: true })
      .order('table_name', { ascending: true })
      .order('match_no', { ascending: true })
      .range(offset, offset + pageSize - 1)

    if (error) throw new Error(`Supabase match_result error: ${error.message}`)
    if (!data) break

    matches.push(...(data as MatchRow[]))
    if (data.length < pageSize) break
    offset += pageSize
  }

  const years = Array.from(new Set(matches.map((m) => m.year))).sort((a, b) => a - b)

  return {
    generated_at: new Date().toISOString(),
    years,
    player_mapping: (player_mapping ?? []) as PlayerMappingRow[],
    matches,
  }
}

function Loader() {
  const [data, setData] = useState<DataFile | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (SUPABASE_URL && SUPABASE_ANON_KEY) {
      loadFromSupabase()
        .then(setData)
        .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
      return
    }

    const url = `${import.meta.env.BASE_URL}data.json`
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load data.json (${r.status})`)
        return r.json() as Promise<DataFile>
      })
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  if (error) {
    return (
      <div className="page">
        <div className="panel">
          <div className="panelTitle">Error</div>
          <div className="error">{error}</div>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="page">
        <div className="panel">
          <div className="panelTitle">Loading</div>
          <div>{SUPABASE_URL && SUPABASE_ANON_KEY ? 'Loading from Supabase…' : 'Loading data.json…'}</div>
        </div>
      </div>
    )
  }

  return <App data={data} />
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Loader />
  </StrictMode>,
)
