'use client';

import { useState, useCallback, useRef } from 'react';

interface UploadPanelProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function UploadPanel({ onUpload, isUploading }: UploadPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Simulate progress when uploading
  useState(() => {
    if (isUploading) {
      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress >= 95) {
          progress = 95;
          clearInterval(interval);
        }
        setUploadProgress(progress);
      }, 300);
      return () => clearInterval(interval);
    } else {
      setUploadProgress(0);
    }
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    const pdf = droppedFiles.find((f) => f.type === 'application/pdf');
    if (pdf) {
      setFile(pdf);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
    }
  }, []);

  const handleUpload = () => {
    if (file) {
      onUpload(file);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="rounded-xl bg-[#0a0a1e]/60 backdrop-blur-md border border-[#2a2a5a]/50 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a5a]/50 bg-[#111128]/40">
        <div className="flex items-center gap-2">
          <span className="text-base">📄</span>
          <h2 className="text-sm font-bold text-white tracking-wide">Protocol Upload</h2>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">PDF</span>
      </div>

      <div className="p-4">
        {!isUploading ? (
          <>
            {/* Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`
                relative cursor-pointer rounded-xl p-8 
                border-2 border-dashed transition-all duration-300
                flex flex-col items-center justify-center gap-3
                ${isDragging
                  ? 'border-indigo-500/60 bg-indigo-500/10 scale-[1.02] shadow-[0_0_30px_-5px_rgba(99,102,241,0.3)]'
                  : file
                    ? 'border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-500/50'
                    : 'border-[#2a2a5a]/60 bg-[#111128]/20 hover:border-indigo-500/40 hover:bg-indigo-500/5'
                }
              `}
            >
              {/* Upload Icon */}
              {!file ? (
                <>
                  <div className={`
                    w-14 h-14 rounded-2xl flex items-center justify-center
                    transition-all duration-300
                    ${isDragging
                      ? 'bg-indigo-500/20 border border-indigo-500/40 scale-110'
                      : 'bg-slate-800/50 border border-slate-700/50'
                    }
                  `}>
                    <svg
                      className={`w-7 h-7 transition-colors duration-300 ${isDragging ? 'text-indigo-400' : 'text-slate-500'}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={1.5}
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                    </svg>
                  </div>
                  <div className="text-center">
                    <p className={`text-sm font-semibold transition-colors duration-300 ${isDragging ? 'text-indigo-300' : 'text-slate-300'}`}>
                      {isDragging ? 'Release to upload' : 'Drop IRB Protocol PDF'}
                    </p>
                    <p className="text-xs text-slate-500 mt-1">or click to browse</p>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-[10px] text-slate-600 px-2 py-0.5 rounded bg-slate-800/50 border border-slate-700/30">
                      .PDF
                    </span>
                    <span className="text-[10px] text-slate-600">Max 50MB</span>
                  </div>
                </>
              ) : (
                /* File Selected */
                <div className="flex items-center gap-3 w-full">
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-emerald-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{file.name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{formatFileSize(file.size)}</p>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setFile(null);
                    }}
                    className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}

              {/* Hidden File Input */}
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                className="hidden"
                onChange={handleFileSelect}
              />
            </div>

            {/* Upload Button */}
            {file && (
              <button
                onClick={handleUpload}
                className="
                  mt-4 w-full py-3 rounded-xl font-semibold text-sm
                  bg-gradient-to-r from-indigo-600 to-purple-600
                  hover:from-indigo-500 hover:to-purple-500
                  text-white shadow-lg shadow-indigo-500/20
                  hover:shadow-indigo-500/40
                  transition-all duration-300 hover:scale-[1.02]
                  active:scale-[0.98]
                  flex items-center justify-center gap-2
                "
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                </svg>
                Begin IRB Review
              </button>
            )}
          </>
        ) : (
          /* Uploading State */
          <div className="py-8 px-4">
            <div className="flex flex-col items-center gap-4">
              {/* Animated processing icon */}
              <div className="relative w-16 h-16">
                <div className="absolute inset-0 rounded-2xl bg-indigo-500/10 animate-ping" />
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <svg className="w-7 h-7 text-indigo-400 animate-spin" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182" />
                  </svg>
                </div>
              </div>

              <div className="text-center">
                <p className="text-sm font-bold text-white">Uploading Protocol...</p>
                <p className="text-xs text-slate-400 mt-1">Initializing multi-agent review pipeline</p>
              </div>

              {/* Progress Bar */}
              <div className="w-full max-w-xs">
                <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500 ease-out"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
                <p className="text-[10px] text-slate-500 text-center mt-2 font-mono">
                  {Math.round(uploadProgress)}% complete
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
