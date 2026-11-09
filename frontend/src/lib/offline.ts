import { openDB } from 'idb';

export type QueuedOutcome = {
  event_uuid: string;
  userId: number;
  loanId: number;
  payload: {
    event_uuid: string; outcome: string; notes: string;
    latitude: number | null; longitude: number | null; occurred_at: string;
    promise_date?: string; promise_amount?: number;
  };
};
type CachedLoanSnapshot = { savedAt: number; loans: unknown[] };

const dbPromise = openDB('collectiq-offline', 2, {
  upgrade(db, oldVersion) {
    if (!db.objectStoreNames.contains('outcomes')) db.createObjectStore('outcomes', { keyPath: 'event_uuid' });
    if (oldVersion < 2 && !db.objectStoreNames.contains('loanSnapshots')) db.createObjectStore('loanSnapshots');
  },
});
export async function enqueue(item: QueuedOutcome) { const db = await dbPromise; await db.put('outcomes', item); }
export async function pending(userId?: number): Promise<QueuedOutcome[]> { const db = await dbPromise; const all = await db.getAll('outcomes') as QueuedOutcome[]; return userId === undefined ? all : all.filter((item) => item.userId === userId); }
export async function removeQueued(id: string) { const db = await dbPromise; await db.delete('outcomes', id); }
// Cache only the assigned list, not full histories, credentials, or reminder contents.
export async function cacheAssignedLoans(userId: number, loans: unknown[]) {
  const db = await dbPromise;
  await db.put('loanSnapshots', { savedAt: Date.now(), loans } satisfies CachedLoanSnapshot, `assigned:${userId}`);
}
export async function getCachedAssignedLoans(userId: number, maxAgeMs = 7 * 24 * 60 * 60 * 1000) {
  const db = await dbPromise;
  const snapshot = await db.get('loanSnapshots', `assigned:${userId}`) as CachedLoanSnapshot | undefined;
  if (!snapshot || Date.now() - snapshot.savedAt > maxAgeMs) return null;
  return snapshot.loans;
}
