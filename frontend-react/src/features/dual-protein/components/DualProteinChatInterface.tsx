import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, BookOpen, ChevronUp, ChevronDown, ExternalLink, AlertCircle, Square } from 'lucide-react';

// Types
interface Reference {
  ref_id: string;
  title: string;
  author?: string;
  authors?: string[];
  journal: string;
  year: number | string;
  doi: string;
  score?: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  thinking?: string[];
  references?: string[];
  isThinking?: boolean;
}

const DualProteinChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Welcome to Dual-Protein Q&A! Ask me anything about dual-protein interactions and related research.' }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [activeReferences, setActiveReferences] = useState<Reference[]>([]);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [systemReady, setSystemReady] = useState(false);
  const [initializing, setInitializing] = useState(true);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isAtBottomRef = useRef(true);

  // Initialize dual protein system on mount, retry until ready
  useEffect(() => {
    let cancelled = false;
    const tryInit = async () => {
      while (!cancelled) {
        try {
          const res = await fetch('/api/dual-protein/init', { method: 'POST' });
          const data = await res.json();
          if (data.success) {
            if (!cancelled) { setSystemReady(true); setInitializing(false); }
            return;
          }
        } catch { /* network error, retry */ }
        if (!cancelled) await new Promise(r => setTimeout(r, 3000));
      }
    };
    tryInit();
    return () => { cancelled = true; };
  }, []);

  const handleScroll = () => {
    const container = chatContainerRef.current;
    if (!container) return;
    const threshold = 50;
    const isBottom = container.scrollHeight - container.scrollTop - container.clientHeight <= threshold;
    isAtBottomRef.current = isBottom;
  };

  useEffect(() => {
    if (isAtBottomRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isTyping]);

  const scrollToBottom = () => {
    isAtBottomRef.current = true;
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsTyping(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    setError(null);
    scrollToBottom();

    setMessages(prev => [...prev, {
      role: 'assistant',
      content: '',
      thinking: [],
      isThinking: true
    }]);

    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/dual-protein/ask_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: input }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        let errorMessage = response.statusText;
        try {
          const errorData = await response.json();
          if (errorData.error) errorMessage = errorData.error;
        } catch { /* ignore */ }
        if (errorMessage.includes('未初始化') || errorMessage.includes('not initialized')) {
          throw new Error('System is initializing, please try again in a moment...');
        }
        throw new Error(errorMessage);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              handleStreamData(data);
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Something went wrong');
        setMessages(prev => {
          const newMsgs = [...prev];
          const lastMsg = newMsgs[newMsgs.length - 1];
          if (lastMsg.role === 'assistant') {
            lastMsg.content += `\n\n[Error: ${err.message}]`;
            lastMsg.isThinking = false;
          }
          return newMsgs;
        });
      }
    } finally {
      setIsTyping(false);
      abortControllerRef.current = null;
    }
  };

  const handleStreamData = (data: any) => {
    setMessages(prev => {
      const newMsgs = [...prev];
      const lastMsgIndex = newMsgs.length - 1;
      const lastMsg = { ...newMsgs[lastMsgIndex] };

      if (!lastMsg || lastMsg.role !== 'assistant') return prev;

      switch (data.type) {
        case 'start': break;
        case 'status': break;
        case 'reasoning_start':
          lastMsg.isThinking = true;
          break;
        case 'reasoning':
          if (!lastMsg.thinking) lastMsg.thinking = [''];
          else lastMsg.thinking = [...lastMsg.thinking];
          if (lastMsg.thinking.length === 0) lastMsg.thinking.push('');
          lastMsg.thinking[lastMsg.thinking.length - 1] += data.content;
          if (lastMsg.thinking[lastMsg.thinking.length - 1].includes('\n')) {
            const parts = lastMsg.thinking[lastMsg.thinking.length - 1].split('\n');
            lastMsg.thinking[lastMsg.thinking.length - 1] = parts[0];
            lastMsg.thinking.push(...parts.slice(1).filter((s: string) => s));
          }
          break;
        case 'reasoning_end':
          lastMsg.isThinking = false;
          break;
        case 'references':
          setActiveReferences(data.references);
          break;
        case 'answer_start':
          lastMsg.isThinking = false;
          break;
        case 'answer':
          lastMsg.content += data.content;
          break;
        case 'done': break;
        case 'error':
          lastMsg.content += `\n\n[System Error: ${data.error}]`;
          break;
      }

      newMsgs[lastMsgIndex] = lastMsg;
      return newMsgs;
    });
  };

  const renderContentWithCitations = (text: string) => {
    const parts = text.split(/(\[ref_\d+(?:,\s*ref_\d+)*\])/g);
    return parts.map((part, index) => {
      if (part.match(/^\[ref_\d+(?:,\s*ref_\d+)*\]$/)) {
        return (
          <span key={index} className="text-blue-600 font-bold text-xs align-super cursor-pointer group relative ml-0.5">
            {part}
            <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs bg-slate-800 text-white text-xs p-2 rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              View References
            </span>
            <span className="absolute bottom-0 left-0 w-full h-[1px] bg-blue-600 scale-x-0 group-hover:scale-x-100 transition-transform origin-left"></span>
          </span>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  if (initializing) {
    return (
      <div className="w-full h-full flex items-center justify-center text-slate-400 text-sm">
        Initializing Dual-Protein system...
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col bg-slate-50 overflow-hidden relative">
      <div className="flex-1 flex w-full h-full gap-6 relative overflow-hidden p-4 md:p-6">

        {/* Left Column: Chat Area */}
        <div className="flex-1 flex flex-col h-full glass-panel rounded-3xl overflow-hidden shadow-xl">

          {/* Messages Area */}
          <div
            ref={chatContainerRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth"
          >
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex flex-col gap-2 ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div
                  className={`
                    max-w-[90%] md:max-w-[85%] p-5 rounded-2xl shadow-sm text-sm md:text-base leading-relaxed
                    ${msg.role === 'user'
                      ? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-tr-sm shadow-md'
                      : 'bg-white/90 text-slate-700 rounded-tl-sm border border-slate-100 shadow-sm'}
                  `}
                >
                  {msg.role === 'assistant' && msg.thinking && msg.thinking.length > 0 && (
                    <div className="mb-4 p-4 rounded-xl bg-slate-100/50 border border-slate-200/50 text-xs font-mono text-slate-500 overflow-hidden">
                      <div className="flex items-center gap-2 mb-2 text-slate-400 uppercase tracking-wider text-[10px] font-bold">
                        <Sparkles size={12} className={msg.isThinking ? 'animate-spin-slow' : ''} />
                        <span>Deep Thinking</span>
                      </div>
                      {msg.thinking.map((line, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="pl-3 border-l-2 border-slate-300/50 my-1 break-words whitespace-pre-wrap"
                        >
                          {line.startsWith('>') ? line : `> ${line}`}
                        </motion.div>
                      ))}
                    </div>
                  )}
                  <div className="whitespace-pre-wrap">
                    {renderContentWithCitations(msg.content)}
                    {msg.role === 'assistant' && idx === messages.length - 1 && isTyping && !msg.isThinking && (
                      <span className="inline-block w-1.5 h-4 ml-1 bg-blue-500 animate-pulse align-middle"></span>
                    )}
                  </div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Area */}
          <div className="p-4 md:p-6 bg-white/60 backdrop-blur-md border-t border-white/30">
            <div className="relative flex items-center shadow-sm rounded-xl">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !isTyping && handleSend()}
                placeholder={
                  !systemReady
                    ? 'System not ready...'
                    : isTyping
                    ? 'DeepSeek is thinking...'
                    : 'Ask a question about dual-protein interactions...'
                }
                disabled={isTyping || !systemReady}
                className="w-full pl-6 pr-28 py-4 rounded-xl bg-white/80 border border-slate-200/60 focus:border-blue-400 focus:ring-4 focus:ring-blue-100/50 focus:outline-none transition-all text-slate-700 placeholder:text-slate-400 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={isTyping ? handleStop : handleSend}
                disabled={(!isTyping && !input.trim()) || !systemReady}
                className={`absolute right-2 top-1/2 -translate-y-1/2 flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-white font-medium shadow-md hover:shadow-lg transition-all active:scale-95 ${
                  isTyping
                    ? 'bg-[var(--color-primary)] hover:bg-blue-600 opacity-90'
                    : 'bg-[var(--color-primary)] hover:bg-blue-600 disabled:opacity-50 disabled:shadow-none'
                }`}
              >
                {!isTyping && <span>Send</span>}
                {isTyping ? <Square size={16} fill="currentColor" /> : <Send size={16} />}
              </button>
            </div>
            <div className="text-center mt-2 flex justify-center items-center gap-2">
              <span className="text-[10px] text-slate-400">Powered by DeepSeek-R1, Designed by FCN lab</span>
              {error && (
                <span className="text-[10px] text-red-500 flex items-center gap-1">
                  <AlertCircle size={10} />
                  {error}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: References (Desktop) */}
        <div className="hidden md:flex w-[280px] flex-col glass-panel rounded-3xl overflow-hidden shadow-xl">
          <div className="p-4 border-b border-white/30 bg-white/60 backdrop-blur-md">
            <div className="flex items-center gap-2 text-slate-700">
              <BookOpen size={18} className="text-blue-600" />
              <h3 className="font-medium text-sm">References</h3>
              <span className="ml-auto bg-blue-100 text-blue-600 text-[10px] px-2 py-0.5 rounded-full font-bold">
                {activeReferences.length}
              </span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {activeReferences.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-center p-4">
                <BookOpen size={32} className="mb-2 opacity-20" />
                <p className="text-xs">References will appear here when you ask a question.</p>
              </div>
            ) : (
              activeReferences.map((ref) => (
                <ReferenceCard key={ref.ref_id} reference={ref} />
              ))
            )}
          </div>
        </div>
      </div>

      {/* Mobile Drawer for References */}
      <div className="md:hidden">
        {activeReferences.length > 0 && !isDrawerOpen && (
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="fixed bottom-0 left-0 right-0 h-12 bg-white rounded-t-2xl shadow-[0_-4px_20px_rgba(0,0,0,0.1)] flex items-center justify-center z-50 text-slate-500 text-xs font-medium gap-2"
          >
            <ChevronUp size={16} />
            <span>View {activeReferences.length} References</span>
          </button>
        )}
        <AnimatePresence>
          {isDrawerOpen && (
            <>
              <motion.div
                key="backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setIsDrawerOpen(false)}
                className="fixed inset-0 bg-black/20 backdrop-blur-sm z-[60]"
              />
              <motion.div
                key="drawer"
                ref={drawerRef}
                initial={{ y: '100%' }}
                animate={{ y: 0 }}
                exit={{ y: '100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className="fixed bottom-0 left-0 right-0 h-[50vh] bg-white rounded-t-3xl z-[70] flex flex-col shadow-2xl"
              >
                <div className="w-full flex items-center justify-center pt-3 pb-2 cursor-grab active:cursor-grabbing" onClick={() => setIsDrawerOpen(false)}>
                  <div className="w-12 h-1 bg-slate-200 rounded-full" />
                </div>
                <div className="px-6 py-2 flex items-center justify-between border-b border-slate-100">
                  <h3 className="font-bold text-slate-800">References</h3>
                  <button onClick={() => setIsDrawerOpen(false)} className="p-1 hover:bg-slate-100 rounded-full">
                    <ChevronDown size={20} className="text-slate-400" />
                  </button>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50/50">
                  {activeReferences.map((ref) => (
                    <ReferenceCard key={ref.ref_id} reference={ref} />
                  ))}
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

const ReferenceCard: React.FC<{ reference: Reference }> = ({ reference }) => {
  const authorText = Array.isArray(reference.authors)
    ? reference.authors.join(', ')
    : reference.author || 'Unknown Author';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="group bg-white rounded-xl p-4 shadow-sm border border-slate-100 hover:shadow-md hover:border-blue-200 transition-all cursor-default overflow-hidden"
    >
      <div className="flex items-start gap-3">
        <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-md mt-0.5 shrink-0 font-mono">
          {reference.ref_id}
        </span>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2 group-hover:line-clamp-none transition-all duration-200 font-sans tracking-tight">
            {reference.title}
          </h4>
          <div className="h-0 opacity-0 group-hover:h-auto group-hover:opacity-100 transition-all duration-300 overflow-hidden">
            <div className="pt-3 mt-2 border-t border-slate-50 text-xs text-slate-600 space-y-1.5 leading-relaxed font-medium">
              <p className="line-clamp-2"><span className="text-slate-400 font-normal">Author:</span> {authorText}</p>
              <p><span className="text-slate-400 font-normal">Journal:</span> {reference.journal} <span className="text-slate-300">|</span> {reference.year}</p>
              {reference.doi && reference.doi !== 'Not Available' && (
                <a
                  href={`https://doi.org/${reference.doi}?utm_source=sweetseek`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 text-blue-600 hover:text-blue-800 hover:underline mt-2 w-max transition-colors font-semibold"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ExternalLink size={12} />
                  <span>DOI: {reference.doi}</span>
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default DualProteinChatInterface;
