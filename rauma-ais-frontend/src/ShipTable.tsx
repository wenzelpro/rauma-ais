import { useState } from 'react';
import type { Ship } from './types';

type SortKey = keyof Ship;
type SortDir = 'asc' | 'desc';
const PAGE_SIZE = 20;

interface Props {
  ships: Ship[];
}

export default function ShipTable({ ships }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('mmsi');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [page, setPage] = useState(1);

  const sorted = [...ships].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const pages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const current = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const headerClass = (key: SortKey) =>
    `p-2 cursor-pointer ${key === sortKey ? 'underline' : ''}`;

  return (
    <div>
      <table className="min-w-full text-sm">
        <thead className="sticky top-0 bg-gray-100">
          <tr>
            <th className={headerClass('mmsi')} onClick={() => toggleSort('mmsi')}>
              MMSI
            </th>
            <th className={headerClass('name')} onClick={() => toggleSort('name')}>
              Name
            </th>
            <th
              className={headerClass('latitude')}
              onClick={() => toggleSort('latitude')}
            >
              Latitude
            </th>
            <th
              className={headerClass('longitude')}
              onClick={() => toggleSort('longitude')}
            >
              Longitude
            </th>
            <th className={headerClass('msgtime')} onClick={() => toggleSort('msgtime')}>
              MsgTime
            </th>
            <th
              className={headerClass('shipType')}
              onClick={() => toggleSort('shipType')}
            >
              ShipType
            </th>
          </tr>
        </thead>
        <tbody>
          {current.map((s) => (
            <tr key={s.mmsi} className="border-t">
              <td className="p-2">{s.mmsi}</td>
              <td className="p-2">{s.name}</td>
              <td className="p-2">{s.latitude}</td>
              <td className="p-2">{s.longitude}</td>
              <td className="p-2">{s.msgtime}</td>
              <td className="p-2">{s.shipType}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="flex items-center justify-between p-2 text-sm">
        <button
          className="px-2 py-1 border rounded"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1}
        >
          Forrige
        </button>
        <span>
          Side {page} av {pages}
        </span>
        <button
          className="px-2 py-1 border rounded"
          onClick={() => setPage((p) => Math.min(pages, p + 1))}
          disabled={page >= pages}
        >
          Neste
        </button>
      </div>
    </div>
  );
}
