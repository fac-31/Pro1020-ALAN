import { useState } from 'react';
import axios from 'axios';

interface Metadata {
  title?: string;
  topics?: string[];
  source?: string;
  url?: string;
  type?: string;
  doc_id?: string;
  added_at?: string;
}

interface Result {
  content: string;
  score: number;
  metadata: Metadata;
}

interface SearchResponse {
  status: string;
  query: string;
  results: Result[];
  total_found: number;
}

const Search = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await axios.post<SearchResponse>(
        'http://127.0.0.1:8000/search',
        {
          query,
          user_interests: [], // adjust if you want to filter by topics
          n_results: 10,
        }
      );

      setResults(res.data.results);
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.detail || 'Error occurred while searching.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className='p-6 max-w-xl mx-auto'>
      <h1 className='text-2xl font-semibold mb-4'>Search Knowledge Base</h1>

      <div className='flex gap-2 mb-4'>
        <input
          type='text'
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='Enter search query...'
          className='flex-1 border p-2 rounded'
        />
        <button onClick={handleSearch} className='border rounded p-2'>
          Search
        </button>
      </div>

      {loading && <p>Loading...</p>}
      {error && <p className='text-red-500'>{error}</p>}

      <div className='space-y-4'>
        {results.map((res, index) => (
          <div key={index} className='border p-3 rounded'>
            <p>
              <strong>Content:</strong> {res.content.slice(0, 100)}
              {res.content.length > 100 ? '...' : ''}
            </p>
            <p>
              <strong>Score:</strong> {res.score.toFixed(3)}
            </p>
            <p>
              <strong>Title:</strong> {res.metadata.title || 'N/A'}
            </p>
            {res.metadata.topics && (
              <p>
                <strong>Topics:</strong> {res.metadata.topics.join(', ')}
              </p>
            )}
            {res.metadata.url && (
              <p>
                <strong>URL:</strong>{' '}
                <a
                  href={res.metadata.url}
                  target='_blank'
                  rel='noopener noreferrer'
                >
                  {res.metadata.url}
                </a>
              </p>
            )}
            {res.metadata.type && <p>Type: {res.metadata.type}</p>}
          </div>
        ))}
      </div>
    </div>
  );
};

export default Search;
