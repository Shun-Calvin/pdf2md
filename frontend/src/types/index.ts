export interface PDFFile {
  id: number;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';
  page_count?: number;
  current_page?: number;  // Current processing page
  processing_duration_seconds?: number;  // Duration in seconds
  created_at: string;
  updated_at?: string;
  completed_at?: string;  // Completion timestamp
  error_message?: string;
  progress?: number;
}

export interface ProcessingOptions {
   use_ocr: boolean;
   ocr_engine: 'paddleocr_mobile' | 'paddleocr_server' | 'tesseract' | 'cloud' | 'none' | 'docling';
   cloud_ocr_provider?: 'aws' | 'azure' | 'google';
   aws_access_key_id?: string;
   aws_secret_access_key?: string;
   aws_region?: string;
   extract_images: boolean;
   extract_tables: boolean;
   extract_drawings: boolean;
   deduplicate_images: boolean;
   describe_images: boolean;
   describe_tables: boolean;
   replace_text_with_description: boolean;
   image_description_provider: 'openai' | 'openai_compatible';
   image_description_concurrent: number;
   image_description_prompt?: string;
   openai_compatible_api_key?: string;
   openai_compatible_base_url?: string;
   openai_compatible_model?: string;
   enable_vector_embedding: boolean;
   vector_embedding_model?: string;
   client_id?: string;
   
   // Parser Selection
   parser_type?: 'standard' | 'docling' | 'odl_batch';
   
   // Docling Settings
   docling_enable_table_detection?: boolean;
   docling_enable_figure_detection?: boolean;
   docling_enable_layout_analysis?: boolean;
   docling_ocr_engine?: 'tesseract' | 'easyocr';
   
   // Open Data Loader Settings
   odl_batch_size?: number;
   odl_num_workers?: number;
   odl_enable_streaming?: boolean;
}

export interface OCRStatus {
  [key: string]: boolean;
}

export interface FileDetails extends PDFFile {
  file_size: number;
  use_ocr: boolean;
  ocr_engine: string;
  pages: Array<{
    page_number: number;
    has_images: boolean;
    has_tables: boolean;
  }>;
  image_count: number;
  duplicate_count: number;
  table_count: number;
  outputs: Array<{
    type: string;
    path: string;
  }>;
}

export interface UploadProgress {
  file_id: number;
  filename: string;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'describing_images' | 'generating_markdown';
  progress: number;
  type: 'progress' | 'complete' | 'error';
  download_url?: string;
  error?: string;
  current_page?: number;
  total_pages?: number;
  current_image?: number;
  total_images?: number;
}

export interface WebSocketMessage {
  type: 'progress' | 'complete' | 'error';
  file_id?: number;
  filename?: string;
  status?: 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'describing_images' | 'generating_markdown';
  progress?: number;
  download_url?: string;
  error?: string;
  current_page?: number;
  total_pages?: number;
  current_image?: number;
  total_images?: number;
}