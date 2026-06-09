import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { deleteAllData } from '../api';
import { useAppStore } from '../stores/appStore';

export default function SettingsPage() {
  const { setActiveProfile, setWardrobeItems, setTryOnResult, clearChat } = useAppStore();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [apiKeyClaude, setApiKeyClaude] = useState('');
  const [apiKeyOpenai, setApiKeyOpenai] = useState('');
  const [ollamaHost, setOllamaHost] = useState('http://localhost:11434');

  const deleteMutation = useMutation({
    mutationFn: deleteAllData,
    onSuccess: () => {
      setActiveProfile(null);
      setWardrobeItems([]);
      setTryOnResult(null);
      clearChat();
      setConfirmDelete(false);
      alert('All data deleted successfully.');
    },
  });

  return (
    <div className="max-w-2xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">⚙️ Settings</h2>

      {/* API Keys */}
      <section className="mb-8 p-5 bg-white rounded-xl border border-gray-200 space-y-4">
        <h3 className="font-semibold">API Keys</h3>
        <p className="text-xs text-gray-400">Keys are stored locally and never sent to our servers.</p>

        <div>
          <label className="text-sm text-gray-600">Anthropic Claude API Key</label>
          <input
            type="password"
            value={apiKeyClaude}
            onChange={(e) => setApiKeyClaude(e.target.value)}
            placeholder="sk-ant-..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mt-1"
          />
        </div>

        <div>
          <label className="text-sm text-gray-600">OpenAI API Key</label>
          <input
            type="password"
            value={apiKeyOpenai}
            onChange={(e) => setApiKeyOpenai(e.target.value)}
            placeholder="sk-..."
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mt-1"
          />
        </div>

        <div>
          <label className="text-sm text-gray-600">Ollama Host</label>
          <input
            type="text"
            value={ollamaHost}
            onChange={(e) => setOllamaHost(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mt-1"
          />
        </div>

        <button className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700">
          💾 Save Keys
        </button>
      </section>

      {/* Privacy */}
      <section className="mb-8 p-5 bg-white rounded-xl border border-gray-200 space-y-3">
        <h3 className="font-semibold">🔒 Privacy</h3>
        <div className="text-sm text-gray-600 space-y-2">
          <p>✅ All body scan data is stored locally (AES-256 encrypted)</p>
          <p>✅ Wardrobe images never leave your machine</p>
          <p>✅ LLM API calls only send garment images and measurements (never body scans)</p>
          <p>✅ Browser extension only communicates via localhost</p>
        </div>
      </section>

      {/* Danger zone */}
      <section className="p-5 bg-white rounded-xl border border-red-200 space-y-3">
        <h3 className="font-semibold text-red-600">⚠️ Danger Zone</h3>
        <p className="text-sm text-gray-500">
          Permanently delete all body profiles, wardrobe data, try-on results, and chat history.
          This cannot be undone.
        </p>
        {!confirmDelete ? (
          <button
            onClick={() => setConfirmDelete(true)}
            className="px-4 py-2 bg-red-100 text-red-600 rounded-lg text-sm hover:bg-red-200"
          >
            Delete All Data
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {deleteMutation.isPending ? 'Deleting...' : '⚠️ Confirm Delete'}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="px-4 py-2 bg-gray-200 rounded-lg text-sm hover:bg-gray-300"
            >
              Cancel
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
