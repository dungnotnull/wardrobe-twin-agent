import React, { useCallback, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../stores/appStore';
import { listWardrobeItems, uploadWardrobePhoto, deleteWardrobeItem, searchWardrobeText } from '../api';

export default function WardrobePage() {
  const { wardrobeItems, setWardrobeItems } = useAppStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('');
  const [filterColor, setFilterColor] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['wardrobe', filterType, filterColor],
    queryFn: async () => {
      const res = await listWardrobeItems({
        item_type: filterType || undefined,
        color: filterColor || undefined,
      });
      setWardrobeItems(res.data);
      return res.data;
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append('file', file);
      return uploadWardrobePhoto(fd);
    },
    onSuccess: () => {
      // Refetch wardrobe
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteWardrobeItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wardrobe'] });
    },
  });

  const searchMutation = useMutation({
    mutationFn: (query: string) => searchWardrobeText(query),
    onSuccess: (res) => setWardrobeItems(res.data),
  });

  const queryClient = useQueryClient();

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => uploadMutation.mutate(file));
  }, [uploadMutation]);

  return (
    <div className="max-w-6xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">👔 Wardrobe</h2>

      {/* Upload & search bar */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
        >
          📸 Add Photos
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          multiple
          className="hidden"
          onChange={handleFileUpload}
        />

        <div className="flex-1 flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchMutation.mutate(searchQuery)}
            placeholder="Search wardrobe (e.g. 'blue top')"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500"
          />
          <button
            onClick={() => searchMutation.mutate(searchQuery)}
            className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300 text-sm"
          >
            🔍
          </button>
        </div>

        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Types</option>
          <option value="t-shirt">T-Shirt</option>
          <option value="shirt">Shirt</option>
          <option value="jacket">Jacket</option>
          <option value="jeans">Jeans</option>
          <option value="dress">Dress</option>
          <option value="skirt">Skirt</option>
        </select>

        <select
          value={filterColor}
          onChange={(e) => setFilterColor(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
        >
          <option value="">All Colors</option>
          <option value="black">Black</option>
          <option value="white">White</option>
          <option value="blue">Blue</option>
          <option value="red">Red</option>
          <option value="green">Green</option>
          <option value="neutral">Neutral</option>
        </select>
      </div>

      {uploadMutation.isPending && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg text-blue-700 text-sm">
          Processing and tagging garment...
        </div>
      )}

      {/* Wardrobe grid */}
      {isLoading ? (
        <div className="text-center py-12 text-gray-400">Loading wardrobe...</div>
      ) : wardrobeItems.length === 0 ? (
        <div className="text-center py-12 text-gray-400">
          <p className="text-4xl mb-2">👗</p>
          <p>Your wardrobe is empty. Add some clothes!</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {wardrobeItems.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-gray-200 overflow-hidden hover:shadow-lg transition-shadow"
            >
              <div className="aspect-square bg-gray-100 flex items-center justify-center">
                {item.image_path ? (
                  <img
                    src={http://127.0.0.1:7331/static/wardrobe/}
                    alt={item.description || 'Garment'}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <span className="text-3xl">👕</span>
                )}
              </div>
              <div className="p-3 space-y-1">
                <p className="text-xs text-gray-400 truncate">{item.item_type || 'Unknown type'}</p>
                <p className="text-xs text-gray-600 truncate">{item.description || 'No description'}</p>
                <div className="flex flex-wrap gap-1">
                  {item.tags?.slice(0, 3).map((tag) => (
                    <span key={tag} className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded-full">
                      {tag}
                    </span>
                  ))}
                </div>
                <div className="flex justify-between items-center pt-1">
                  <span className="text-[10px] text-gray-300">{item.color || ''}</span>
                  <button
                    onClick={() => deleteMutation.mutate(item.id)}
                    className="text-[10px] text-red-400 hover:text-red-600"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
