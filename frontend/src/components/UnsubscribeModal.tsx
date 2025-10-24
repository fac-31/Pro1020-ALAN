import { useState } from 'react';
import axios from 'axios';

interface UnsubscribeModalProps {
  onClose: () => void;
}

const UnsubscribeModal = ({ onClose }: UnsubscribeModalProps) => {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  const handleUnsubscribe = async () => {
    try {
      await axios.delete(`http://localhost:8000/subscribers/${encodeURIComponent(email)}`);
      setMessage('Successfully unsubscribed!');
    } catch (error) {
      if (axios.isAxiosError(error) && error.response) {
        setMessage(`Error: ${error.response.data.detail}`);
      } else {
        setMessage('An unexpected error occurred.');
      }
    }
  };

  return (
    <div className="fixed inset-0 bg-[#242424] overflow-y-auto h-full w-full flex items-center justify-center">
      <div className="relative mx-auto p-5 border w-96 shadow-lg rounded-md bg-gray-200">
        <div className="mt-3 text-center">
          <h3 className="text-lg leading-6 font-medium text-gray-900">Unsubscribe</h3>
          <div className="mt-2 px-7 py-3">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Enter your email"
              className="input w-full border border-gray-900 rounded-md px-3 py-2 text-gray-900"
            />
          </div>
          <div className="items-center px-4 py-3">
            <button
              onClick={handleUnsubscribe}
              className="btn btn-primary w-full"
            >
              Unsubscribe
            </button>
          </div>
          {message && <p className="mt-2 text-sm text-gray-500">{message}</p>}
          <div className="items-center px-4 py-3">
            <button
              onClick={onClose}
              className="btn btn-secondary w-full"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UnsubscribeModal;
