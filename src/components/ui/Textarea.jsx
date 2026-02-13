const Textarea = ({ className = "", ...props }) => {
  return (
    <textarea
      {...props}
      className={`w-full rounded-lg p-3 
      bg-white dark:bg-slate-900 
      border border-slate-300 dark:border-slate-600 
      text-slate-800 dark:text-slate-200 
      placeholder-slate-400 dark:placeholder-slate-500 
      focus:outline-none focus:ring-2 focus:ring-indigo-500 
      transition-colors duration-200 
      ${className}`}
    />
  );
};

export default Textarea;
