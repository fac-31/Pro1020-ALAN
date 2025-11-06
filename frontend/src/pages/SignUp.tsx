import { useForm, Controller } from 'react-hook-form';
import { useState } from 'react';
import axios from 'axios';
import InterestSelector from '../components/InterestSelector';
import UnsubscribeModal from '../components/UnsubscribeModal';

export default function Signup() {
  const { register, handleSubmit, control } = useForm();
  const [feedback, setFeedback] = useState({ type: '', message: '' });
  const [isUnsubscribeModalOpen, setIsUnsubscribeModalOpen] = useState(false);

  const onSubmit = async (data: unknown) => {
    setFeedback({ type: '', message: '' });
    try {
      await axios.post('http://127.0.0.1:8000/subscribe', data);
      setFeedback({
        type: 'success',
        message: 'Check your inbox for confirmation!',
      });
    } catch (error) {
      console.error('Error submitting form:', error);
      if (axios.isAxiosError(error) && error.response) {
        setFeedback({
          type: 'error',
          message: error.response.data.message || 'An error occurred.',
        });
      } else {
        setFeedback({ type: 'error', message: 'An error occurred.' });
      }
    }
  };

  const defaultInterests = [
    'Technology',
    'Health',
    'Finance',
    'Education',
    'Entertainment',
    'Sports',
    'Travel',
    'Food',
  ];

  return (
    <div className='flex flex-col items-center justify-center min-h-screen p-6 w-full'>
      <nav className='absolute top-4 right-4'>
        <button
          onClick={() => setIsUnsubscribeModalOpen(true)}
          className='btn btn-secondary mt-4'
        >
          Unsubscribe
        </button>
      </nav>
      <h1 className='text-3xl font-bold mb-10'>Say hello to ALAN!</h1>
      <form
        onSubmit={handleSubmit(onSubmit)}
        className='space-y-4 h-full w-1/2 max-w-md'
      >
        <div>
          <label htmlFor='name' className='block text-sm font-medium mb-1'>
            Name
          </label>
          <input
            {...register('name')}
            type='text'
            id='name'
            placeholder='Name'
            className='input w-full'
            required
          />
        </div>
        <div>
          <label htmlFor='email' className='block text-sm font-medium mb-1'>
            Email
          </label>
          <input
            {...register('email')}
            type='email'
            id='email'
            placeholder='Email'
            className='input w-full'
            required
          />
        </div>

        {/* Replace textarea with controlled chip selector */}
        <Controller
          name='interests'
          control={control}
          defaultValue={[]}
          rules={{ validate: (v) => v.length > 0 || 'Select at least one' }}
          render={({ field: { value, onChange }, fieldState: { error } }) => (
            <InterestSelector
              defaultInterests={defaultInterests}
              selected={value}
              onChange={onChange}
              error={error}
            />
          )}
        />

        <button type='submit' className='btn btn-primary w-full'>
          Sign Up
        </button>

        {feedback.message && (
          <div
            className={`mt-4 text-center p-2 rounded-md ${
              feedback.type === 'success'
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {feedback.message}
          </div>
        )}
      </form>
      {isUnsubscribeModalOpen && (
        <UnsubscribeModal onClose={() => setIsUnsubscribeModalOpen(false)} />
      )}
    </div>
  );
}
