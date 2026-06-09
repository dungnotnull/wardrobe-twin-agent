import React, { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useAppStore } from '../stores/appStore';
import { scanBody, listProfiles } from '../api';

export default function BodyScanPage() {
  const { activeProfile, setActiveProfile } = useAppStore();
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [manualMeasurements, setManualMeasurements] = useState({
    height_cm: '', weight_kg: '', chest_cm: '', waist_cm: '',
    hip_cm: '', inseam_cm: '', shoulder_cm: '',
  });

  const { data: profiles } = useQuery({
    queryKey: ['profiles'],
    queryFn: async () => (await listProfiles()).data,
  });

  const scanMutation = useMutation({
    mutationFn: scanBody,
    onSuccess: (data) => { setActiveProfile(data.data); },
  });

  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
      if (videoRef.current) { videoRef.current.srcObject = stream; setIsCameraOn(true); }
    } catch (err) { console.error('Camera access failed:', err); }
  };

  const stopCamera = () => {
    if (videoRef.current?.srcObject) {
      (videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop());
      setIsCameraOn(false);
    }
  };

  const captureAndScan = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(videoRef.current, 0, 0);
    const frameB64 = canvas.toDataURL('image/jpeg').split(',')[1];
    scanMutation.mutate({
      label: 'default',
      measurements: {
        height_cm: manualMeasurements.height_cm ? parseFloat(manualMeasurements.height_cm) : null,
        weight_kg: manualMeasurements.weight_kg ? parseFloat(manualMeasurements.weight_kg) : null,
        chest_cm: manualMeasurements.chest_cm ? parseFloat(manualMeasurements.chest_cm) : null,
        waist_cm: manualMeasurements.waist_cm ? parseFloat(manualMeasurements.waist_cm) : null,
        hip_cm: manualMeasurements.hip_cm ? parseFloat(manualMeasurements.hip_cm) : null,
        inseam_cm: manualMeasurements.inseam_cm ? parseFloat(manualMeasurements.inseam_cm) : null,
        shoulder_cm: manualMeasurements.shoulder_cm ? parseFloat(manualMeasurements.shoulder_cm) : null,
      },
      webcam_frame_b64: frameB64,
    });
    stopCamera();
  };

  const saveManual = () => {
    scanMutation.mutate({
      label: 'default',
      measurements: {
        height_cm: manualMeasurements.height_cm ? parseFloat(manualMeasurements.height_cm) : null,
        weight_kg: manualMeasurements.weight_kg ? parseFloat(manualMeasurements.weight_kg) : null,
        chest_cm: manualMeasurements.chest_cm ? parseFloat(manualMeasurements.chest_cm) : null,
        waist_cm: manualMeasurements.waist_cm ? parseFloat(manualMeasurements.waist_cm) : null,
        hip_cm: manualMeasurements.hip_cm ? parseFloat(manualMeasurements.hip_cm) : null,
        inseam_cm: manualMeasurements.inseam_cm ? parseFloat(manualMeasurements.inseam_cm) : null,
        shoulder_cm: manualMeasurements.shoulder_cm ? parseFloat(manualMeasurements.shoulder_cm) : null,
      },
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6">🧍 Body Scan</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Camera Scan</h3>
          <div className="webcam-container bg-gray-900 flex items-center justify-center">
            <video ref={videoRef} autoPlay playsInline className="w-full h-full object-cover" />
            {!isCameraOn && <p className="text-gray-400 text-sm absolute">Camera off</p>}
          </div>
          <canvas ref={canvasRef} className="hidden" />
          <div className="flex gap-2">
            {!isCameraOn ? (
              <button onClick={startCamera} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">📷 Start Camera</button>
            ) : (
              <>
                <button onClick={captureAndScan} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">✨ Capture & Scan</button>
                <button onClick={stopCamera} className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600">Stop</button>
              </>
            )}
          </div>
          {scanMutation.isPending && (
            <div className="flex items-center gap-2 text-primary-600">
              <div className="animate-spin w-4 h-4 border-2 border-primary-600 border-t-transparent rounded-full" />
              Scanning body...
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h3 className="font-semibold text-lg">Manual Measurements (cm)</h3>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(manualMeasurements).map(([key, value]) => (
              <div key={key}>
                <label className="text-xs text-gray-500 capitalize">{key.replace('_cm', '').replace('_', ' ')}</label>
                <input type="number" step="0.1" value={value} onChange={(e) => setManualMeasurements(m => ({ ...m, [key]: e.target.value }))}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-primary-500" placeholder="cm" />
              </div>
            ))}
          </div>
          <button onClick={saveManual} disabled={scanMutation.isPending}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">💾 Save Measurements</button>
        </div>
      </div>

      {activeProfile && (
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-xl">
          <h3 className="font-semibold text-blue-800">Active Profile: {activeProfile.label}</h3>
          <div className="grid grid-cols-4 gap-2 mt-2 text-sm">
            {Object.entries(activeProfile.measurements).map(([key, value]) => value !== null && (
              <div key={key} className="text-blue-700"><span className="capitalize">{key.replace('_cm', '').replace('_', ' ')}:</span> <strong>{value} cm</strong></div>
            ))}
          </div>
        </div>
      )}

      {profiles && profiles.length > 0 && (
        <div className="mt-4">
          <h3 className="font-semibold mb-2">Saved Profiles</h3>
          <div className="space-y-2">
            {profiles.map((p: any) => (
              <button key={p.id} onClick={() => setActiveProfile(p)}
                className={`w-full text-left p-3 rounded-lg border transition-colors ${activeProfile?.id === p.id ? 'border-primary-500 bg-primary-50' : 'border-gray-200 hover:bg-gray-50'}`}>
                <span className="font-medium">{p.label}</span>
                <span className="text-xs text-gray-400 ml-2">{p.id.slice(0, 8)}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
