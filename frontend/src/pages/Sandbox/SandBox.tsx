import { Link } from 'react-router-dom';

const SandBox = () => {
  return (
    <div>
      <h1>Sandbox</h1>
      <Link className='flex' to='upload'>
        Upload
      </Link>
      <Link className='flex' to='search'>
        Search
      </Link>
      <Link className='flex' to='chat'>
        Chat
      </Link>
    </div>
  );
};

export default SandBox;
