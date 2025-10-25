import axios from 'axios'

const baseURL = (import.meta as any).env?.VITE_API_BASE || ''

export const api = axios.create({
  baseURL,
  withCredentials: false,
})

export function getWsUrl(): string {
  const envUrl = (import.meta as any).env?.VITE_BACKEND_WS_URL
  if (envUrl) return envUrl as string
  // Derive from API base or current origin
  const base: string = (import.meta as any).env?.VITE_API_BASE || window.location.origin
  return base.replace(/^http/, 'ws').replace(/\/$/, '') + '/ws'
}

export async function fetchDrift() {
  const { data } = await api.get('/drift')
  return data
}

export async function fetchOptimization() {
  const { data } = await api.get('/optimization')
  return data
}

export async function fetchAgents() {
  const { data } = await api.get('/api/agents')
  return data
}

export async function createAgent(form: { name: string; role: string }) {
  const fd = new FormData()
  fd.append('name', form.name)
  fd.append('role', form.role)
  const { data } = await api.post('/api/agents', fd)
  return data
}

export async function fetchAuditFiles() {
  const { data } = await api.get('/api/audit')
  return data
}

export async function fetchKbaIndex() {
  const { data } = await api.get('/api/kba')
  return data
}

export async function uploadKba(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await api.post('/api/upload_kba', fd)
  return data
}

export async function sendJunieTask(task: any) {
  const { data } = await api.post('/api/junie', task)
  return data
}

export async function queryGPT(query: string) {
  const { data } = await api.post('/api/gpt/query', { query })
  return data
}
