import axios from 'axios';
import { ProcessingOptions, PDFFile, FileDetails, OCRStatus } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const uploadFiles = async (
  files: File[],
  options: ProcessingOptions,
  onProgress?: (progress: number) => void
): Promise<{ files: PDFFile[] }> => {
  const formData = new FormData();
  
  files.forEach(file => {
    formData.append('files', file);
  });
  
  // Add all options to form data
  formData.append('use_ocr', String(options.use_ocr ?? true));
  formData.append('ocr_engine', options.ocr_engine);
  formData.append('cloud_ocr_provider', options.cloud_ocr_provider || '');
  formData.append('aws_access_key_id', options.aws_access_key_id || '');
  formData.append('aws_secret_access_key', options.aws_secret_access_key || '');
  formData.append('aws_region', options.aws_region || 'us-east-1');
  formData.append('extract_images', String(options.extract_images ?? true));
  formData.append('extract_tables', String(options.extract_tables ?? true));
  formData.append('extract_drawings', String(options.extract_drawings ?? true));
  formData.append('deduplicate_images', String(options.deduplicate_images ?? false));
  formData.append('describe_images', String(options.describe_images ?? false));
  formData.append('describe_tables', String(options.describe_tables ?? false));
  formData.append('replace_text_with_description', String(options.replace_text_with_description ?? false));
  formData.append('image_description_provider', options.image_description_provider || 'openai_compatible');
  formData.append('image_description_concurrent', String(options.image_description_concurrent ?? 5));
  formData.append('image_description_prompt', options.image_description_prompt || '');
  formData.append('enable_vector_embedding', String(options.enable_vector_embedding ?? false));
  formData.append('vector_embedding_model', options.vector_embedding_model || 'clip');
  formData.append('openai_compatible_api_key', options.openai_compatible_api_key || '');
  formData.append('openai_compatible_base_url', options.openai_compatible_base_url || '');
  formData.append('openai_compatible_model', options.openai_compatible_model || '');
  if (options.client_id) {
    formData.append('client_id', options.client_id);
  }

  const response = await api.post('/upload', formData, {
    onUploadProgress: (progressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });

  return response.data;
};

export const getFiles = async (status?: string): Promise<PDFFile[]> => {
  const params = status ? { status } : {};
  const response = await api.get('/files', { params });
  return response.data;
};

export const getFileDetails = async (fileId: number): Promise<FileDetails> => {
  const response = await api.get(`/files/${fileId}`);
  return response.data;
};

export const downloadFile = async (fileId: number): Promise<Blob> => {
  const response = await api.get(`/download/${fileId}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const downloadBatchFiles = async (fileIds: number[]): Promise<Blob> => {
  const response = await api.post('/download/batch', { file_ids: fileIds }, {
    responseType: 'blob',
  });
  return response.data;
};

export const getOCREngines = async (): Promise<OCRStatus> => {
  const response = await api.get('/ocr-engines');
  return response.data;
};

export const checkHealth = async (): Promise<{ status: string; version: string }> => {
  const response = await api.get('/health');
  return response.data;
};

export const deleteFile = async (fileId: number): Promise<{ message: string; file_id: number }> => {
  const response = await api.delete(`/files/${fileId}`);
  return response.data;
};

export const testImageDescriptionConnection = async (
  provider: string,
  apiKey?: string,
  baseUrl?: string,
  model?: string
): Promise<{ success: boolean; message: string; test_response?: string }> => {
  const formData = new FormData();
  formData.append('provider', provider);
  if (apiKey) formData.append('api_key', apiKey);
  if (baseUrl) formData.append('base_url', baseUrl);
  if (model) formData.append('model', model);
  
  const response = await api.post('/test-connection/image-description', formData);
  return response.data;
};

export const testCloudOCRConnection = async (
  provider: string,
  awsAccessKeyId?: string,
  awsSecretAccessKey?: string,
  awsRegion?: string
): Promise<{ success: boolean; message: string }> => {
  const formData = new FormData();
  formData.append('provider', provider);
  if (awsAccessKeyId) formData.append('aws_access_key_id', awsAccessKeyId);
  if (awsSecretAccessKey) formData.append('aws_secret_access_key', awsSecretAccessKey);
  if (awsRegion) formData.append('aws_region', awsRegion);
  
  const response = await api.post('/test-connection/cloud-ocr', formData);
  return response.data;
};

export default api;