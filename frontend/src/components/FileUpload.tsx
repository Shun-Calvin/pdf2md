import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, FileCheck, AlertCircle, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onFilesSelected,
  selectedFiles,
  onRemoveFile,
}) => {

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      const pdfFiles = acceptedFiles.filter(
        (file) => file.type === 'application/pdf' || file.name.endsWith('.pdf')
      );

      if (pdfFiles.length === 0) {
        toast.error('Please select PDF files only', {
          icon: '🚫',
        });
        return;
      }

      const invalidFiles = acceptedFiles.filter(
        (file) => file.type !== 'application/pdf' && !file.name.endsWith('.pdf')
      );

      if (invalidFiles.length > 0) {
        toast.error(`${invalidFiles.length} file(s) were skipped (not PDFs)`, {
          icon: '⚠️',
        });
      }

      onFilesSelected([...selectedFiles, ...pdfFiles]);
      toast.success(`${pdfFiles.length} PDF file(s) added`, {
        icon: '✅',
      });
    },
    [onFilesSelected, selectedFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getTotalSize = () => {
    return selectedFiles.reduce((acc, file) => acc + file.size, 0);
  };

  const clearAllFiles = () => {
    selectedFiles.forEach((_, index) => onRemoveFile(index));
    toast.success('All files cleared');
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`
          relative border-2 border-dashed rounded-2xl p-10 text-center cursor-pointer
          transition-all duration-300 ease-in-out overflow-hidden
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50/80 scale-[1.02]' 
            : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50/50'
          }
        `}
      >
        {/* Animated Background */}
        <div className={`
          absolute inset-0 bg-gradient-to-br from-blue-500/5 to-indigo-500/5
          transition-opacity duration-300
          ${isDragActive ? 'opacity-100' : 'opacity-0'}
        `} />
        
        <input {...getInputProps()} />
        
        <div className="relative z-10">
          <div className={`
            mx-auto w-20 h-20 rounded-2xl flex items-center justify-center mb-4
            transition-all duration-300
            ${isDragActive 
              ? 'bg-blue-500 shadow-lg shadow-blue-500/30 scale-110' 
              : 'bg-gray-100'
            }
          `}>
            <Upload className={`
              h-10 w-10 transition-colors duration-300
              ${isDragActive ? 'text-white' : 'text-gray-400'}
            `} />
          </div>
          
          <p className="text-lg font-semibold text-gray-700 mb-2">
            {isDragActive ? 'Drop PDF files here' : 'Drag & drop PDF files here'}
          </p>
          <p className="text-sm text-gray-500">
            or <span className="text-blue-600 font-medium">click to browse</span> files
          </p>
          <p className="text-xs text-gray-400 mt-3">
            Supports multiple PDF files • Max 100MB each
          </p>
        </div>
      </div>

      {/* Selected Files List */}
      {selectedFiles.length > 0 && (
        <div className="animate-slide-up">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <FileCheck className="h-5 w-5 text-blue-600" />
              <h3 className="text-sm font-semibold text-gray-900">
                Selected Files ({selectedFiles.length})
              </h3>
            </div>
            <div className="flex items-center space-x-3">
              <span className="text-xs text-gray-500">
                Total: {formatFileSize(getTotalSize())}
              </span>
              <button
                onClick={clearAllFiles}
                className="flex items-center space-x-1 text-xs text-red-600 hover:text-red-700 
                         hover:bg-red-50 px-2 py-1 rounded-lg transition-colors"
              >
                <Trash2 className="h-3.5 w-3.5" />
                <span>Clear All</span>
              </button>
            </div>
          </div>
          
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
            <ul className="divide-y divide-gray-100 max-h-80 overflow-y-auto">
              {selectedFiles.map((file, index) => (
                <li
                  key={`${file.name}-${index}`}
                  className="flex items-center justify-between px-4 py-3 hover:bg-gray-50/80 
                           transition-colors group"
                >
                  <div className="flex items-center space-x-3 min-w-0 flex-1">
                    <div className="flex-shrink-0 w-10 h-10 bg-red-50 rounded-lg 
                                  flex items-center justify-center">
                      <FileText className="h-5 w-5 text-red-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {formatFileSize(file.size)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => onRemoveFile(index)}
                    className="ml-2 p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 
                             rounded-lg transition-all opacity-0 group-hover:opacity-100"
                    title="Remove file"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </li>
              ))}
            </ul>
            
            {/* Summary Footer */}
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
              <div className="flex items-center justify-between text-xs">
                <span className="text-gray-500">
                  {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} ready for conversion
                </span>
                <span className="font-medium text-gray-900">
                  {formatFileSize(getTotalSize())}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Empty State Hint */}
      {selectedFiles.length === 0 && (
        <div className="flex items-center justify-center space-x-2 text-sm text-gray-400 py-4">
          <AlertCircle className="h-4 w-4" />
          <span>No files selected. Drag PDFs above or click to browse.</span>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
