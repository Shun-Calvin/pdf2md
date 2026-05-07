import React, { useState, useMemo } from 'react';
import { 
  FileText, 
  Download, 
  Trash2, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  Clock,
  Archive,
  Calendar,
  FileDigit,
  Timer
} from 'lucide-react';
import { PDFFile, UploadProgress } from '../types';

interface FileListProps {
  files: PDFFile[];
  processingStatus: { [key: number]: UploadProgress };
  onDownload: (fileId: number) => void;
  onDelete: (fileId: number) => void;
  onBatchDownload?: (fileIds: number[]) => void;
  onBatchDelete?: (fileIds: number[]) => void;
}

const FileList: React.FC<FileListProps> = ({
  files,
  processingStatus,
  onDownload,
  onDelete,
  onBatchDownload,
  onBatchDelete,
}) => {
  const [selectedFiles, setSelectedFiles] = useState<Set<number>>(new Set());
  const [downloadingFiles, setDownloadingFiles] = useState<Set<number>>(new Set());
  const [isBatchDownloading, setIsBatchDownloading] = useState(false);

  // Get completed files only (can be downloaded)
  const completedFiles = useMemo(() => {
    return files.filter(file => file.status === 'completed');
  }, [files]);

  // Get selected completed files
  const selectedCompletedFiles = useMemo(() => {
    return Array.from(selectedFiles).filter(id => {
      const file = files.find(f => f.id === id);
      return file?.status === 'completed';
    });
  }, [selectedFiles, files]);

  // Check if all completed files are selected
  const isAllSelected = completedFiles.length > 0 && selectedCompletedFiles.length === completedFiles.length;

  // Handle select all toggle
  const handleSelectAll = () => {
    if (isAllSelected) {
      setSelectedFiles(new Set());
    } else {
      const allCompletedIds = completedFiles.map(f => f.id);
      setSelectedFiles(new Set(allCompletedIds));
    }
  };

  // Handle individual file selection
  const handleSelectFile = (fileId: number, isCompleted: boolean) => {
    if (!isCompleted) return;
    
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(fileId)) {
      newSelected.delete(fileId);
    } else {
      newSelected.add(fileId);
    }
    setSelectedFiles(newSelected);
  };

  // Handle batch download with loading state
  const handleBatchDownload = async () => {
    if (selectedCompletedFiles.length > 0 && onBatchDownload) {
      setIsBatchDownloading(true);
      try {
        await onBatchDownload(selectedCompletedFiles);
      } finally {
        setIsBatchDownloading(false);
        setSelectedFiles(new Set());
      }
    }
  };

  // Handle individual download with loading state
  const handleIndividualDownload = async (fileId: number) => {
    setDownloadingFiles(prev => new Set(prev).add(fileId));
    try {
      await onDownload(fileId);
    } finally {
      setDownloadingFiles(prev => {
        const newSet = new Set(prev);
        newSet.delete(fileId);
        return newSet;
      });
    }
  };

  // Handle batch delete
  const handleBatchDelete = () => {
    if (selectedFiles.size > 0 && onBatchDelete) {
      onBatchDelete(Array.from(selectedFiles));
      setSelectedFiles(new Set());
    }
  };

  const getStatusConfig = (status: string) => {
    switch (status) {
      case 'completed':
        return {
          icon: <CheckCircle className="h-5 w-5" />,
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          label: 'Completed',
          progressColor: 'bg-green-500'
        };
      case 'failed':
        return {
          icon: <AlertCircle className="h-5 w-5" />,
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          label: 'Failed',
          progressColor: 'bg-red-500'
        };
      case 'processing':
        return {
          icon: <Loader2 className="h-5 w-5 animate-spin" />,
          color: 'text-blue-600',
          bgColor: 'bg-blue-50',
          borderColor: 'border-blue-200',
          label: 'Processing',
          progressColor: 'bg-blue-500'
        };
      case 'pending':
        return {
          icon: <Clock className="h-5 w-5" />,
          color: 'text-gray-500',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          label: 'Pending',
          progressColor: 'bg-gray-400'
        };
      default:
        return {
          icon: <Clock className="h-5 w-5" />,
          color: 'text-gray-500',
          bgColor: 'bg-gray-50',
          borderColor: 'border-gray-200',
          label: status,
          progressColor: 'bg-gray-400'
        };
    }
  };

  const getStatusText = (status: string, progress?: number, currentImage?: number, totalImages?: number) => {
    switch (status) {
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'processing':
        return progress ? `Processing (${progress}%)` : 'Processing...';
      case 'describing_images':
        if (currentImage && totalImages) {
          return `Describing images (${currentImage}/${totalImages})`;
        }
        return 'Describing images...';
      case 'pending':
        return 'Pending';
      default:
        return status;
    }
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '';
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.round(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  if (files.length === 0) {
    return (
      <div className="text-center py-16 bg-gray-50/50 rounded-2xl border-2 border-dashed border-gray-200">
        <div className="w-20 h-20 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <FileText className="h-10 w-10 text-gray-400" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 mb-2">No files yet</h3>
        <p className="text-gray-500 max-w-sm mx-auto">
          Upload PDF files to start converting them to Markdown. Your converted files will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Batch Actions Toolbar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 
                    bg-white rounded-xl border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center space-x-4">
          {/* Select All Checkbox */}
          <label className="flex items-center space-x-3 cursor-pointer group">
            <div className={`
              w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
              ${isAllSelected 
                ? 'bg-blue-600 border-blue-600' 
                : 'border-gray-300 group-hover:border-blue-400'
              }
            `}>
              {isAllSelected && <CheckCircle className="h-3.5 w-3.5 text-white" />}
            </div>
            <input
              type="checkbox"
              checked={isAllSelected}
              onChange={handleSelectAll}
              className="sr-only"
            />
            <span className="text-sm font-medium text-gray-700">
              {isAllSelected ? 'Deselect All' : 'Select All'}
            </span>
          </label>
          
          {/* Selection Count */}
          {selectedFiles.size > 0 && (
            <span className="text-sm text-gray-500 bg-gray-100 px-3 py-1 rounded-full">
              {selectedCompletedFiles.length} of {selectedFiles.size} selected
            </span>
          )}
        </div>

        {/* Batch Actions */}
        {selectedFiles.size > 0 && (
          <div className="flex items-center space-x-2">
            {selectedCompletedFiles.length > 0 && onBatchDownload && (
              <button
                onClick={handleBatchDownload}
                disabled={isBatchDownloading}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white 
                         rounded-lg hover:bg-blue-700 transition-all text-sm font-medium 
                         disabled:opacity-50 disabled:cursor-not-allowed shadow-sm
                         hover:shadow-md active:scale-95"
              >
                {isBatchDownloading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Downloading...</span>
                  </>
                ) : (
                  <>
                    <Archive className="h-4 w-4" />
                    <span>Download ({selectedCompletedFiles.length})</span>
                  </>
                )}
              </button>
            )}
            {onBatchDelete && (
              <button
                onClick={handleBatchDelete}
                className="flex items-center space-x-2 px-4 py-2 bg-red-50 text-red-600 
                         rounded-lg hover:bg-red-100 transition-all text-sm font-medium
                         border border-red-200 hover:border-red-300 active:scale-95"
              >
                <Trash2 className="h-4 w-4" />
                <span>Delete ({selectedFiles.size})</span>
              </button>
            )}
          </div>
        )}
      </div>

      {/* File List */}
      <div className="space-y-3">
        {files.map((file) => {
          const status = processingStatus[file.id] || { 
            type: 'progress', 
            status: file.status, 
            progress: file.progress || 0 
          };
          const isCompleted = file.status === 'completed' || status.status === 'completed';
          const isFailed = file.status === 'failed' || status.status === 'failed';
          const isProcessing = file.status === 'processing' || status.status === 'processing';
          const isSelected = selectedFiles.has(file.id);
          const statusConfig = getStatusConfig(status.status || file.status);

          return (
            <div
              key={file.id}
              className={`
                bg-white rounded-xl border transition-all duration-200 overflow-hidden
                ${isFailed ? 'border-red-200' : 'border-gray-200'}
                ${isSelected ? 'ring-2 ring-blue-500 border-blue-500' : 'hover:border-gray-300'}
                shadow-sm hover:shadow-md
              `}
            >
              {/* Main File Row */}
              <div className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start space-x-4 flex-1 min-w-0">
                    {/* Checkbox */}
                    <div className="flex-shrink-0 pt-1">
                      <button
                        onClick={() => handleSelectFile(file.id, isCompleted)}
                        disabled={!isCompleted}
                        className={`
                          w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                          ${isSelected 
                            ? 'bg-blue-600 border-blue-600' 
                            : isCompleted 
                              ? 'border-gray-300 hover:border-blue-400 cursor-pointer' 
                              : 'border-gray-200 cursor-not-allowed opacity-50'
                          }
                        `}
                      >
                        {isSelected && <CheckCircle className="h-3.5 w-3.5 text-white" />}
                      </button>
                    </div>

                    {/* Status Icon */}
                    <div className={`
                      flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center
                      ${statusConfig.bgColor} ${statusConfig.color}
                    `}>
                      {statusConfig.icon}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      {/* Filename */}
                      <h4 className="text-sm font-semibold text-gray-900 truncate mb-1">
                        {file.filename}
                      </h4>
                      
                      {/* Metadata */}
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500">
                        <span className={`
                          inline-flex items-center px-2 py-0.5 rounded-full font-medium
                          ${statusConfig.bgColor} ${statusConfig.color}
                        `}>
                          {getStatusText(status.status || file.status, status.progress, 
                            status.current_image, status.total_images)}
                        </span>
                        
                        <span className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatDate(file.created_at)}</span>
                        </span>
                        
                        {file.page_count && (
                          <span className="flex items-center space-x-1">
                            <FileDigit className="h-3 w-3" />
                            <span>{file.page_count} pages</span>
                          </span>
                        )}
                        
                        {file.processing_duration_seconds && (
                          <span className="flex items-center space-x-1 text-green-600">
                            <Timer className="h-3 w-3" />
                            <span>{formatDuration(file.processing_duration_seconds)}</span>
                          </span>
                        )}
                      </div>

                      {/* Progress bar */}
                      {isProcessing && (
                        <div className="mt-3">
                          <div className="flex justify-between text-xs text-gray-600 mb-1">
                            <span className="font-medium">
                              {status.status === 'describing_images' && status.current_image && status.total_images 
                                ? `Describing image ${status.current_image} of ${status.total_images}`
                                : status.current_page && status.total_pages 
                                  ? `Processing page ${status.current_page} of ${status.total_pages}`
                                  : 'Processing...'}
                            </span>
                            <span className="font-semibold">{status.progress || 0}%</span>
                          </div>
                          <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-full rounded-full transition-all duration-500 ${statusConfig.progressColor}`}
                              style={{ 
                                width: `${status.progress || 0}%`,
                                background: status.status === 'describing_images' 
                                  ? 'linear-gradient(90deg, #8b5cf6, #a78bfa)' 
                                  : undefined
                              }}
                            />
                          </div>
                        </div>
                      )}

                      {/* Error message */}
                      {isFailed && file.error_message && (
                        <div className="mt-3 p-3 bg-red-50 rounded-lg border border-red-100">
                          <p className="text-xs text-red-600 flex items-start space-x-2">
                            <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                            <span>{file.error_message}</span>
                          </p>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center space-x-1">
                    {isCompleted && (
                      <button
                        onClick={() => handleIndividualDownload(file.id)}
                        disabled={downloadingFiles.has(file.id)}
                        className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors
                                 disabled:opacity-50 disabled:cursor-not-allowed"
                        title="Download Markdown"
                      >
                        {downloadingFiles.has(file.id) ? (
                          <Loader2 className="h-5 w-5 animate-spin" />
                        ) : (
                          <Download className="h-5 w-5" />
                        )}
                      </button>
                    )}
                    <button
                      onClick={() => onDelete(file.id)}
                      className="p-2 text-gray-400 hover:text-red-600 hover:bg-red-50 
                               rounded-lg transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default FileList;
