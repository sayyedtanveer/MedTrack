import { useEffect, useState, useCallback } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import workOrderService, { type JobCard, type WorkOrderDetail } from '@/services/work-order.service';

const STATUS_STYLES: Record<string, { badge: string; icon: string }> = {
  PENDING:     { badge: 'bg-slate-700 text-slate-300', icon: '⏳' },
  IN_PROGRESS: { badge: 'bg-amber-900 text-amber-200', icon: '⚙️' },
  DONE:        { badge: 'bg-emerald-900 text-emerald-200', icon: '✅' },
};

export default function JobCardsPage() {
  const { woId } = useParams<{ woId: string }>();
  const navigate = useNavigate();
  const [wo, setWo] = useState<WorkOrderDetail | null>(null);
  const [cards, setCards] = useState<JobCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [showRemarks, setShowRemarks] = useState<string | null>(null);
  const [remarks, setRemarks] = useState('');
  
  const [prodJcId, setProdJcId] = useState<string | null>(null);
  const [prodGood, setProdGood] = useState('');
  const [prodScrap, setProdScrap] = useState('');
  const [prodNotes, setProdNotes] = useState('');

  const load = useCallback(async () => {
    if (!woId) return;
    setLoading(true);
    setError(null);
    try {
      const [woRes, jcRes] = await Promise.all([
        workOrderService.get(woId),
        workOrderService.listJobCards(woId),
      ]);
      setWo(woRes.data);
      setCards(jcRes.data);
    } catch {
      setError('Failed to load job cards.');
    } finally {
      setLoading(false);
    }
  }, [woId]);

  useEffect(() => { load(); }, [load]);

  const handleStart = async (jcId: string) => {
    if (!woId || pendingId) return;
    setPendingId(jcId);
    try {
      await workOrderService.startJobCard(woId, jcId);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Failed to start job card.');
    } finally {
      setPendingId(null);
    }
  };

  const handleComplete = async (jcId: string) => {
    if (!woId || pendingId) return;
    setPendingId(jcId);
    try {
      await workOrderService.completeJobCard(woId, jcId, remarks || undefined);
      setShowRemarks(null);
      setRemarks('');
      setProdJcId(null);
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Failed to complete job card.');
    } finally {
      setPendingId(null);
    }
  };

  const handleRecordProduction = async (jcId: string) => {
    if (!woId || pendingId) return;
    if (!prodGood && !prodScrap) {
      setError('Please enter either Good or Scrap quantity.');
      return;
    }
    const goodNum = Number(prodGood) || 0;
    const scrapNum = Number(prodScrap) || 0;
    if (goodNum < 0 || scrapNum < 0) {
      setError('Quantities cannot be negative.');
      return;
    }
    if (goodNum === 0 && scrapNum === 0) {
      setError('Total production quantity must be greater than zero.');
      return;
    }

    setPendingId(jcId);
    setError(null);
    try {
      await workOrderService.recordProduction(woId, {
        job_card_id: jcId,
        produced_quantity: goodNum,
        scrap_quantity: scrapNum,
        notes: prodNotes || undefined,
      });
      setProdJcId(null);
      setProdGood('');
      setProdScrap('');
      setProdNotes('');
      await load();
    } catch (e: any) {
      setError(e?.response?.data?.message || 'Failed to record production.');
    } finally {
      setPendingId(null);
    }
  };

  const doneCount = cards.filter((c) => c.status === 'DONE').length;
  const pct = cards.length > 0 ? Math.round((doneCount / cards.length) * 100) : 0;

  return (
    <div className="min-h-screen bg-[#0d0f14] text-white">
      {/* Header */}
      <div className="border-b border-white/10 bg-[#111318] px-4 py-4 sm:px-6">
        <button onClick={() => navigate('/shop-floor')} className="text-slate-400 text-xs mb-2 block">
          ← Shop Floor
        </button>
        {wo ? (
          <div className="flex items-center justify-between gap-2">
            <div>
              <h1 className="text-xl font-bold font-mono text-indigo-300">{wo.wo_number}</h1>
              <p className="text-xs text-slate-400 mt-0.5">Job Cards — {doneCount}/{cards.length} complete</p>
            </div>
            <button
              onClick={load}
              className="rounded-full p-2 bg-white/5 hover:bg-white/10 transition-colors text-sm"
              title="Refresh"
            >🔄</button>
          </div>
        ) : (
          <div className="h-6 bg-white/10 rounded animate-pulse w-32" />
        )}
      </div>

      {/* Progress */}
      {cards.length > 0 && (
        <div className="px-4 pt-4 sm:px-6">
          <div className="flex justify-between text-xs text-slate-400 mb-1.5">
            <span>Operations Progress</span>
            <span className="text-emerald-400 font-medium">{pct}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-indigo-600 to-emerald-500 transition-all duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mx-4 mt-4 rounded-xl border border-red-800 bg-red-900/20 p-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="p-4 sm:p-6 space-y-3 max-w-2xl mx-auto mt-2">
        {loading && (
          <div className="flex flex-col items-center justify-center h-48 gap-3 text-slate-400">
            <div className="w-7 h-7 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-sm">Loading job cards…</span>
          </div>
        )}

        {!loading && cards.map((jc) => {
          const st = STATUS_STYLES[jc.status] ?? STATUS_STYLES.PENDING;
          const isWorking = pendingId === jc.id;

          return (
            <div
              key={jc.id}
              className="rounded-2xl border border-white/10 bg-[#111318] p-5 shadow"
            >
              {/* Card header */}
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center text-lg font-bold text-slate-200 shrink-0">
                  {jc.sequence}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate font-mono">{jc.operation_id}</p>
                  {jc.started_at && (
                    <p className="text-xs text-slate-400">Started {new Date(jc.started_at).toLocaleTimeString()}</p>
                  )}
                  {jc.completed_at && (
                    <p className="text-xs text-emerald-400">Done {new Date(jc.completed_at).toLocaleTimeString()}</p>
                  )}
                  {jc.status !== 'PENDING' && (
                    <div className="mt-2 text-xs text-slate-300">
                      Planned: <span className="font-bold">{wo?.planned_quantity || 0}</span> | Good: <span className="text-emerald-400 font-bold">{jc.produced_quantity || 0}</span> | Scrap: <span className="text-rose-400 font-bold">{jc.scrap_quantity || 0}</span>
                    </div>
                  )}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-base">{st.icon}</span>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${st.badge}`}>
                    {jc.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Remarks display */}
              {jc.remarks && (
                <p className="text-xs text-slate-400 bg-white/5 rounded-lg px-3 py-2 mb-3">
                  💬 {jc.remarks}
                </p>
              )}

              {/* Production Form */}
              {jc.status === 'IN_PROGRESS' && prodJcId !== jc.id && showRemarks !== jc.id && (
                  <button
                    onClick={() => { setProdJcId(jc.id); setShowRemarks(null); }}
                    className="rounded-xl bg-indigo-700/80 hover:bg-indigo-600 active:scale-[0.98] py-2.5 text-sm font-semibold transition-all mb-3 w-full border border-indigo-500/50"
                  >
                    + Record Production
                  </button>
              )}

              {jc.status === 'IN_PROGRESS' && prodJcId === jc.id && (
                <div className="mb-4 space-y-3 bg-white/5 p-4 rounded-xl border border-white/10">
                  <h4 className="text-sm font-semibold text-indigo-300">Record Production</h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Good Quantity</label>
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={prodGood}
                        onChange={(e) => setProdGood(e.target.value)}
                        className="w-full rounded-lg bg-[#0d0f14] border border-white/10 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        placeholder={`e.g. ${wo?.planned_quantity || 0}`}
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-slate-400 mb-1">Scrap Quantity</label>
                      <input
                        type="number"
                        min="0"
                        step="any"
                        value={prodScrap}
                        onChange={(e) => setProdScrap(e.target.value)}
                        className="w-full rounded-lg bg-[#0d0f14] border border-white/10 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                        placeholder="0"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Notes / Reason for Scrap</label>
                    <textarea
                      value={prodNotes}
                      onChange={(e) => setProdNotes(e.target.value)}
                      placeholder="Optional notes…"
                      rows={2}
                      className="w-full rounded-lg bg-[#0d0f14] border border-white/10 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
                    />
                  </div>
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => setProdJcId(null)}
                      className="rounded-xl bg-white/5 hover:bg-white/10 px-4 py-2 text-sm transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleRecordProduction(jc.id)}
                      disabled={!!pendingId}
                      className="flex-1 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-[0.98] disabled:opacity-50 py-2 text-sm font-semibold transition-all"
                    >
                      {isWorking ? '…' : 'Save Production'}
                    </button>
                  </div>
                </div>
              )}

              {/* Remarks input (before completing) */}
              {showRemarks === jc.id && (
                <div className="mb-3">
                  <textarea
                    value={remarks}
                    onChange={(e) => setRemarks(e.target.value)}
                    placeholder="Add completion remarks (optional)…"
                    rows={2}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none"
                    autoFocus
                  />
                </div>
              )}

              {/* Action buttons — large for mobile */}
              <div className="flex gap-2 mt-1">
                {jc.status === 'PENDING' && (
                  <button
                    id={`btn-start-jc-${jc.id}`}
                    onClick={() => handleStart(jc.id)}
                    disabled={!!pendingId}
                    className="flex-1 rounded-xl bg-amber-700 hover:bg-amber-600 active:scale-[0.98] disabled:opacity-50 py-3 text-sm font-semibold transition-all"
                  >
                    {isWorking ? '…' : '▶ Start Operation'}
                  </button>
                )}

                {jc.status === 'IN_PROGRESS' && showRemarks !== jc.id && (
                  <>
                    <button
                      onClick={() => setShowRemarks(jc.id)}
                      className="flex-1 rounded-xl bg-emerald-700 hover:bg-emerald-600 active:scale-[0.98] py-3 text-sm font-semibold transition-all"
                    >
                      ✓ Complete
                    </button>
                  </>
                )}

                {jc.status === 'IN_PROGRESS' && showRemarks === jc.id && (
                  <>
                    <button
                      onClick={() => { setShowRemarks(null); setRemarks(''); }}
                      className="rounded-xl bg-white/5 hover:bg-white/10 px-4 py-3 text-sm transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      id={`btn-complete-jc-${jc.id}`}
                      onClick={() => handleComplete(jc.id)}
                      disabled={!!pendingId}
                      className="flex-1 rounded-xl bg-emerald-700 hover:bg-emerald-600 active:scale-[0.98] disabled:opacity-50 py-3 text-sm font-semibold transition-all"
                    >
                      {isWorking ? '…' : '✓ Confirm Complete'}
                    </button>
                  </>
                )}

                {jc.status === 'DONE' && (
                  <div className="flex-1 rounded-xl bg-white/5 py-3 text-sm text-emerald-400 text-center font-medium">
                    ✅ Operation Complete
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {!loading && cards.length === 0 && (
          <div className="flex flex-col items-center justify-center h-48 gap-3 text-slate-400">
            <div className="text-4xl">📭</div>
            <p className="text-sm">No job cards found for this work order.</p>
          </div>
        )}
      </div>
    </div>
  );
}
