const Input = ({
  type = "text",
  name,
  value,
  onChange,
  placeholder,
  required = false,
  disabled = false,
  error = false,
  className = "",
  ...props
}) => {
  return (
    <input
      type={type}
      name={name}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      disabled={disabled}
      {...props}
      className={`
        w-full rounded-lg px-4 py-2 
        border
        bg-white dark:bg-slate-900
        text-slate-800 dark:text-slate-200
        placeholder-slate-400 dark:placeholder-slate-500
        border-slate-300 dark:border-slate-600
        focus:outline-none focus:ring-2 focus:ring-indigo-500
        transition-colors duration-200
        disabled:opacity-50 disabled:cursor-not-allowed
        ${error ? "border-red-500 focus:ring-red-500" : ""}
        ${className}
      `}
    />
  );
};

export default Input;
