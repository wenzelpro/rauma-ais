import { useEffect, useMemo, useState } from 'react';
import ShipTable from './ShipTable';
import { useShips } from './useShips';
import type { Ship } from './types';

export default function App() {
  const { ships, isLoading, error, lastUpdated, fetchShips, newShips } = useShips();
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchShips();
    const id = setInterval(() => fetchShips(), 600_000);
    return () => clearInterval(id);
  }, [fetchShips]);

  useEffect(() => {
    if (newShips.length > 0 && import.meta.env.VITE_ENABLE_SLACK_NOTIFY === 'true') {
      const base = import.meta.env.VITE_SHIPS_API_BASE || 'https://rauma-ais-767fd7649193.herokuapp.com';
      fetch(`${base}/notify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ships: newShips }),
      }).catch((err) => console.warn('Slack notify error', err));
    }
  }, [newShips]);

  const filtered: Ship[] = useMemo(() => {
    const q = search.toLowerCase();
    return ships.filter(
      (s) =>
        s.name?.toLowerCase().includes(q) || s.mmsi.toString().includes(q)
    );
  }, [ships, search]);

  return (
    <div className="min-h-screen bg-gray-100 p-4">
      <div className="max-w-6xl mx-auto">
        <header className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
          <h1 className="text-2xl font-bold">Rauma AIS</h1>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-sm text-gray-600">
                Sist oppdatert: {lastUpdated.toISOString().replace('T', ' ').replace(/\.\d+Z/, '')} UTC
              </span>
            )}
            <button
              onClick={fetchShips}
              className="px-3 py-1 bg-blue-600 text-white rounded"
            >
              Refresh
            </button>
            {newShips.length > 0 && (
              <span className="inline-flex items-center px-2 py-1 text-sm font-medium bg-green-200 text-green-800 rounded-full">
                Nye skip: {newShips.length}
              </span>
            )}
          </div>
        </header>
        {error && (
          <div className="mb-2 p-2 bg-red-100 text-red-700 rounded">{error}</div>
        )}
        {isLoading && <div className="mb-2">Laster...</div>}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Søk etter MMSI eller navn"
          className="mb-4 p-2 border rounded w-full"
          autoFocus
        />
        <div className="bg-white rounded shadow">
          <ShipTable ships={filtered} />
        </div>
      </div>
    </div>
  );
}
