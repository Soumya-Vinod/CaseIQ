const Card = ({ children, className = "", variant = "default" }) => {
  const variants = {
    default: "bg-white border border-slate-200 shadow-md",
    lavender: "bg-[#D5DCF9] border border-[#A7B0CA] shadow-lg",
    teal: "bg-[#8EDCE6] border border-[#A7B0CA] shadow-lg",
    powder: "bg-[#A7B0CA] border border-[#8EDCE6] shadow-lg",
    warm: "bg-[#725E54] text-white border border-[#443627] shadow-lg",
  };

  return (
    <div
      className={`rounded-2xl p-8 transition-all duration-300 hover:shadow-xl hover:-translate-y-1 ${variants[variant]} ${className}`}
    >
      {children}
    </div>
  );
};

export default Card;
