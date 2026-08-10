import React, { useEffect, useRef, useState } from 'react';
import UnifiedQAInterface from '../../../components/ui/UnifiedQAInterface';
import AnswerContent from '../../encapsulation/components/AnswerContent';
import type { EncapsulationReference } from '../../encapsulation/types';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  references?: EncapsulationReference[];
}

const SUGGESTIONS = [
  '大豆蛋白和乳清蛋白混合后会发生什么相互作用？',
  'pH、离子强度和加热条件如何共同影响双蛋白体系的稳定性？',
  '如何为高蛋白饮料设计双蛋白配方，并兼顾溶解性、乳化性和货架期稳定性？',
];

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const sleep = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

const DualProteinChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [typing, setTyping] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch('/api/dual-protein/prewarm', { method: 'POST' }).catch(() => undefined);
  }, []);

  const updateAssistant = (update: (message: Message) => Message) => {
    setMessages((previous) => {
      const next = [...previous];
      let index = next.length - 1;
      while (index >= 0 && next[index].role !== 'assistant') index -= 1;
      if (index >= 0) next[index] = update(next[index]);
      return next;
    });
  };

  const isInitializationError = (message: string) => {
    const normalized = message.toLowerCase();
    return normalized.includes('未初始化') || normalized.includes('initializing') || normalized.includes('not initialized') || normalized.includes('dimguardfailed');
  };

  const requestAnswer = async (question: string, signal: AbortSignal) => {
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      const response = await fetch('/api/dual-protein/ask_stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, similarity_threshold: 0.18, max_results: 200 }),
        signal,
      });
      if (response.ok) return response;
      const payload = await response.json().catch(() => ({}));
      const message = String(payload.error || response.statusText);
      if (isInitializationError(message) && attempt < 3) {
        setStatus('正在初始化双蛋白知识库...');
        await fetch('/api/dual-protein/init', { method: 'POST', signal }).catch(() => undefined);
        await sleep(1000 * attempt);
        continue;
      }
      throw new Error(message);
    }
    throw new Error('双蛋白知识库仍在初始化，请稍后重试');
  };

  const send = async () => {
    const question = input.trim();
    if (!question || typing) return;
    setInput('');
    setTyping(true);
    setStatus('正在检索文献...');
    setError(null);
    setWarning(null);
    setMessages((previous) => [
      ...previous,
      { id: makeId(), role: 'user', content: question },
      { id: makeId(), role: 'assistant', content: '', references: [] },
    ]);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const response = await requestAnswer(question, controller.signal);
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
            updateAssistant((message) => ({ ...message, references: data.references || [] }));
          }
          if (data.type === 'retrieval_stats') setWarning(data.warning || null);
          if (data.type === 'answer') {
            updateAssistant((message) => ({ ...message, content: message.content + data.content }));
          }
          if (data.type === 'error') throw new Error(data.error || '问答服务异常');
          if (data.type === 'done') setStatus('');
        }
      }
    } catch (requestError) {
      const reason = requestError as Error;
      if (reason.name !== 'AbortError') setError(reason.message || '请求失败，请稍后重试');
    } finally {
      setTyping(false);
      setStatus('');
      abortRef.current = null;
    }
  };

  return (
    <UnifiedQAInterface
      title="Explore Dual-Protein Science"
      subtitle="From Molecular Interactions to Functional Food Systems"
      placeholder="Ask a question about dual-protein research"
      ariaLabel="Dual-protein question"
      suggestions={SUGGESTIONS}
      input={input}
      onInputChange={setInput}
      messages={messages}
      typing={typing}
      error={error}
      warning={warning}
      status={status || '正在组织回答...'}
      onSend={() => void send()}
      onStop={() => abortRef.current?.abort()}
      renderAssistant={(message) => (
        <AnswerContent content={message.content} references={message.references || []} />
      )}
    />
  );
};

export default DualProteinChatInterface;
