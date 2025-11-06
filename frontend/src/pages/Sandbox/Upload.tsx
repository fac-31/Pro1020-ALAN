import { useState } from 'react';
import axios from 'axios';

const Upload = () => {
  const [mode, setMode] = useState('document'); // "document" or "article"
  const [form, setForm] = useState({
    filename: '',
    content: '',
    topics: '',
    title: '',
    url: '',
  });
  const [status, setStatus] = useState(''); // show success/error

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setStatus('');

    try {
      if (mode === 'document') {
        const res = await axios.post('http://127.0.0.1:8000/documents/upload', {
          filename: form.filename,
          content: form.content,
          topics: form.topics.split(',').map((t) => t.trim()),
        });
        setStatus(res.data.message);
      } else {
        const res = await axios.post('http://127.0.0.1:8000/news/add', {
          title: form.title,
          content: form.content,
          url: form.url,
          topics: form.topics.split(',').map((t) => t.trim()),
        });
        setStatus(res.data.message);
      }
    } catch (err) {
      console.error(err);
      setStatus(
        err.response?.data?.detail || 'An error occurred while uploading.'
      );
    }
  };

  return (
    <div className='p-6 max-w-xl mx-auto'>
      <h1 className='text-2xl font-semibold mb-4'>Upload</h1>

      {/* Mode selector */}
      <div className='flex gap-4 mb-6'>
        <label>
          <input
            type='radio'
            name='uploadType'
            value='document'
            checked={mode === 'document'}
            onChange={() => setMode('document')}
          />{' '}
          Document
        </label>

        <label>
          <input
            type='radio'
            name='uploadType'
            value='article'
            checked={mode === 'article'}
            onChange={() => setMode('article')}
          />{' '}
          News Article
        </label>
      </div>

      <form onSubmit={handleSubmit} className='space-y-4'>
        {mode === 'document' ? (
          <>
            <div>
              <label>Filename</label>
              <input
                type='text'
                name='filename'
                value={form.filename}
                onChange={handleChange}
                className='w-full border p-2 rounded'
                placeholder='example.txt'
                required
              />
            </div>
            <div>
              <label>Content</label>
              <textarea
                name='content'
                rows={5}
                value={form.content}
                onChange={handleChange}
                className='w-full border p-2 rounded'
                placeholder='Paste document text here...'
                required
              />
            </div>
          </>
        ) : (
          <>
            <div>
              <label>Title</label>
              <input
                type='text'
                name='title'
                value={form.title}
                onChange={handleChange}
                className='w-full border p-2 rounded'
                placeholder='Article title...'
                required
              />
            </div>
            <div>
              <label>URL</label>
              <input
                type='text'
                name='url'
                value={form.url}
                onChange={handleChange}
                className='w-full border p-2 rounded'
                placeholder='https://example.com/article'
                required
              />
            </div>
            <div>
              <label>Content</label>
              <textarea
                name='content'
                rows={5}
                value={form.content}
                onChange={handleChange}
                className='w-full border p-2 rounded'
                placeholder='Paste article content here...'
                required
              />
            </div>
          </>
        )}

        <div>
          <label>Topics</label>
          <input
            type='text'
            name='topics'
            value={form.topics}
            onChange={handleChange}
            className='w-full border p-2 rounded'
            placeholder='Comma-separated topics (e.g. AI, NLP, tech)'
          />
        </div>

        <button type='submit' className='w-full border rounded p-2'>
          Upload
        </button>
      </form>

      {status && <p className='mt-4'>{status}</p>}
    </div>
  );
};

export default Upload;
