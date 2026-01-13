import React, { useState, useCallback, useRef } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';
import { Alert, AlertDescription } from '../ui/alert';
import { 
  Upload, 
  File, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  FolderOpen,
  Trash2
} from 'lucide-react';

interface UploadedFile {
  id: string;
  name: string;
  size: number;
  type: string;
  status: 'uploading' | 'completed' | 'failed' | 'validating';
  progress: number;
  error?: string;
  uploadedAt: Date;
  fileType: 'audio' | 'orders' | 'ucc';
}

interface FileTypeConfig {
  id: 'audio' | 'orders' | 'ucc';
  name: string;
  description: string;
  acceptedTypes: string[];
  maxSize: number; // in MB
  destination: string;
  icon: React.ReactNode;
}

const FILE_TYPES: FileTypeConfig[] = [
  {
    id: 'audio',
    name: 'Audio Files',
    description: 'Call recordings for transcription and analysis',
    acceptedTypes: ['.wav', '.mp3', '.m4a', '.flac', '.729'],
    maxSize: 100,
    destination: 'audio_segments/',
    icon: <File className="h-5 w-5" />
  },
  {
    id: 'orders',
    name: 'Order Files',
    description: 'CSV files containing order data',
    acceptedTypes: ['.csv'],
    maxSize: 50,
    destination: 'September/Order Files/',
    icon: <File className="h-5 w-5" />
  },
  {
    id: 'ucc',
    name: 'UCC Database',
    description: 'Excel file containing UCC (Unique Client Code) database',
    acceptedTypes: ['.xlsx', '.xls'],
    maxSize: 20,
    destination: 'September/UCC Files/',
    icon: <File className="h-5 w-5" />
  }
];

interface FileUploadProps {
  onUploadComplete?: (files: UploadedFile[]) => void;
  onCancel?: () => void;
}

export const FileUpload: React.FC<FileUploadProps> = ({
  onUploadComplete,
  onCancel
}) => {
  const [selectedFileType, setSelectedFileType] = useState<FileTypeConfig | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File, fileType: FileTypeConfig): string | null => {
    // Check file size
    if (file.size > fileType.maxSize * 1024 * 1024) {
      return `File size exceeds ${fileType.maxSize}MB limit`;
    }

    // Check file extension
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!fileType.acceptedTypes.includes(fileExtension)) {
      return `File type not supported. Accepted types: ${fileType.acceptedTypes.join(', ')}`;
    }

    return null;
  };

  const uploadFile = async (file: File, fileType: FileTypeConfig): Promise<UploadedFile> => {
    const fileId = Math.random().toString(36).substr(2, 9);
    const uploadedFile: UploadedFile = {
      id: fileId,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      progress: 0,
      uploadedAt: new Date(),
      fileType: fileType.id
    };

    // Add to uploaded files list
    setUploadedFiles(prev => [...prev, uploadedFile]);

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('file_type', fileType.id);
      formData.append('date', selectedDate);

      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:5001';
      const response = await fetch(`${apiUrl}/api/upload/files`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
        throw new Error(errorData.error || `Upload failed: ${response.status} ${response.statusText}`);
      }

      await response.json();
      
      // Update file status
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'completed', progress: 100 }
            : f
        )
      );

      return { ...uploadedFile, status: 'completed', progress: 100 };
    } catch (error) {
      // Update file status with error
      setUploadedFiles(prev => 
        prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                status: 'failed', 
                error: error instanceof Error ? error.message : 'Upload failed'
              }
            : f
        )
      );

      throw error;
    }
  };

  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || !selectedFileType) return;

    setError(null);

    // Validate files
    const validFiles: File[] = [];
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const validationError = validateFile(file, selectedFileType);
      if (validationError) {
        setError(validationError);
        return;
      }
      validFiles.push(file);
    }

    try {
      // Upload files
      const uploadPromises = validFiles.map(file => uploadFile(file, selectedFileType));
      const results = await Promise.allSettled(uploadPromises);
      
      const successfulUploads = results
        .filter((result): result is PromiseFulfilledResult<UploadedFile> => result.status === 'fulfilled')
        .map(result => result.value);

      if (successfulUploads.length > 0 && onUploadComplete) {
        onUploadComplete(successfulUploads);
      }
    } catch (error) {
      console.error('Upload error:', error);
    }
  }, [selectedFileType, onUploadComplete, selectedDate]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileSelect(e.target.files);
  };

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'uploading':
        return <Upload className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'validating':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h2 className="text-2xl font-bold mb-4">Upload Files</h2>
        <p className="text-gray-600 mb-6">
          Upload files for trade surveillance processing. Files will be associated with the selected date.
        </p>
      </Card>

      {error && (
        <Alert className="border-red-200 bg-red-50">
          <XCircle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* File Type Selection */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Select File Type</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {FILE_TYPES.map((fileType) => (
            <Card
              key={fileType.id}
              className={`p-4 cursor-pointer transition-colors hover:bg-accent ${
                selectedFileType?.id === fileType.id ? 'bg-accent border-primary' : ''
              }`}
              onClick={() => setSelectedFileType(fileType)}
            >
              <div className="flex items-start gap-3">
                {fileType.icon}
                <div className="flex-1">
                  <h4 className="font-medium">{fileType.name}</h4>
                  <p className="text-sm text-muted-foreground mb-2">
                    {fileType.description}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    <div>Accepted: {fileType.acceptedTypes.join(', ')}</div>
                    <div>Max size: {fileType.maxSize}MB</div>
                    <div>Destination: {fileType.destination}</div>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </Card>

      {/* Date Selection */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Select Date</h3>
        <div className="flex items-center gap-4">
          <label htmlFor="date-picker" className="text-sm font-medium">
            Date for uploaded files:
          </label>
          <input
            id="date-picker"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <p className="text-sm text-muted-foreground mt-2">
          Files will be associated with this date for surveillance processing.
        </p>
      </Card>

      {/* Upload Area */}
      {selectedFileType && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Upload {selectedFileType.name}</h3>
          
          <div
            className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragOver 
                ? 'border-primary bg-primary/5' 
                : 'border-gray-300 hover:border-gray-400'
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <Upload className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <p className="text-lg font-medium mb-2">
              Drop files here or click to browse
            </p>
            <p className="text-sm text-gray-500 mb-4">
              Accepted formats: {selectedFileType.acceptedTypes.join(', ')}
            </p>
            <Button
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
            >
              Choose Files
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={selectedFileType.acceptedTypes.join(',')}
              onChange={handleFileInputChange}
              className="hidden"
            />
          </div>
        </Card>
      )}

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">Uploaded Files</h3>
          <div className="space-y-3">
            {uploadedFiles.map((file) => (
              <div key={file.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-3">
                  {getStatusIcon(file.status)}
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-gray-500">
                      {formatFileSize(file.size)} • {file.uploadedAt.toLocaleTimeString()}
                    </p>
                    {file.error && (
                      <p className="text-sm text-red-500">{file.error}</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {file.status === 'uploading' && (
                    <Progress value={file.progress} className="w-20 h-2" />
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(file.id)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
