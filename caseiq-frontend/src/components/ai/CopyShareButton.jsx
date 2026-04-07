import { useState } from 'react';
import { Copy, Check, Share2 } from 'lucide-react';
import toast from 'react-hot-toast';

const CopyShareButton = ({ text, title = 'CaseIQ Legal Information' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Copy failed');
    }
  };

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title,
          text: text.slice(0, 300) + '...',
          url: window.location.href,
        });
      } catch {}
    } else {
      handleCopy();
    }
  };

  return (
    <div className="flex gap-1">
      <button
        onClick={handleCopy}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-[#443627] px-2 py-1 rounded-lg hover:bg-[#D5DCF9]/40 transition"
        title="Copy response"
      >
        {copied ? <Check size={12} className="text-green-500" /> : <Copy size={12} />}
        {copied ? 'Copied' : 'Copy'}
      </button>
      <button
        onClick={handleShare}
        className="flex items-center gap-1 text-xs text-slate-400 hover:text-[#443627] px-2 py-1 rounded-lg hover:bg-[#D5DCF9]/40 transition"
        title="Share response"
      >
        <Share2 size={12} />
        Share
      </button>
    </div>
  );
};

export default CopyShareButton;