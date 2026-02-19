const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
      <div className="bg-white rounded-xl p-6 w-[400px] shadow-lg relative">
        
        <h3 className="text-lg font-semibold mb-4">
          {title}
        </h3>

        <div>{children}</div>

        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-slate-500 hover:text-red-500"
        >
          ✕
        </button>
      </div>
    </div>
  );
};

export default Modal;
