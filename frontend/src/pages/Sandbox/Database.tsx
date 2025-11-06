import { useEffect, useState } from 'react';
import axios from 'axios';

interface ChunkMetadata {
  title?: string;
  topics?: string[];
  source?: string;
  url?: string;
  added_at?: string;
}

interface ChunksResponse {
  status: string;
  chunks: string[];
  metadata: ChunkMetadata[];
}

const Database = () => {
  const [grouped, setGrouped] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchChunks = async () => {
      setLoading(true);
      try {
        const res = await axios.get<ChunksResponse>('http://127.0.0.1:8000/faiss/chunks');
        const { chunks, metadata } = res.data;
        const map: Record<string, string[]> = {};
        chunks.forEach((chunk, idx) => {
          const key = metadata[idx]?.title || 'Untitled';
          if (!map[key]) map[key] = [];
          map[key].push(chunk);
        });
        setGrouped(map);
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchChunks();
  }, []);

  if (loading) return <div>Loading chunks...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div className="p-4">
      <h1 className="text-xl mb-4">FAISS Chunks by Document</h1>
      {Object.entries(grouped).map(([title, chunks]) => (
        <div key={title} className="mb-6">
          <h2 className="font-semibold">{title}</h2>
          <ul className="list-disc list-inside">
            {chunks.map((chunk, i) => (
              <li key={i} className="text-sm mb-1">
                {chunk.length > 200 ? chunk.slice(0, 200) + '…' : chunk}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

export default Database;
