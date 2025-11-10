import { useState, useEffect } from 'react';
import axios from 'axios';

const Chat = () => {
  const [messages, setMessages] = useState([
    { id: 1, text: '', fixed: false, response: '' },
  ]);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await axios.get(
          'http://127.0.0.1:8000/chat-history/frontend-user'
        );
        const history = res.data.history || [];
        if (history.length > 0) {
          const formattedMessages = [];
          for (let i = 0; i < history.length; i++) {
            if (history[i].type === 'incoming') {
              const message = {
                id: new Date(history[i].timestamp).getTime(),
                text: history[i].content,
                fixed: true,
                response: '',
              };
              if (i + 1 < history.length && history[i + 1].type === 'outgoing') {
                message.response = history[i + 1].content;
                i++;
              }
              formattedMessages.push(message);
            }
          }
          setMessages(
            formattedMessages.concat([
              { id: Date.now(), text: '', fixed: false, response: '' },
            ])
          );
        }
      } catch (err) {
        console.error('Error fetching chat history:', err);
      }
    };
    fetchHistory();
  }, []);

  const handleKeyDown = async (e, id) => {
    if (e.key === 'Enter') {
      e.preventDefault();

      setMessages((prev) =>
        prev.map((msg) => (msg.id === id ? { ...msg, fixed: true } : msg))
      );

      const currentMsg = messages.find((msg) => msg.id === id);
      if (!currentMsg?.text.trim()) return;

      try {
        const res = await axios.post('http://127.0.0.1:8000/test-rag', {
          query: currentMsg.text,
          user_interests: [],
          n_results: 3,
        });

        const history = res.data.history || [];
        if (history.length > 0) {
          const formattedMessages = [];
          for (let i = 0; i < history.length; i++) {
            if (history[i].type === 'incoming') {
              const message = {
                id: new Date(history[i].timestamp).getTime(),
                text: history[i].content,
                fixed: true,
                response: '',
              };
              if (i + 1 < history.length && history[i + 1].type === 'outgoing') {
                message.response = history[i + 1].content;
                i++;
              }
              formattedMessages.push(message);
            }
          }
          setMessages(
            formattedMessages.concat([
              { id: Date.now(), text: '', fixed: false, response: '' },
            ])
          );
        }
      } catch (err) {
        console.error('Error fetching response:', err);
        setMessages((prev) =>
          prev
            .map((msg) =>
              msg.id === id
                ? { ...msg, response: 'Error: could not reach backend.' }
                : msg
            )
            .concat({ id: Date.now(), text: '', fixed: false, response: '' })
        );
      }
    }
  };

  const handleChange = (e, id) => {
    const { value } = e.target;
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, text: value } : msg))
    );
  };

  return (
    <div className='p-6 max-w-xl mx-auto'>
      <h1 className='text-2xl font-semibold mb-2'>Chat</h1>
      <p className='mb-4'>Feature: You can send Alan 'emails' and he responds.</p>

      {messages.map((msg) => (
        <div key={msg.id} className='mb-6'>
          {msg.fixed ? (
            <>
              <div className='p-3'>
                <strong>You:</strong> {msg.text || '(empty)'}
              </div>
              <div className='p-3'>
                <strong>Alan:</strong>{' '}
                {msg.response ? msg.response : 'Thinking...'}
              </div>
            </>
          ) : (
            <textarea
              autoFocus
              rows={2}
              value={msg.text}
              onChange={(e) => handleChange(e, msg.id)}
              onKeyDown={(e) => handleKeyDown(e, msg.id)}
              placeholder='Type your message and press Enter...'
              className='w-full p-2 border rounded-lg focus:outline-none focus:ring'
            />
          )}
        </div>
      ))}
    </div>
  );
};

export default Chat;
