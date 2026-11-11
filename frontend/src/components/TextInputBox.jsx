import { useState, useRef, useEffect } from 'react';
import { SendHorizontal, MessageSquare } from 'lucide-react';

export default function TextInputBox({ onSend }) {
  const [text, setText] = useState('');
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim()) {
      onSend(text.trim());
      setText('');
    }
  };

  return (
    <div className="fixed bottom-24 right-6 w-88 glass-panel border border-white/10 rounded-2xl shadow-2xl p-4 z-40 backdrop-blur-xl">
      <div className="mb-2 text-xs text-gray-300 font-semibold tracking-wide flex items-center gap-1.5">
        <MessageSquare size={14} className="text-blue-400" />
        <span>Live Caption Broadcast (Normal Mode)</span>
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type message to caption..."
          className="flex-1 glass-input text-white text-xs rounded-xl px-3.5 py-2.5 border border-white/10 placeholder-gray-500 focus:outline-none focus:border-blue-400"
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-500 text-white rounded-xl px-3 py-2 transition-all shadow-md shadow-blue-500/20 disabled:opacity-50 flex items-center justify-center shrink-0"
          disabled={!text.trim()}
          title="Send Subtitle"
        >
          <SendHorizontal size={16} />
        </button>
      </form>
    </div>
  );
}
