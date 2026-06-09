import React, { useState, useRef, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useAppStore } from '../stores/appStore';
import { virtualTryOn, mixMatch } from '../api';

export default function TryOnPage() {
  const { activeProfile, tryOnResult, setTryOnResult, isTryOnLoading, setTryOnLoading } = useAppStore();
  const [selectedGarmentId, setSelectedGarmentId] = useState('');
  const [category, setCategory] = useState('upper_body');
  const [garmentImageB64, setGarmentImageB64] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const tryonMutation = useMutation({
    mutationFn: virtualTryOn,
    onMutate: () => setTryOnLoading(true),
    onSuccess: (data) => {
      setTryOnResult(data.data);
      setTryOnLoading(false);
    },
    onError: () => setTryOnLoading(false),
  });

  const mixMatchMutation = useMutation({
    mutationFn: mixMatch,
  });

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const b64 = (reader.result as string).split(',')[1];
      setGarmentImageB64(b64);
    };
    reader.readAsDataURL(file);
  }, []);

  const startTryOn = () => {
    if (!activeProfile) {
      alert('Please set up your body profile first (Body Scan page)');
      return;
    }
    tryonMutation.mutate({
      profile_id: activeProfile.id,
      garment_image_b64: garmentImageB64 || undefined,
      garment_wardrobe_id: selectedGarmentId || undefined,
      category,
    });
  };

  return (
    <div className="max-w-5xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">👗 Virtual Try-On</h2>

      {!activeProfile && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-300 rounded-lg text-yellow-800 text-sm">
          ⚠️ No body profile found. Go to Body Scan to set up your measurements first.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Garment input */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Select Garment</h3>

          {/* Upload garment image */}
          <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-primary-400 transition-colors">
            {garmentImageB64 ? (
              <div className="space-y-2">
                <img
                  src={data:image/png;base64,}
                  alt="Garment"
                  className="max-h-48 mx-auto rounded-lg"
                />
                <button
                  onClick={() => setGarmentImageB64('')}
                  className="text-xs text-red-500 hover:underline"
                >
                  Remove
                </button>
              </div>
            ) : (
              <div>
                <p className="text-gray-400 mb-2">Upload a garment image</p>
                <button
                  onClick={() => fileRef.current?.click()}
                  className="px-4 py-2 bg-primary-600 text-white rounded-lg text-sm hover:bg-primary-700"
                >
                  📤 Choose Image
                </button>
              </div>
            )}
            <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFileUpload} />
          </div>

          {/* Category selector */}
          <div>
            <label className="text-sm text-gray-500">Garment Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
            >
              <option value="upper_body">Upper Body (Top/Shirt/Jacket)</option>
              <option value="lower_body">Lower Body (Pants/Jeans/Skirt)</option>
              <option value="dresses">Dresses / Full Body</option>
            </select>
          </div>

          {/* Try-on button */}
          <button
            onClick={startTryOn}
            disabled={isTryOnLoading || (!garmentImageB64 && !selectedGarmentId)}
            className="w-full px-6 py-3 bg-accent-500 text-white rounded-xl font-semibold hover:bg-accent-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isTryOnLoading ? '⏳ Generating try-on...' : '✨ Start Virtual Try-On'}
          </button>
        </div>

        {/* Results */}
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Try-On Result</h3>
          {isTryOnLoading && (
            <div className="bg-gray-100 rounded-xl p-12 text-center">
              <div className="animate-spin w-8 h-8 border-4 border-primary-600 border-t-transparent rounded-full mx-auto mb-3" />
              <p className="text-gray-500 text-sm">Generating your virtual try-on...</p>
              <p className="text-gray-400 text-xs">This may take 20-60 seconds</p>
            </div>
          )}
          {tryOnResult && !isTryOnLoading && (
            <div className="space-y-4">
              {/* Result image */}
              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
                {tryOnResult.result_image_b64 ? (
                  <img
                    src={data:image/png;base64,}
                    alt="Try-on result"
                    className="w-full"
                  />
                ) : tryOnResult.result_image_path ? (
                  <img
                    src={http://127.0.0.1:7331/static/avatars/}
                    alt="Try-on result"
                    className="w-full"
                  />
                ) : (
                  <div className="p-12 text-center text-gray-400">No result image</div>
                )}
              </div>

              {/* Size recommendation */}
              {tryOnResult.size_recommendation && (
                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm font-semibold text-green-800">
                    Size: {tryOnResult.size_recommendation}
                  </p>
                  {tryOnResult.fit_notes && (
                    <p className="text-xs text-green-600 mt-1">{tryOnResult.fit_notes}</p>
                  )}
                </div>
              )}
            </div>
          )}
          {!tryOnResult && !isTryOnLoading && (
            <div className="bg-gray-50 rounded-xl p-12 text-center text-gray-400">
              <p className="text-4xl mb-2">👗</p>
              <p>Upload a garment and start try-on to see the result</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
