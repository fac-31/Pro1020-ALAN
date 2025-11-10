import { useState, useCallback } from 'react';
import axios from 'axios';
import { useDropzone } from 'react-dropzone';

const Upload = () => {
  const [mode, setMode] = useState('document'); // "document", "article", or "pdf"
  const [form, setForm] = useState({
    filename: '',
    content: '',
    topics: '',
    title: '',
    url: '',
  });
  const [pdfFile, setPdfFile] = useState(null); // For PDF uploads
  const [status, setStatus] = useState(''); // show success/error

  const onDrop = useCallback((acceptedFiles) => {
    // We only allow single PDF uploads
    if (acceptedFiles.length > 0) {
      setPdfFile(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: false,
  });

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
      } else if (mode === 'article') {
        const res = await axios.post('http://127.0.0.1:8000/news/add', {
          title: form.title,
          content: form.content,
          url: form.url,
          topics: form.topics.split(',').map((t) => t.trim()),
        });
        setStatus(res.data.message);
      } else if (mode === 'pdf') {
        if (!pdfFile) {
          setStatus('Please select a PDF file to upload.');
          return;
        }
        const formData = new FormData();
        formData.append('file', pdfFile);
        formData.append('topics', form.topics);

        const res = await axios.post(
          'http://127.0.0.1:8000/documents/upload_pdf',
          formData,
          {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          }
        );
        setStatus(res.data.message);
        setPdfFile(null); // Reset after upload
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

        <label>
          <input
            type='radio'
            name='uploadType'
            value='pdf'
            checked={mode === 'pdf'}
            onChange={() => setMode('pdf')}
          />{' '}
          PDF
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
        ) : mode === 'article' ? (
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
        ) : (
          <div>
            <label>PDF File</label>
            <div
              {...getRootProps()}
              className='border-2 border-dashed rounded p-10 text-center cursor-pointer'
            >
              <input {...getInputProps()} />
              {isDragActive ? (
                <p>Drop the PDF here ...</p>
              ) : pdfFile ? (
                <p>{pdfFile.name}</p>
              ) : (
                <p>Drag 'n' drop a PDF here, or click to select one</p>
              )}
            </div>
          </div>
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
