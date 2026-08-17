"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { userApi } from "@/lib/api";

export default function AddUserPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    if (f.type !== 'application/pdf') {
      setError('Please upload a PDF file.');
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError(null);
    setSuccess(false);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files && e.target.files[0];
    if (f) handleFile(f);
  };

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files && e.dataTransfer.files[0];
    if (f) handleFile(f);
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a PDF form to upload.");
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      // Call the real API endpoint to upload PDF and extract data
      const response = await userApi.uploadPdfForm(file);

      // The backend can return two shapes:
      // 1) { success: boolean, user_id: number, extracted_data: {...}, message: string }
      // 2) { ok: true, key: string, url: string, filename: string, file_size: number }
      // Handle both: only redirect if we received a user_id; otherwise treat upload as successful

      if ((response as any).success && (response as any).user_id) {
        setSuccess(true);
        setFile(null);
        setPreview(null);

        // Redirect to the newly created user's page after a short delay
        setTimeout(() => {
          router.push(`/main/users/${(response as any).user_id}`);
        }, 1500);
      } else if ((response as any).ok) {
        // The form was uploaded and stored for processing. Show success but do not redirect.
        setSuccess(true);
        setFile(null);
        setPreview(null);
        setError(null);
        console.log('[UI] Form uploaded, S3 key:', (response as any).key);
      } else {
        setError("Failed to create user. Please try again.");
      }
    } catch (err: any) {
      console.error('PDF upload error:', err);
      const errorMessage = err.message || "Upload failed. Please try again.";
      
      // Check for specific error types
      if (errorMessage.includes('UNIQUE constraint')) {
        setError("A user with this phone number or email already exists.");
      } else if (errorMessage.includes('Invalid file format')) {
        setError("Invalid file format. Please upload a PDF file.");
      } else if (errorMessage.includes('OCR extraction failed')) {
        setError("Failed to extract data from PDF. Please ensure the form is clear and readable.");
      } else {
        setError(errorMessage);
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-8 h-[calc(100vh-64px)] flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Add User</h2>
        <p className="text-sm text-gray-500">Upload a PDF form to create an account.</p>
      </div>

      <div className="flex-1 bg-white rounded-lg border border-gray-200">
        <form onSubmit={onSubmit} className="h-full flex flex-col p-8 space-y-6">
          {/* Drop Zone */}
          <div
            onDragOver={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`flex-1 relative border-2 border-dashed rounded-2xl transition-all cursor-pointer ${
              dragging
                ? "border-blue-500 bg-blue-50"
                : "border-gray-300 bg-gray-50 hover:border-gray-400 hover:bg-gray-100"
            } ${
              preview ? "p-8" : "p-16"
            }`}
          >
            {!preview ? (
              <div className="absolute inset-0 flex flex-col items-center justify-center text-center space-y-4">
                <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center">
                  <Upload className="h-8 w-8 text-gray-500" />
                </div>
                <div>
                  <p className="text-lg font-medium text-gray-700">Drop the form here</p>
                  <p className="text-sm text-gray-500 mt-1">or click to browse</p>
                </div>
                <p className="text-xs text-gray-400">Supports: PDF files only</p>
              </div>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center space-y-4 p-8">
                <div className="flex flex-col items-center space-y-4">
                  <div className="w-24 h-24 rounded-lg bg-red-100 flex items-center justify-center">
                    <svg className="h-12 w-12 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-gray-900">{file?.name}</p>
                  <p className="text-sm text-gray-500">{(file?.size || 0 / 1024).toFixed(2)} KB</p>
                </div>
              </div>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              onChange={onFileChange}
              className="hidden"
            />
          </div>

          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
              {error}
            </div>
          )}

          {success && (
            <div className="text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg p-3">
              ✓ Account created successfully.
            </div>
          )}

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={uploading || !file}
              className={`px-6 py-2.5 rounded-lg bg-black text-white font-medium border border-black hover:bg-white hover:text-black disabled:opacity-50 disabled:cursor-not-allowed transition-colors`}
            >
              {uploading ? "Creating Account..." : "Upload & Create User"}
            </button>

            <button
              type="button"
              onClick={() => router.push("/main/users")}
              className="px-6 py-2.5 rounded-lg border border-gray-300 bg-white text-gray-700 font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>

            {success && (
              <button
                type="button"
                onClick={() => router.push(`/main/users/123`)}
                className="px-6 py-2.5 rounded-lg bg-green-600 text-white font-medium hover:bg-green-700 transition-colors"
              >
                View Created Account
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
