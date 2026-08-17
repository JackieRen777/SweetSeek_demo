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
  '蔗糖为什么会产生甜味？',
  '分子结构、浓度和温度如何共同影响甜味感知？',
  '如何结合受体机制与感官证据，设计一款低糖饮料的甜味方案？',
];

const makeId = () => `${Date.now()}-${Math.random().toString(36).slice(2)}`;
const sleep = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

const ChatInterface: React.FC = () => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [typing, setTyping] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    fetch('/api/init', { method: 'POST' }).catch(() => undefined);
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

  const requestAnswer = async (question: string, signal: AbortSignal) => {
    const ask = () => fetch('/api/ask_stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, similarity_threshold: 0.3, max_results: 200 }),
      signal,
    });

    let response = await ask();
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      const message = String(payload.error || response.statusText);
      if (message.includes('未初始化') || message.toLowerCase().includes('not initialized')) {
        setStatus('正在初始化甜味知识库...');
        const deadline = Date.now() + 10 * 60 * 1000;
        let initialized = false;
        while (Date.now() < deadline) {
          const initialization = await fetch('/api/init', { method: 'POST', signal });
          const initializationPayload = await initialization.json().catch(() => ({}));
          if (!initialization.ok && initialization.status !== 202) {
            throw new Error(initializationPayload.error || initializationPayload.message || '甜味知识库初始化失败');
          }
          if (initializationPayload.ready || initializationPayload.status === 'ready') {
            initialized = true;
            break;
          }
          await sleep(1000);
        }
        if (!initialized) {
          throw new Error('甜味知识库初始化超时，请稍后重试');
        }
        response = await ask();
      } else {
        throw new Error(message);
      }
    }
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || response.statusText);
    }
    return response;
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
      title="Explore Sweetness Science"
      subtitle="From Molecular Perception to Sensory Experience"
      placeholder="Ask a question about sweetness"
      ariaLabel="Sweetness question"
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

export default ChatInterface;
