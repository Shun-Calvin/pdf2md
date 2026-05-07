import React, { useEffect, useState, useCallback } from 'react';
import { Toaster, toast } from 'react-hot-toast';
import { 
  Upload, 
  FileText, 
  CheckCircle, 
  FolderOpen,
  Activity,
  Database,
  Zap,
  Clock,
  ArrowRight,
  Sparkles
} from 'lucide-react';
import FileUpload from './components/FileUpload';
import ProcessingOptionsPanel from './components/ProcessingOptions';
import FileList from './components/FileList';
import { useStore } from './store/useStore';
import { useWebSocket } from './hooks/useWebSocket';
import { uploadFiles, getFiles, downloadFile, getOCREngines, checkHealth, deleteFile, downloadBatchFiles } from './services/api';
import './App.css';

// Stats Card Component
const StatCard: React.FC<{
  icon: React.ReactNode;
  label: string;
  value: string | number;
  color: 'blue' | 'green' | 'yellow' | 'purple';
  trend?: string;
}> = ({ icon, label, value, color, trend }) => {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600 border-blue-100',
    green: 'bg-green-50 text-green-600 border-green-100',
    yellow: 'bg-yellow-50 text-yellow-600 border-yellow-100',
    purple: 'bg-purple-50 text-purple-600 border-purple-100',
  };

  return (
    <div className="card card-hover p-6">
      <div className="flex items-start justify-between">
        <div className={`p-3 rounded-xl ${colorClasses[color]}`}>
          {icon}
        </div>
        {trend && (
          <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
            {trend}
          </span>
        )}
      </div>
      <div className="mt-4">
        <p className="text-3xl font-bold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500 mt-1">{label}</p>
      </div>
    </div>
  );
};

// Feature Card Component
const FeatureCard: React.FC<{
  icon: React.ReactNode;
  title: string;
  description: string;
}> = ({ icon, title, description }) => (
  <div className="flex items-start space-x-4 p-4 rounded-xl hover:bg-gray-50 transition-colors">
    <div className="flex-shrink-0 p-2 bg-blue-50 rounded-lg text-blue-600">
      {icon}
    </div>
    <div>
      <h4 className="font-semibold text-gray-900">{title}</h4>
      <p className="text-sm text-gray-500 mt-1">{description}</p>
    </div>
  </div>
);

