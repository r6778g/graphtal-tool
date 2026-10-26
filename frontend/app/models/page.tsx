'use client'

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import type { Session, User } from '@supabase/supabase-js'
import { ArrowLeft, RefreshCw, UploadCloud } from 'lucide-react'
import { API_BASE_URL } from '@/lib/api'
import { getSupabaseClient } from '@/lib/supabase'

type ModuleName = 'upstream' | 'formulation'

type ModelVersion = {
  id: string
  module: ModuleName
  target: string
  algorithm: string
  version: number
  dataset_id: string
  dataset_version?: number
  metrics: {
    train_r2?: number
    test_r2?: number
    active_test_r2?: number | null
    test_r2_delta?: number | null
    eligible_for_promotion?: boolean
    evaluation_rows?: number
  }
  status: 'candidate' | 'active' | 'archived' | 'rejected'
  is_active: boolean
  created_at: string
}

type TrainingJob = {
  id: string
  module: ModuleName
  dataset_id: string
  status: 'queued' | 'training' | 'candidate' | 'failed'
  progress: number
  message: string
  candidate_ids: string[]
  created_at: string
}

const formatScore = (value?: number | null) =>
  typeof value === 'number' ? value.toFixed(3) : '—'

export default function ModelManagementPage() {
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<User | null>(null)
  const [configurationError, setConfigurationError] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [moduleName, setModuleName] = useState<ModuleName>('upstream')
  const [file, setFile] = useState<File | null>(null)
  const [models, setModels] = useState<ModelVersion[]>([])
  const [activeModels, setActiveModels] = useState<ModelVersion[]>([])
  const [jobs, setJobs] = useState<TrainingJob[]>([])
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')

  const isAdmin = useMemo(() => {
    const metadata = user?.app_metadata as Record<string, unknown> | undefined
    const roles = metadata?.roles
    return metadata?.graphtal_role === 'admin' ||
      (Array.isArray(roles) && roles.includes('graphtal_admin'))
  }, [user])

  useEffect(() => {
    let mounted = true
    try {
      const supabase = getSupabaseClient()
      supabase.auth.getSession().then(({ data, error: sessionError }) => {
        if (!mounted) return
        if (sessionError) setError(sessionError.message)
        setSession(data.session)
        setUser(data.session?.user ?? null)
      })
      const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
        setSession(nextSession)
        setUser(nextSession?.user ?? null)
      })
      return () => {
        mounted = false
        data.subscription.unsubscribe()
      }
    } catch (cause) {
      setConfigurationError(cause instanceof Error ? cause.message : String(cause))
      return () => {
        mounted = false
      }
    }
  }, [])

  const request = useCallback(async <T,>(
    path: string,
    token: string,
    init?: RequestInit,
  ): Promise<T> => {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${token}`,
        ...(init?.headers ?? {}),
      },
    })
    const body = await response.json()
    if (!response.ok) {
      throw new Error(body.error || `Request failed with status ${response.status}`)
    }
    return body as T
  }, [])

  const loadRegistry = useCallback(async (token: string) => {
    const [modelResult, activeResult, jobResult] = await Promise.all([
      request<{ models: ModelVersion[] }>('/api/models', token),
      request<{ models: ModelVersion[] }>('/api/models/active', token),
      request<{ jobs: TrainingJob[] }>('/api/training/jobs', token),
    ])
    setModels(modelResult.models)
    setActiveModels(activeResult.models)
    setJobs(jobResult.jobs)
  }, [request])

  useEffect(() => {
    if (!session?.access_token) return
    let mounted = true
    const refresh = async () => {
      try {
        await loadRegistry(session.access_token)
        if (mounted) setError('')
      } catch (cause) {
        if (mounted) setError(cause instanceof Error ? cause.message : String(cause))
      }
    }
    void refresh()
    const timer = window.setInterval(() => {
      void refresh()
    }, 5000)
    return () => {
      mounted = false
      window.clearInterval(timer)
    }
  }, [session, loadRegistry])

  const signIn = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await getSupabaseClient().auth.signInWithPassword({ email, password })
      if (result.error) throw result.error
      setPassword('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  const submitTraining = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!file || !session) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const form = new FormData()
      form.set('module', moduleName)
      form.set('file', file)
      const uploaded = await request<{ dataset: { id: string; version: number } }>(
        '/api/datasets/upload',
        session.access_token,
        { method: 'POST', body: form },
      )
      const queued = await request<{ job: TrainingJob }>(
        '/api/training/jobs',
        session.access_token,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'Idempotency-Key': crypto.randomUUID() },
          body: JSON.stringify({ module: moduleName, dataset_id: uploaded.dataset.id }),
        },
      )
      setNotice(`Dataset v${uploaded.dataset.version} validated. Training job queued; activation requires administrator approval.`)
      await loadRegistry(session.access_token)
      if (queued.job.status === 'queued') {
        setJobs((current) => [queued.job, ...current.filter((job) => job.id !== queued.job.id)])
      }
      setFile(null)
      const input = document.getElementById('model-dataset') as HTMLInputElement | null
      if (input) input.value = ''
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  const performModelAction = async (modelId: string, action: 'promote' | 'rollback') => {
    if (!session) return
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await request(`/api/models/${modelId}/${action}`, session.access_token, {
        method: 'POST',
      })
      setNotice(action === 'promote'
        ? 'Candidate activated. Other API instances will refresh within the configured interval.'
        : 'Previous model restored. Other API instances will refresh within the configured interval.')
      await loadRegistry(session.access_token)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  const retryJob = async (jobId: string) => {
    if (!session) return
    setBusy(true)
    try {
      await request(`/api/training/jobs/${jobId}/retry`, session.access_token, {
        method: 'POST',
      })
      setNotice('Training retry queued.')
      await loadRegistry(session.access_token)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  const refreshModels = async () => {
    if (!session) return
    setBusy(true)
    try {
      await request('/api/models/refresh', session.access_token, { method: 'POST' })
      await loadRegistry(session.access_token)
      setNotice('This API instance checked the active registry versions.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause))
    } finally {
      setBusy(false)
    }
  }

  const signOut = async () => {
    const result = await getSupabaseClient().auth.signOut()
    if (result.error) setError(result.error.message)
  }

  return (
    <main className="min-h-screen bg-[#faf8f5] text-[#1e293b]">
      <header className="sticky top-0 z-20 border-b border-[#e8dfd3] bg-[#f4efe8]/95">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="rounded-lg p-2 hover:bg-[#e8dfd3]" aria-label="Back to home">
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <h1 className="text-lg font-bold">Model Management</h1>
              <p className="text-xs text-slate-500">Versioned training, evaluation and activation</p>
            </div>
          </div>
          {session && (
            <div className="flex items-center gap-3 text-sm">
              <span className="hidden text-slate-600 sm:inline">{user?.email}</span>
              <button onClick={() => void signOut()} className="rounded-lg border px-3 py-2 text-xs hover:bg-white">
                Sign out
              </button>
            </div>
          )}
        </div>
      </header>

      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
        {(configurationError || error || notice) && (
          <div className={`rounded-xl border p-4 text-sm ${
            configurationError || error
              ? 'border-red-200 bg-red-50 text-red-800'
              : 'border-emerald-200 bg-emerald-50 text-emerald-800'
          }`}>
            {configurationError || error || notice}
          </div>
        )}

        {!session ? (
          <section className="mx-auto max-w-md rounded-2xl border border-[#e8dfd3] bg-white p-6 shadow-sm">
            <h2 className="mb-2 text-lg font-semibold">Sign in to manage models</h2>
            <p className="mb-5 text-sm text-slate-600">Use your provisioned Supabase account. Training and model history are private to your account and organization.</p>
            <form onSubmit={signIn} className="space-y-4">
              <label className="block text-sm font-medium">
                Email
                <input required type="email" value={email} onChange={(event) => setEmail(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5" />
              </label>
              <label className="block text-sm font-medium">
                Password
                <input required type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 w-full rounded-lg border p-2.5" />
              </label>
              <button disabled={busy || Boolean(configurationError)} className="w-full rounded-lg bg-[#d97706] px-4 py-2.5 font-semibold text-white disabled:opacity-50">
                {busy ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
          </section>
        ) : (
          <>
            <section className="rounded-2xl border border-[#e8dfd3] bg-white p-6 shadow-sm">
              <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold">Train a candidate model</h2>
                  <p className="mt-1 text-sm text-slate-600">Uploads are validated and stored privately. Training never replaces the active model.</p>
                </div>
                <button onClick={() => void refreshModels()} disabled={busy || !isAdmin} className="inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs disabled:opacity-50">
                  <RefreshCw className="h-3.5 w-3.5" /> Refresh this API
                </button>
              </div>
              <form onSubmit={submitTraining} className="grid gap-4 sm:grid-cols-[1fr_2fr_auto] sm:items-end">
                <label className="text-sm font-medium">
                  Module
                  <select value={moduleName} onChange={(event) => setModuleName(event.target.value as ModuleName)} className="mt-1 block w-full rounded-lg border bg-white p-2.5">
                    <option value="upstream">Upstream</option>
                    <option value="formulation">Formulation</option>
                  </select>
                </label>
                <label className="text-sm font-medium">
                  CSV or Excel dataset
                  <input id="model-dataset" required type="file" accept=".csv,.xls,.xlsx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="mt-1 block w-full rounded-lg border p-2 text-sm" />
                </label>
                <button disabled={busy || !file} className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#d97706] px-4 py-2.5 font-semibold text-white disabled:opacity-50">
                  <UploadCloud className="h-4 w-4" /> Queue training
                </button>
              </form>
              <p className="mt-3 text-xs text-slate-500">Requires the module&apos;s existing feature and target columns. At least 8 complete unique records are needed. Candidates that do not match the active holdout score cannot be promoted.</p>
            </section>

            <section className="rounded-2xl border border-[#e8dfd3] bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold">Active production models</h2>
              {activeModels.length === 0 ? (
                <p className="text-sm text-slate-500">No registry-managed model has been activated yet; predictions continue using the existing local artifacts.</p>
              ) : (
                <div className="grid gap-3 md:grid-cols-2">
                  {activeModels.map((model) => (
                    <div key={model.id} className="rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
                      <div className="flex items-center justify-between gap-2">
                        <h3 className="font-semibold">{model.module} · {model.target}</h3>
                        <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">Active v{model.version}</span>
                      </div>
                      <p className="mt-2 text-sm text-slate-600">{model.algorithm} · test R² {formatScore(model.metrics?.test_r2)}</p>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-[#e8dfd3] bg-white p-6 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold">Training history</h2>
              {jobs.length === 0 ? <p className="text-sm text-slate-500">No training jobs yet.</p> : (
                <div className="space-y-3">
                  {jobs.map((job) => (
                    <div key={job.id} className="rounded-xl border p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <h3 className="font-medium">{job.module} · {job.status}</h3>
                          <p className="mt-1 text-xs text-slate-500">{job.message} · {new Date(job.created_at).toLocaleString()}</p>
                        </div>
                        {job.status === 'failed' && (
                          <button onClick={() => void retryJob(job.id)} disabled={busy} className="rounded-lg border px-3 py-2 text-xs hover:bg-slate-50 disabled:opacity-50">Retry</button>
                        )}
                      </div>
                      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                        <div className={`h-full ${job.status === 'failed' ? 'bg-red-500' : 'bg-[#d97706]'}`} style={{ width: `${Math.max(0, Math.min(100, job.progress))}%` }} />
                      </div>
                      <p className="mt-1 text-right text-xs text-slate-500">{job.progress}% · {job.candidate_ids.length} candidates</p>
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-[#e8dfd3] bg-white p-6 shadow-sm">
              <div className="mb-4 flex items-center justify-between gap-2">
                <div>
                  <h2 className="text-lg font-semibold">Model version history</h2>
                  <p className="text-xs text-slate-500">Candidate creation and active-model promotion are separate states.</p>
                </div>
                {isAdmin && <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-900">Administrator</span>}
              </div>
              {models.length === 0 ? <p className="text-sm text-slate-500">No candidate or historical model versions yet.</p> : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead className="border-b text-xs uppercase text-slate-500">
                      <tr><th className="py-3 pr-3">Model / version</th><th className="py-3 pr-3">Status</th><th className="py-3 pr-3">Evaluation</th><th className="py-3 pr-3">Dataset</th><th className="py-3">Actions</th></tr>
                    </thead>
                    <tbody className="divide-y">
                      {models.map((model) => (
                        <tr key={model.id}>
                          <td className="py-3 pr-3">
                            <span className="font-medium">{model.module} · {model.target}</span>
                            <span className="block text-xs text-slate-500">{model.algorithm} · model v{model.version} · dataset v{model.dataset_version ?? '—'}</span>
                          </td>
                          <td className="py-3 pr-3">
                            <span className={`rounded-full px-2 py-1 text-xs ${model.is_active ? 'bg-emerald-100 text-emerald-800' : model.status === 'candidate' ? 'bg-amber-100 text-amber-900' : 'bg-slate-100 text-slate-600'}`}>
                              {model.is_active ? 'active' : model.status}
                            </span>
                          </td>
                          <td className="py-3 pr-3 text-xs">
                            <div>test R² {formatScore(model.metrics?.test_r2)}</div>
                            <div className="text-slate-500">active {formatScore(model.metrics?.active_test_r2)} · Δ {formatScore(model.metrics?.test_r2_delta)}</div>
                          </td>
                          <td className="py-3 pr-3 text-xs">
                            <span>v{model.dataset_version ?? '—'}</span>
                            <span className="block font-mono text-slate-500">{model.dataset_id.slice(0, 8)}</span>
                          </td>
                          <td className="py-3">
                            {isAdmin && model.status === 'candidate' && (
                              <button onClick={() => void performModelAction(model.id, 'promote')} disabled={busy || !model.metrics?.eligible_for_promotion} title={model.metrics?.eligible_for_promotion ? 'Activate this candidate' : 'Candidate must meet the active holdout score'} className="mr-2 rounded-lg bg-[#d97706] px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40">Promote</button>
                            )}
                            {isAdmin && model.status === 'archived' && (
                              <button onClick={() => void performModelAction(model.id, 'rollback')} disabled={busy} className="rounded-lg border px-3 py-2 text-xs hover:bg-slate-50 disabled:opacity-50">Rollback</button>
                            )}
                            {!isAdmin && <span className="text-xs text-slate-400">Admin approval required</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
            {!isAdmin && <p className="text-xs text-slate-500">Promotion, rollback, and instance refresh require an administrator role in Supabase app_metadata.</p>}
          </>
        )}
      </div>
    </main>
  )
}
