import React, { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { AlertCircle, ArrowUp, ArrowUpRight, LoaderCircle, Square } from 'lucide-react';
import AnswerContent from './AnswerContent';
import type { ChatMessage, EncapsulationReference } from '../types';
import { isNearBottom } from '../scrollUtils';

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const CONVERSATION_REVEAL_MS = 320;
const PRESET_QUESTIONS = [
  '哪些壁材可以提高包埋效率？',
  '喷雾干燥如何影响生物活性物质的稳定性？',
  '食品递送系统中的释放行为受哪些因素控制？',
];

type ExperiencePhase = 'intro' | 'departing' | 'conversation';

const EncapsulationChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [typing, setTyping] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<ExperiencePhase>('intro');
  const reducedMotion = Boolean(useReducedMotion());
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const autoScrollRef = useRef(true);
  const scrollFrameRef = useRef<number | null>(null);
  const transitionTimerRef = useRef<number | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    fetch('/api/encapsulation/prewarm', { method: 'POST' }).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!messages.length || !autoScrollRef.current) return;
    if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
    scrollFrameRef.current = requestAnimationFrame(() => {
      const container = scrollRef.current;
      if (container && autoScrollRef.current) container.scrollTop = container.scrollHeight;
      scrollFrameRef.current = null;
    });

    return () => {
      if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
      scrollFrameRef.current = null;
    };
  }, [messages, status]);

  useEffect(() => () => {
    if (scrollFrameRef.current !== null) cancelAnimationFrame(scrollFrameRef.current);
    if (transitionTimerRef.current !== null) window.clearTimeout(transitionTimerRef.current);
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = '0px';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [input]);

  const updateAssistant = (update: (message: ChatMessage) => ChatMessage) => {
    setMessages((previous) => {
      const next = [...previous];
      let index = next.length - 1;
      while (index >= 0 && next[index].role !== 'assistant') index -= 1;
      if (index >= 0) next[index] = update(next[index]);
      return next;
    });
  };

  const send = async () => {
    const question = input.trim();
    if (!question || typing) return;

    const assistantId = makeId();
    if (phase === 'intro') {
      setPhase('departing');
      transitionTimerRef.current = window.setTimeout(
        () => setPhase('conversation'),
        reducedMotion ? 120 : CONVERSATION_REVEAL_MS,
      );
    }
    autoScrollRef.current = true;
    setInput('');
    setError(null);
    setStatus('正在检索文献...');
    setTyping(true);
    setMessages((previous) => [
      ...previous,
      { id: makeId(), role: 'user', content: question },
      { id: assistantId, role: 'assistant', content: '', references: [] },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch('/api/encapsulation/ask_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || response.statusText);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('响应流不可用');
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          const line = event.split('\n').find((item) => item.startsWith('data: '));
          if (!line) continue;
          const data = JSON.parse(line.slice(6));
          if (data.type === 'status') setStatus(data.message || '正在生成答案...');
          if (data.type === 'answer_start') setStatus('');
          if (data.type === 'references') {
            updateAssistant((message) => ({
              ...message,
              references: (data.references || []) as EncapsulationReference[],
            }));
          }
          if (data.type === 'answer') {
            updateAssistant((message) => ({ ...message, content: message.content + data.content }));
          }
          if (data.type === 'error') throw new Error(data.error || '问答服务异常');
          if (data.type === 'done') setStatus('');
        }
      }
    } catch (requestError) {
      const reason = requestError as Error;
      if (reason.name !== 'AbortError') {
        setError(reason.message || '请求失败，请稍后重试');
      }
    } finally {
      setTyping(false);
      setStatus('');
      abortRef.current = null;
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      void send();
    }
  };

  const selectPreset = (question: string) => {
    setInput(question);
    requestAnimationFrame(() => textareaRef.current?.focus());
  };

  const composer = (variant: 'intro' | 'conversation') => (
    <div className="w-full">
      <div className={`relative border transition focus-within:border-blue-300 focus-within:ring-4 focus-within:ring-blue-50 ${
        variant === 'intro'
          ? 'rounded-xl border-slate-200/80 bg-white/82 shadow-[0_18px_50px_rgba(15,23,42,0.11)] backdrop-blur-md'
          : 'rounded-md border-slate-200 bg-white shadow-[0_8px_30px_rgba(15,23,42,0.08)]'
      }`}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={typing}
          rows={1}
          placeholder="Ask anything about encapsulation research"
          className={`block max-h-[180px] w-full resize-none bg-transparent px-6 pr-16 text-[15px] leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:opacity-70 ${
            variant === 'intro' ? 'min-h-[96px] py-5' : 'min-h-[76px] py-4'
          }`}
          aria-label="Encapsulation question"
        />
        <button
          type="button"
          title={typing ? 'Stop generating' : 'Send'}
          aria-label={typing ? 'Stop generating' : 'Send question'}
          onClick={() => typing ? abortRef.current?.abort() : void send()}
          disabled={!typing && !input.trim()}
          className="absolute bottom-3 right-3 flex size-9 items-center justify-center rounded-md bg-blue-600 text-white transition hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400"
        >
          {typing ? <Square size={14} fill="currentColor" /> : <ArrowUp size={18} strokeWidth={2.4} />}
        </button>
      </div>
      {variant === 'intro' && (
        <div
          className="mt-4 flex flex-col gap-1"
          aria-label="Suggested questions"
          data-testid="suggested-questions"
        >
          {PRESET_QUESTIONS.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => selectPreset(question)}
              className="group flex min-h-10 items-center justify-between gap-3 rounded-md bg-transparent px-2 py-2 text-left text-sm leading-6 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              <span>{question}</span>
              <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-slate-400 transition group-hover:text-cyan-600" />
            </button>
          ))}
        </div>
      )}
      {error && (
        <div className="mt-2 flex items-center gap-1.5 text-xs text-red-600">
          <AlertCircle size={13} /> {error}
        </div>
      )}
    </div>
  );

  return (
    <main className={`relative isolate flex h-full w-full overflow-hidden bg-white ${
      phase === 'conversation' ? 'flex-col' : 'items-center justify-center px-4 pb-[2vh]'
    }`}>
      {phase !== 'conversation' ? (
        <motion.div
          data-testid="encapsulation-welcome"
          initial={false}
          animate={phase === 'departing' ? { opacity: 0, scale: 0.99 } : { opacity: 1, scale: 1 }}
          transition={{ duration: reducedMotion ? 0.12 : 0.28, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 flex w-full max-w-[1040px] flex-col items-center text-center"
        >
          <h1 className="font-medium leading-[1.06] tracking-normal text-slate-950">
            <span className="block whitespace-nowrap text-[24px] sm:text-[36px] md:text-[48px] lg:text-[54px]">Explore encapsulation science</span>
            <span className="mt-1 block whitespace-nowrap text-[17px] sm:text-[27px] md:text-[36px] lg:text-[46px]">from precise encapsulation to targeted release</span>
          </h1>
          <div className="mt-8 w-full max-w-[890px] text-left md:mt-10">{composer('intro')}</div>
        </motion.div>
      ) : (
        <>
          <div
            ref={scrollRef}
            className="relative z-10 flex-1 overflow-y-auto overscroll-contain"
            onWheel={() => { autoScrollRef.current = false; }}
            onTouchMove={() => { autoScrollRef.current = false; }}
            onScroll={(event) => {
              autoScrollRef.current = isNearBottom(event.currentTarget);
            }}
          >
            <div className="mx-auto w-full max-w-[900px] px-4 py-8 md:px-8 md:py-12">
              {messages.map((message) => (
                <article key={message.id} className="mb-9 last:mb-0">
                  {message.role === 'user' ? (
                    <div className="flex justify-end">
                      <div className="max-w-[82%] rounded-md bg-slate-100 px-4 py-3 text-[15px] leading-6 text-slate-800 whitespace-pre-wrap">
                        {message.content}
                      </div>
                    </div>
                  ) : (
                    <div className="min-h-7">
                      {message.content ? (
                        <AnswerContent content={message.content} references={message.references || []} />
                      ) : typing ? (
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                          <LoaderCircle size={15} className="animate-spin" /> {status || '正在组织回答...'}
                        </div>
                      ) : null}
                    </div>
                  )}
                </article>
              ))}
            </div>
          </div>
          <div className="relative z-10 shrink-0 border-t border-slate-100 bg-white/95 px-4 py-4 backdrop-blur md:px-8">
            <div className="mx-auto w-full max-w-[900px]">{composer('conversation')}</div>
          </div>
        </>
      )}
    </main>
  );
};

export default EncapsulationChatInterface;
