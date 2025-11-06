import { useState } from 'react';
import type { FieldError } from 'react-hook-form';

/* 🧩 Interest Selector Component */
export default function InterestSelector({
  defaultInterests,
  selected,
  onChange,
  error,
}: {
  defaultInterests: string[];
  selected: string[];
  onChange: (v: string[]) => void;
  error: FieldError | undefined;
}) {
  const [interests, setInterests] = useState(defaultInterests);
  const [newInterest, setNewInterest] = useState('');

  const toggleInterest = (interest: string) => {
    const updated = selected.includes(interest)
      ? selected.filter((i: string) => i !== interest)
      : [...selected, interest];
    onChange(updated);
  };

  const addInterest = () => {
    const value = newInterest.trim();
    if (!value) return;
    if (!interests.includes(value)) setInterests([...interests, value]);
    if (!selected.includes(value)) onChange([...selected, value]);
    setNewInterest('');
  };

  return (
    <div>
      <label className='block text-sm font-medium mb-1'>
        Select your interests:
      </label>
      <div className='flex flex-wrap gap-2 mb-2'>
        {interests.map((interest) => (
          <button
            type='button'
            key={interest}
            onClick={() => toggleInterest(interest)}
            className={`px-3 py-1 rounded-full border transition-all ${
              selected.includes(interest)
                ? 'bg-blue-500 text-white border-blue-500'
                : 'bg-white text-gray-700 hover:bg-gray-100 border-gray-300'
            }`}
          >
            {interest}
          </button>
        ))}
      </div>

      <div className='flex gap-2 mb-1'>
        <input
          type='text'
          placeholder='Add your own...'
          value={newInterest}
          onChange={(e) => setNewInterest(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault(); // Prevent form submission
              addInterest(); // Call your add function
            }
          }}
          className='flex-1 border rounded-full px-3 py-1'
        />
        <button
          type='button'
          onClick={addInterest}
          className='bg-blue-500 text-white rounded-full px-3 py-1'
        >
          Add
        </button>
      </div>

      {error && <p className='text-red-500 text-sm mt-1'>{error.message}</p>}
    </div>
  );
}
