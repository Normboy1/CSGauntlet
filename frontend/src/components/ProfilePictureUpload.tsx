import React, { useState, useRef } from 'react';
import { useAuth } from '../context/AuthContext';

interface ProfilePictureUploadProps {
  currentPicture?: string | null;
  onUploadSuccess?: (pictureUrl: string) => void;
  onDeleteSuccess?: () => void;
  className?: string;
}

const ProfilePictureUpload: React.FC<ProfilePictureUploadProps> = ({
  currentPicture,
  onUploadSuccess,
  onDeleteSuccess,
  className = ''
}) => {
  const { token } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Validate file size (16MB max)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
      setUploadError('File size must be less than 16MB');
      return;
    }

    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      setUploadError('Only PNG, JPG, JPEG, GIF, and WebP files are allowed');
      return;
    }

    await uploadFile(file);
  };

  const uploadFile = async (file: File) => {
    setIsUploading(true);
    setUploadError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/profile/upload-picture', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Upload failed');
      }

      if (data.success) {
        onUploadSuccess?.(data.url);
        setUploadError(null);
      } else {
        throw new Error(data.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async () => {
    if (!currentPicture) return;

    setIsDeleting(true);
    setUploadError(null);

    try {
      const response = await fetch('/api/profile/delete-picture', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Delete failed');
      }

      if (data.success) {
        onDeleteSuccess?.();
        setUploadError(null);
      } else {
        throw new Error(data.error || 'Delete failed');
      }
    } catch (error) {
      console.error('Delete error:', error);
      setUploadError(error instanceof Error ? error.message : 'Delete failed');
    } finally {
      setIsDeleting(false);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Profile Picture Display */}
      <div className="flex flex-col items-center space-y-4">
        <div className="relative">
          <div className="w-32 h-32 rounded-full overflow-hidden bg-gray-700 border-4 border-gray-600 flex items-center justify-center">
            {currentPicture ? (
              <img
                src={currentPicture}
                alt="Profile"
                className="w-full h-full object-cover"
                onError={(e) => {
                  // Fallback to default if image fails to load
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  target.nextElementSibling?.classList.remove('hidden');
                }}
              />
            ) : null}
            {!currentPicture && (
              <div className="text-4xl text-gray-400">
                👤
              </div>
            )}
          </div>

          {/* Loading overlay */}
          {(isUploading || isDeleting) && (
            <div className="absolute inset-0 bg-black bg-opacity-50 rounded-full flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
            </div>
          )}
        </div>

        {/* Upload/Delete Controls */}
        <div className="flex space-x-3">
          <button
            onClick={triggerFileSelect}
            disabled={isUploading || isDeleting}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center space-x-2"
          >
            <span>📷</span>
            <span>{currentPicture ? 'Change' : 'Upload'}</span>
          </button>

          {currentPicture && (
            <button
              onClick={handleDelete}
              disabled={isUploading || isDeleting}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center space-x-2"
            >
              <span>🗑️</span>
              <span>Remove</span>
            </button>
          )}
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
          onChange={handleFileSelect}
          className="hidden"
        />

        {/* Error message */}
        {uploadError && (
          <div className="bg-red-900/20 border border-red-500 rounded-lg p-3 text-red-400 text-sm max-w-xs text-center">
            {uploadError}
          </div>
        )}

        {/* Help text */}
        <div className="text-xs text-gray-400 text-center max-w-xs">
          Upload PNG, JPG, JPEG, GIF, or WebP files up to 16MB
        </div>
      </div>
    </div>
  );
};

export default ProfilePictureUpload;