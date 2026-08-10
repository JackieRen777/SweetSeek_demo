import React, { useEffect, useRef, useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { AlertCircle, ArrowUp, ArrowUpRight, LoaderCircle, Square } from 'lucide-react';

export interface UnifiedQAMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface Props<T extends UnifiedQAMessage> {
  title: string;
  subtitle: string;
  placeholder: string;
  ariaLabel: string;
  suggestions: string[];
  input: string;
  onInputChange: (value: string) => void;
  messages: T[];
  typing: boolean;
  sendDisabled?: boolean;
  status?: string;
  error?: string | null;
  warning?: string | null;
  onSend: () => void;
  onStop: () => void;
  renderAssistant: (message: T, index: number) => React.ReactNode;
}

const CONVERSATION_REVEAL_MS = 320;

const UnifiedQAInterface = <T extends UnifiedQAMessage>({
  title,
  subtitle,
  placeholder,
  ariaLabel,
  suggestions,
  input,
  onInputChange,
  messages,
  typing,
  sendDisabled = false,
  status,
  error,
  warning,
  onSend,
  onStop,
  renderAssistant,
}: Props<T>) => {
  const [phase, setPhase] = useState<'intro' | 'departing' | 'conversation'>('intro');
  const reducedMotion = Boolean(useReducedMotion());
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const transitionTimerRef = useRef<number | null>(null);
  const autoScrollRef = useRef(true);

  useEffect(() => () => {
    if (transitionTimerRef.current !== null) window.clearTimeout(transitionTimerRef.current);
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = '0px';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 180)}px`;
  }, [input]);

  useEffect(() => {
    const container = scrollRef.current;
    if (phase === 'conversation' && container && autoScrollRef.current) {
      container.scrollTop = container.scrollHeight;
    }
  }, [messages, phase, status]);

  const submit = () => {
    if (!input.trim() || typing || sendDisabled) return;
    if (phase === 'intro') {
      setPhase('departing');
      transitionTimerRef.current = window.setTimeout(
        () => setPhase('conversation'),
        reducedMotion ? 120 : CONVERSATION_REVEAL_MS,
      );
    }
    autoScrollRef.current = true;
    onSend();
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
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
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={typing}
          rows={1}
          placeholder={placeholder}
          className={`block max-h-[180px] w-full resize-none bg-transparent px-6 pr-16 text-[15px] leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:opacity-70 ${
            variant === 'intro' ? 'min-h-[96px] py-5' : 'min-h-[76px] py-4'
          }`}
          aria-label={ariaLabel}
        />
        <button
          type="button"
          title={typing ? 'Stop generating' : 'Send'}
          aria-label={typing ? 'Stop generating' : 'Send question'}
          onClick={typing ? onStop : submit}
          disabled={!typing && (!input.trim() || sendDisabled)}
          className="absolute bottom-3 right-3 flex size-9 items-center justify-center rounded-md bg-blue-600 text-white transition hover:bg-blue-700 disabled:bg-slate-200 disabled:text-slate-400"
        >
          {typing ? <Square size={14} fill="currentColor" /> : <ArrowUp size={18} strokeWidth={2.4} />}
        </button>
      </div>

      {variant === 'intro' && (
        <div className="mt-4 flex flex-col gap-1" aria-label="Suggested questions">
          {suggestions.map((question) => (
            <button
              key={question}
              type="button"
              onClick={() => {
                onInputChange(question);
                requestAnimationFrame(() => textareaRef.current?.focus());
              }}
              className="group flex min-h-10 items-center justify-between gap-3 rounded-md bg-transparent px-2 py-2 text-left text-sm leading-6 text-slate-600 transition hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
            >
              <span>{question}</span>
              <ArrowUpRight className="mt-0.5 size-4 shrink-0 text-slate-400 transition group-hover:text-cyan-600" />
            </button>
          ))}
        </div>
      )}

      {(error || warning) && (
        <div className={`mt-2 flex items-center gap-1.5 text-xs ${error ? 'text-red-600' : 'text-amber-600'}`}>
          <AlertCircle size={13} /> {error || warning}
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
          initial={false}
          animate={phase === 'departing' ? { opacity: 0, scale: 0.99 } : { opacity: 1, scale: 1 }}
          transition={{ duration: reducedMotion ? 0.12 : 0.28, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-10 flex w-full max-w-[1040px] flex-col items-center text-center"
        >
          <h1 className="font-medium leading-[1.06] tracking-normal text-slate-950">
            <span className="block whitespace-nowrap text-[24px] sm:text-[36px] md:text-[48px] lg:text-[54px]">{title}</span>
            <span className="mt-1 block whitespace-nowrap text-[17px] sm:text-[27px] md:text-[36px] lg:text-[46px]">{subtitle}</span>
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
              const element = event.currentTarget;
              autoScrollRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 80;
            }}
          >
            <div className="mx-auto w-full max-w-[900px] px-4 py-8 md:px-8 md:py-12">
              {messages.map((message, index) => (
                <article key={index} className="mb-9 last:mb-0">
                  {message.role === 'user' ? (
                    <div className="flex justify-end">
                      <div className="max-w-[82%] rounded-md bg-slate-100 px-4 py-3 text-[15px] leading-6 text-slate-800 whitespace-pre-wrap">
                        {message.content}
                      </div>
                    </div>
                  ) : (
                    <div className="min-h-7">
                      {message.content ? renderAssistant(message, index) : typing ? (
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

export default UnifiedQAInterface;
