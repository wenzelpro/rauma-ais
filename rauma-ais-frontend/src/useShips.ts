import { useCallback, useRef, useState } from 'react';
import type { Ship } from './types';

const STORAGE_KEY = 'seenMmsi';

function loadSeen(): Set<number> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return new Set();
    const arr = JSON.parse(raw) as number[];
    return new Set(arr);
  } catch {
    return new Set();
  }
}

export function useShips() {
  const [ships, setShips] = useState<Ship[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [newShips, setNewShips] = useState<Ship[]>([]);
  const seenRef = useRef<Set<number>>(loadSeen());

  const fetchShips = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const base = import.meta.env.VITE_SHIPS_API_BASE || 'https://rauma-ais-767fd7649193.herokuapp.com';
      const res = await fetch(`${base}/ships`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const fetched: Ship[] = data.features ?? [];
      setShips(fetched);
      const currentMmsi = new Set(fetched.map((s) => s.mmsi));
      const seen = seenRef.current;
      const newMmsi = Array.from(currentMmsi).filter((m) => !seen.has(m));
      const newList = fetched.filter((s) => newMmsi.includes(s.mmsi));
      if (newMmsi.length > 0) {
        newMmsi.forEach((m) => seen.add(m));
        localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(seen)));
      }
      setNewShips(newList);
      setLastUpdated(new Date());
    } catch (e: any) {
      setError(e.message ?? String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { ships, isLoading, error, lastUpdated, fetchShips, newShips };
}
