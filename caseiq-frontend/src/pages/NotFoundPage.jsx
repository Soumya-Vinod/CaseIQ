import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const NotFoundPage = () => {
  const navigate = useNavigate();
  return (
    <div className="min-h-[70vh] flex items-center justify-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="text-center space-y-6 max-w-md"
      >
        <div className="text-8xl font-black text-[#D5DCF9]">404</div>
        <div className="text-5xl">⚖️</div>
        <h1 className="text-2xl font-bold text-[#443627]">Page Not Found</h1>
        <p className="text-[#725E54]">
          The page you are looking for does not exist or has been moved.
        </p>
        <button
          onClick={() => navigate('/')}
          className="bg-[#443627] text-white px-8 py-3 rounded-xl hover:bg-[#725E54] transition shadow-lg"
        >
          Back to Home
        </button>
      </motion.div>
    </div>
  );
};

export default NotFoundPage;