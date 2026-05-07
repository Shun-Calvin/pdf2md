import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import { PDFFile, ProcessingOptions, UploadProgress } from '../types';

interface AppState {
  // Files
  files: PDFFile[];
  addFiles: (files: PDFFile[]) => void;
  updateFile: (fileId: number, updates: Partial<PDFFile>) => void;
  removeFile: (fileId: number) => void;
  setFiles: (files: PDFFile[]) => void;
  
  // Upload progress
  uploadProgress: { [key: number]: number };
  setUploadProgress: (fileId: number, progress: number) => void;
  
  // Processing status
  processingStatus: { [key: number]: UploadProgress };
  setProcessingStatus: (fileId: number, status: UploadProgress) => void;
  
  // Processing options
  processingOptions: ProcessingOptions;
  setProcessingOptions: (options: Partial<ProcessingOptions>) => void;
  resetProcessingOptions: () => void;
  
  // UI state
  isUploading: boolean;
  setIsUploading: (isUploading: boolean) => void;
  
  // Client ID for WebSocket
  clientId: string;
  regenerateClientId: () => void;
}

const defaultOptions: ProcessingOptions = {
  use_ocr: true,
  ocr_engine: 'paddleocr_mobile',
  cloud_ocr_provider: undefined,
  aws_access_key_id: '',
  aws_secret_access_key: '',
  aws_region: 'us-east-1',
  extract_images: true,
  extract_tables: true,
  extract_drawings: true,
  deduplicate_images: false,
  describe_images: false,
  describe_tables: false,
  replace_text_with_description: false,
  image_description_provider: 'openai_compatible',
  image_description_concurrent: 2,
  image_description_prompt: '',
  openai_compatible_api_key: '',
  openai_compatible_base_url: '',
  openai_compatible_model: 'llava',
  enable_vector_embedding: false,
  vector_embedding_model: 'clip',
};

const generateClientId = () => {
  return `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
};

export const useStore = create<AppState>()(
  devtools(
    persist(
      (set, get) => ({
        // Files
        files: [],
        addFiles: (files) => set((state) => ({ 
          files: [...state.files, ...files] 
        })),
        updateFile: (fileId, updates) => set((state) => ({
          files: state.files.map((f) =>
            f.id === fileId ? { ...f, ...updates } : f
          ),
        })),
        removeFile: (fileId) => set((state) => ({
          files: state.files.filter((f) => f.id !== fileId),
        })),
        setFiles: (files) => set({ files }),
        
        // Upload progress
        uploadProgress: {},
        setUploadProgress: (fileId, progress) => set((state) => ({
          uploadProgress: { ...state.uploadProgress, [fileId]: progress },
        })),
        
        // Processing status
        processingStatus: {},
        setProcessingStatus: (fileId, status) => set((state) => ({
          processingStatus: { ...state.processingStatus, [fileId]: status },
        })),
        
        // Processing options
        processingOptions: defaultOptions,
        setProcessingOptions: (options) => set((state) => ({
          processingOptions: { ...state.processingOptions, ...options },
        })),
        resetProcessingOptions: () => set({ processingOptions: defaultOptions }),
        
        // UI state
        isUploading: false,
        setIsUploading: (isUploading) => set({ isUploading }),
        
        // Client ID
        clientId: generateClientId(),
        regenerateClientId: () => set({ clientId: generateClientId() }),
      }),
      {
        name: 'pdf2md-storage',
        partialize: (state) => ({ 
          processingOptions: state.processingOptions,
          clientId: state.clientId,
        }),
      }
    )
  )
);

export default useStore;