function App() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [availableEngines, setAvailableEngines] = useState<{ [key: string]: boolean }>({});
  const [activeTab, setActiveTab] = useState<'upload' | 'files'>('upload');

  const {
    files,
    addFiles,
    updateFile,
    removeFile,
    setFiles,
    processingOptions,
    setProcessingOptions,
    processingStatus,
    setProcessingStatus,
    isUploading,
    setIsUploading,
    clientId,
  } = useStore();

  const { isConnected, lastMessage } = useWebSocket(clientId);

  // Calculate stats
  const stats = {
    totalFiles: files.length,
    completedFiles: files.filter(f => f.status === 'completed').length,
    processingFiles: files.filter(f => f.status === 'processing' || f.status === 'pending').length,
    failedFiles: files.filter(f => f.status === 'failed').length,
  };

  // Define functions first
  const loadFiles = useCallback(async () => {
    try {
      const files = await getFiles();
      setFiles(files);
    } catch (error) {
      console.error('Error loading files:', error);
      toast.error('Failed to load files');
    }
  }, [setFiles]);

  const loadOCREngines = useCallback(async () => {
    try {
      const engines = await getOCREngines();
      setAvailableEngines(engines);
    } catch (error) {
      console.error('Error loading OCR engines:', error);
    }
  }, []);

  const checkServerHealth = useCallback(async () => {
    try {
      await checkHealth();
    } catch (error) {
      toast.error('Server connection failed. Please check if the backend is running.', {
        duration: 10000,
      });
    }
  }, []);

  // Load files on mount
  useEffect(() => {
    loadFiles();
    loadOCREngines();
    checkServerHealth();
  }, [loadFiles, loadOCREngines, checkServerHealth]);

  // Handle WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const { file_id, filename, status, progress, type, download_url, error, current_page, total_pages } = lastMessage;
      
      if (file_id && type) {
        const messageType = type as 'progress' | 'complete' | 'error';
        const messageStatus = status as 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | undefined;
        
        setProcessingStatus(file_id, {
          file_id,
          filename: filename || '',
          status: messageStatus || 'processing',
          progress: progress || 0,
          type: messageType,
          download_url,
          error,
          current_page,
          total_pages,
          current_image: lastMessage.current_image,
          total_images: lastMessage.total_images,
        });

        if (messageType === 'complete') {
          updateFile(file_id, { status: 'completed', progress: 100 });
          toast.success(`${filename} processing completed!`, {
            icon: '✅',
            duration: 4000,
          });
        } else if (messageType === 'error') {
          updateFile(file_id, { status: 'failed', error_message: error });
          toast.error(`${filename} processing failed: ${error}`, {
            icon: '❌',
            duration: 6000,
          });
        } else if (messageStatus) {
          updateFile(file_id, { status: messageStatus, progress });
        }
      }
    }
  }, [lastMessage, setProcessingStatus, updateFile]);

  const handleFilesSelected = useCallback((files: File[]) => {
    setSelectedFiles(files);
  }, []);

  const handleRemoveFile = useCallback((index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  }, []);

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      toast.error('Please select at least one PDF file');
      return;
    }

    // Validate image description settings if enabled
    if ((processingOptions.describe_images || processingOptions.describe_tables) && 
        processingOptions.image_description_provider === 'openai_compatible') {
      if (!processingOptions.openai_compatible_api_key) {
        toast.error('Please enter an API key for image description');
        return;
      }
      if (!processingOptions.openai_compatible_base_url) {
        toast.error('Please enter a base URL for the OpenAI-compatible API');
        return;
      }
    }

    setIsUploading(true);

    try {
      const options = {
        ...processingOptions,
        client_id: clientId,
      };

      const result = await uploadFiles(selectedFiles, options);
      
      if (result.files && result.files.length > 0) {
        addFiles(result.files);
        toast.success(`Successfully uploaded ${result.files.length} file(s)`);
        setSelectedFiles([]);
        setActiveTab('files');
      }
    } catch (error) {
      console.error('Upload error:', error);
      toast.error('Failed to upload files. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownload = async (fileId: number) => {
    try {
      const blob = await downloadFile(fileId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      const file = files.find(f => f.id === fileId);
      const baseName = file?.filename.replace(/\.pdf$/i, '') || `file_${fileId}`;
      link.download = `${baseName}.zip`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('File downloaded successfully');
    } catch (error) {
      console.error('Download error:', error);
      toast.error('Failed to download file');
    }
  };

  const handleDelete = async (fileId: number) => {
    try {
      await deleteFile(fileId);
      removeFile(fileId);
      toast.success('File deleted successfully');
    } catch (error) {
      console.error('Error deleting file:', error);
      toast.error('Failed to delete file');
    }
  };

  const handleBatchDownload = async (fileIds: number[]) => {
    try {
      const blob = await downloadBatchFiles(fileIds);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `pdf2md_export_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success(`Downloaded ${fileIds.length} file(s) with extracted assets`);
    } catch (error) {
      console.error('Batch download error:', error);
      toast.error('Failed to download files');
    }
  };

  const handleBatchDelete = async (fileIds: number[]) => {
    try {
      for (const fileId of fileIds) {
        await deleteFile(fileId);
        removeFile(fileId);
      }
      toast.success(`Deleted ${fileIds.length} file(s)`);
    } catch (error) {
      console.error('Batch delete error:', error);
      toast.error('Failed to delete some files');
      loadFiles();
    }
  };

  // Connection Status Component
  const ConnectionStatus = () => (
    <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full text-sm font-medium ${
      isConnected 
        ? 'bg-green-50 text-green-700 border border-green-200' 
        : 'bg-red-50 text-red-700 border border-red-200'
    }`}>
      <div className={`w-2 h-2 rounded-full animate-pulse ${
        isConnected ? 'bg-green-500' : 'bg-red-500'
      }`} />
      <span>{isConnected ? 'Connected' : 'Disconnected'}</span>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-white to-blue-50/30">
      <Toaster 
        position="top-right"
        toastOptions={{
          duration: 5000,
          style: {
            background: '#fff',
            border: '1px solid #e5e7eb',
            borderRadius: '12px',
            padding: '16px',
            boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
          },
        }}
      />
      
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-gray-200/80">
        <div className="container-custom">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="absolute inset-0 bg-blue-500 rounded-xl blur-lg opacity-30"></div>
                <div className="relative bg-gradient-to-br from-blue-600 to-indigo-600 p-2.5 rounded-xl shadow-lg shadow-blue-500/25">
                  <FileText className="h-6 w-6 text-white" />
                </div>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                  PDF2MD
                </h1>
                <p className="text-xs text-gray-500 font-medium">PDF to Markdown Converter</p>
              </div>
            </div>
            
            {/* Connection Status */}
            <ConnectionStatus />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container-custom py-8">
        {/* Navigation Tabs */}
        <div className="mb-8">
          <nav className="flex space-x-1 bg-gray-100/80 p-1 rounded-2xl w-fit">
            <button
              onClick={() => setActiveTab('upload')}
              className={`
                flex items-center space-x-2 px-6 py-2.5 rounded-xl font-medium text-sm transition-all duration-200
                ${activeTab === 'upload'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/50'
                }
              `}
            >
              <Upload className="h-4 w-4" />
              <span>Upload & Convert</span>
            </button>
            <button
              onClick={() => setActiveTab('files')}
              className={`
                flex items-center space-x-2 px-6 py-2.5 rounded-xl font-medium text-sm transition-all duration-200
                ${activeTab === 'files'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-200/50'
                }
              `}
            >
              <FolderOpen className="h-4 w-4" />
              <span>My Files</span>
              {stats.totalFiles > 0 && (
                <span className="ml-2 px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-semibold">
                  {stats.totalFiles}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Upload Tab */}
        {activeTab === 'upload' && (
          <div className="space-y-8 animate-slide-up">
            {/* Stats Overview */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard 
                icon={<Database className="h-6 w-6" />}
                label="Total Files"
                value={stats.totalFiles}
                color="blue"
              />
              <StatCard 
                icon={<CheckCircle className="h-6 w-6" />}
                label="Completed"
                value={stats.completedFiles}
                color="green"
              />
              <StatCard 
                icon={<Activity className="h-6 w-6" />}
                label="Processing"
                value={stats.processingFiles}
                color="yellow"
              />
              <StatCard 
                icon={<Zap className="h-6 w-6" />}
                label="Success Rate"
                value={stats.totalFiles > 0 
                  ? `${Math.round((stats.completedFiles / stats.totalFiles) * 100)}%` 
                  : '0%'}
                color="purple"
              />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
              {/* Left Column - Upload & Features */}
              <div className="lg:col-span-3 space-y-6">
                {/* Upload Section */}
                <div className="card">
                  <div className="card-header">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <Upload className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <h2 className="text-lg font-bold text-gray-900">Upload PDF Files</h2>
                        <p className="text-sm text-gray-500">Drag & drop or click to select files</p>
                      </div>
                    </div>
                  </div>
                  <div className="card-body">
                    <FileUpload
                      onFilesSelected={handleFilesSelected}
                      selectedFiles={selectedFiles}
                      onRemoveFile={handleRemoveFile}
                    />
                    
                    {selectedFiles.length > 0 && (
                      <div className="mt-6">
                        <button
                          onClick={handleUpload}
                          disabled={isUploading}
                          className={`
                            w-full py-3.5 px-6 rounded-xl font-semibold text-white
                            transition-all duration-200 flex items-center justify-center space-x-2
                            shadow-lg shadow-blue-500/25
                            ${isUploading
                              ? 'bg-gray-400 cursor-not-allowed'
                              : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:shadow-xl hover:shadow-blue-500/30 active:scale-[0.98]'
                            }
                          `}
                        >
                          {isUploading ? (
                            <>
                              <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                              <span>Uploading {selectedFiles.length} file(s)...</span>
                            </>
                          ) : (
                            <>
                              <Sparkles className="h-5 w-5" />
                              <span>Convert {selectedFiles.length} File(s) to Markdown</span>
                              <ArrowRight className="h-5 w-5" />
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Features Section */}
                <div className="card">
                  <div className="card-header">
                    <h3 className="font-bold text-gray-900">Features</h3>
                  </div>
                  <div className="card-body space-y-2">
                    <FeatureCard
                      icon={<Scan className="h-5 w-5" />}
                      title="Multiple OCR Engines"
                      description="Choose from PaddleOCR, Tesseract, or cloud-based OCR services for optimal accuracy."
                    />
                    <FeatureCard
                      icon={<FileImage className="h-5 w-5" />}
                      title="Image & Table Extraction"
                      description="Automatically extract and describe images and tables from your PDFs."
                    />
                    <FeatureCard
                      icon={<Zap className="h-5 w-5" />}
                      title="AI-Powered Descriptions"
                      description="Generate intelligent descriptions for images using vision AI models."
                    />
                    <FeatureCard
                      icon={<Clock className="h-5 w-5" />}
                      title="Real-time Processing"
                      description="Track conversion progress in real-time with WebSocket updates."
                    />
                  </div>
                </div>
              </div>

              {/* Right Column - Options */}
              <div className="lg:col-span-2">
                <ProcessingOptionsPanel
                  options={processingOptions}
                  onChange={setProcessingOptions}
                  availableEngines={availableEngines}
                />
              </div>
            </div>
          </div>
        )}

        {/* Files Tab */}
        {activeTab === 'files' && (
          <div className="space-y-6 animate-slide-up">
            <div className="card">
              <div className="card-header flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-indigo-100 rounded-lg">
                    <FolderOpen className="h-5 w-5 text-indigo-600" />
                  </div>
                  <div>
                    <h2 className="text-lg font-bold text-gray-900">Your Files</h2>
                    <p className="text-sm text-gray-500">
                      {stats.totalFiles} file{stats.totalFiles !== 1 ? 's' : ''} total
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => loadFiles()}
                  className="btn btn-secondary"
                >
                  <Activity className="h-4 w-4 mr-2" />
                  Refresh
                </button>
              </div>
              
              <div className="card-body">
                <FileList
                  files={files}
                  processingStatus={processingStatus}
                  onDownload={handleDownload}
                  onDelete={handleDelete}
                  onBatchDownload={handleBatchDownload}
                  onBatchDelete={handleBatchDelete}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-16 bg-white">
        <div className="container-custom py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-2 text-gray-500">
              <FileText className="h-5 w-5" />
              <span className="font-medium">PDF2MD Converter</span>
              <span className="text-gray-300">|</span>
              <span className="text-sm">v1.0.0</span>
            </div>
            
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>PaddleOCR</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>Tesseract</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <CheckCircle className="h-4 w-4 text-green-500" />
                <span>Cloud OCR</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

// Icon imports helper
const Scan = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
  </svg>
);

const FileImage = ({ className }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
  </svg>
);

export default App;
