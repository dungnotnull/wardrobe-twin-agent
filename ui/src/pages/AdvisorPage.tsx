import React, { useState, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useAppStore } from '../stores/appStore';
import { askAdvisor } from '../api';

export default function AdvisorPage() {
  const { chatMessages, addChatMessage, clearChat } = useAppStore();
  const [input, setInput] = useState('');
  const [occasion, setOccasion] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);

  const advisorMutation = useMutation({
    mutationFn: askAdvisor,
    onSuccess: (data) => {
      addChatMessage({
        role: 'assistant',
        content: data.data.advice,
      });
      setTimeout(() => chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
    },
  });

  const sendMessage = () => {
    if (!input.trim()) return;
    addChatMessage({ role: 'user', content: input });
    advisorMutation.mutate({
      prompt: input,
      wardrobe_context: true,
      occasion: occasion || undefined,
    });
    setInput('');
  };

  const quickPrompts = [
    'What should I wear today?',
    'Suggest an outfit for a job interview',
    'What goes with my blue jeans?',
    'Help me pack for a weekend trip',
    'Which items in my wardrobe are underused?',
  ];

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-180px)]">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold">💡 Style Advisor</h2>
        <button onClick={clearChat} className="text-xs text-gray-400 hover:text-gray-600">
          Clear chat
        </button>
      </div>

      {/* Occasion selector */}
      <div className="mb-3">
        <input
          type="text"
          value={occasion}
          onChange={(e) => setOccasion(e.target.value)}
          placeholder="Occasion (optional, e.g. 'dinner date', 'job interview')"
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
        />
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto space-y-3 pr-2 mb-4">
        {chatMessages.length === 0 && (
          <div className="text-center py-12">
            <p className="text-4xl mb-3">💡</p>
            <p className="text-gray-400 mb-4">Ask your AI stylist anything!</p>
            <div className="flex flex-wrap gap-2 justify-center">
              {quickPrompts.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => {
                    setInput(prompt);
                  }}
                  className="text-xs px-3 py-1.5 bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {chatMessages.map((msg) => (
          <div key={msg.id} className={chat-message }>
            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
          </div>
        ))}
        {advisorMutation.isPending && (
          <div className="chat-message assistant">
            <div className="flex items-center gap-2">
              <div className="animate-spin w-3 h-3 border border-gray-400 border-t-transparent rounded-full" />
              <span className="text-xs text-gray-400">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask your stylist..."
          className="flex-1 border border-gray-300 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-primary-500"
          disabled={advisorMutation.isPending}
        />
        <button
          onClick={sendMessage}
          disabled={advisorMutation.isPending || !input.trim()}
          className="px-6 py-3 bg-primary-600 text-white rounded-xl hover:bg-primary-700 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
