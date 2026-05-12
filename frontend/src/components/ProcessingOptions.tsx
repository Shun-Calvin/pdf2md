import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  FileImage, 
  Scan, 
  Cloud,
  Image as ImageIcon,
  Sparkles,
  AlertCircle,
  TestTube,
  Loader2,
  ChevronDown,
  ChevronUp,
  Eye,
  Cpu,
  Zap,
  Info,
  Key,
  Globe,
  Box,
  Download,
  CheckCircle2,
  RefreshCw
} from 'lucide-react';
import { ProcessingOptions as Options, OCRStatus } from '../types';
import { 
  testImageDescriptionConnection, 
  testCloudOCRConnection,
  checkDependencies,
  installDocling 
} from '../services/api';
import toast from 'react-hot-toast';

interface ProcessingOptionsProps {
  options: Options;
  onChange: (options: Partial<Options>) => void;
  availableEngines: OCRStatus;
}

// Collapsible Section Component
const Section: React.FC<{
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
  badge?: string;
}> = ({ title, icon, children, defaultOpen = true, badge }) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="border-b border-gray-100 last:border-0">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50/50 
                 transition-colors"
      >
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-blue-50 rounded-lg text-blue-600">
            {icon}
          </div>
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-gray-900">{title}</span>
            {badge && (
              <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                {badge}
              </span>
            )}
          </div>
        </div>
        {isOpen ? (
          <ChevronUp className="h-5 w-5 text-gray-400" />
        ) : (
          <ChevronDown className="h-5 w-5 text-gray-400" />
        )}
      </button>
      
      {isOpen && (
        <div className="px-4 pb-4 animate-fade-in">
          {children}
        </div>
      )}
    </div>
  );
};

// Toggle Switch Component
const Toggle: React.FC<{
  id: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}> = ({ id, checked, onChange, label, description, disabled }) => (
  <div className={`flex items-start space-x-3 ${disabled ? 'opacity-50' : ''}`}>
    <div className="flex items-center h-5">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => !disabled && onChange(!checked)}
        className={`
          relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full 
          transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 
          focus:ring-blue-500 focus:ring-offset-2
          ${checked ? 'bg-blue-600' : 'bg-gray-200'}
          ${disabled ? 'cursor-not-allowed' : ''}
        `}
      >
        <span
          className={`
            pointer-events-none inline-block h-5 w-5 transform rounded-full 
            bg-white shadow ring-0 transition duration-200 ease-in-out
            ${checked ? 'translate-x-6' : 'translate-x-0.5'}
          `}
          style={{ marginTop: '2px' }}
        />
      </button>
      <input
        type="checkbox"
        id={id}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="sr-only"
      />
    </div>
    <div className="flex-1">
      <label 
        htmlFor={id} 
        className={`font-medium text-gray-900 ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {label}
      </label>
      {description && (
        <p className="text-sm text-gray-500 mt-0.5">{description}</p>
      )}
    </div>
  </div>
);

const ProcessingOptionsPanel: React.FC<ProcessingOptionsProps> = ({
  options,
  onChange,
  availableEngines,
}) => {
  const [testingImageDesc, setTestingImageDesc] = useState(false);
  const [testingCloudOCR, setTestingCloudOCR] = useState(false);
  const [checkingDependencies, setCheckingDependencies] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [dependencies, setDependencies] = useState<any>({
    docling: { installed: false },
    open_data_loader: { installed: false }
  });

  // Check dependencies on mount
  useEffect(() => {
    const checkDeps = async () => {
      setCheckingDependencies(true);
      try {
        const result = await checkDependencies();
        setDependencies(result);
      } catch (error) {
        console.error('Failed to check dependencies:', error);
      } finally {
        setCheckingDependencies(false);
      }
    };
    
    checkDeps();
  }, []);

  // Install Docling function
  const handleInstallDocling = async () => {
    setInstalling(true);
    
    try {
      const result = await installDocling();
      
      if (result.success) {
        toast.success(result.message, {
          icon: result.already_installed ? '✅' : '🎉',
          duration: 5000
        });
        
        // Refresh dependencies check
        const updatedDeps = await checkDependencies();
        setDependencies(updatedDeps);
      } else {
        toast.error(result.message, { icon: '❌' });
      }
    } catch (error) {
      console.error('Failed to install docling:', error);
      toast.error('Failed to install Docling. Please try again.', { icon: '❌' });
    } finally {
      setInstalling(false);
    }
  };

  const handleTestImageDescription = async () => {
    if (options.image_description_provider === 'openai_compatible' && !options.openai_compatible_api_key) {
      toast.error('Please enter an API key first');
      return;
    }

    setTestingImageDesc(true);
    try {
      const result = await testImageDescriptionConnection(
        options.image_description_provider,
        options.openai_compatible_api_key,
        options.openai_compatible_base_url,
        options.openai_compatible_model
      );
      
      if (result.success) {
        toast.success(result.message, { icon: '✅' });
      } else {
        toast.error(result.message, { icon: '❌' });
      }
    } catch (error) {
      toast.error('Failed to test connection');
    } finally {
      setTestingImageDesc(false);
    }
  };

  const handleTestCloudOCR = async () => {
    if (options.ocr_engine !== 'cloud') {
      toast.error('Please select Cloud OCR engine first');
      return;
    }

    if (!options.cloud_ocr_provider) {
      toast.error('Please select a cloud provider first');
      return;
    }

    setTestingCloudOCR(true);
    try {
      const result = await testCloudOCRConnection(
        options.cloud_ocr_provider,
        options.aws_access_key_id,
        options.aws_secret_access_key,
        options.aws_region
      );
      
      if (result.success) {
        toast.success(result.message, { icon: '✅' });
      } else {
        toast.error(result.message, { icon: '❌' });
      }
    } catch (error) {
      toast.error('Failed to test connection');
    } finally {
      setTestingCloudOCR(false);
    }
  };

  const getEngineIcon = (engine: string) => {
    switch (engine) {
      case 'paddleocr_mobile':
        return <Zap className="h-4 w-4" />;
      case 'paddleocr_server':
        return <Cpu className="h-4 w-4" />;
      case 'tesseract':
        return <Eye className="h-4 w-4" />;
      case 'cloud':
        return <Cloud className="h-4 w-4" />;
      default:
        return <Scan className="h-4 w-4" />;
    }
  };

  return (
    <div className="card sticky top-24">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg shadow-md">
              <Settings className="h-5 w-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Processing Options</h3>
              <p className="text-xs text-gray-500">Configure conversion settings</p>
            </div>
          </div>
        </div>
      </div>

      <div className="divide-y divide-gray-100">
        {/* Parser Selection */}
        <Section 
          title="Document Parser" 
          icon={<FileImage className="h-5 w-5" />}
          badge="Advanced Processing"
          defaultOpen={false}
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Parser Engine
              </label>
              <div className="relative">
                <select
                  value={options.parser_type || 'standard'}
                  onChange={(e) => onChange({ 
                    parser_type: e.target.value as Options['parser_type']
                  })}
                  className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2.5 
                            text-sm focus:border-blue-500 focus:ring-blue-500 
                            transition-colors appearance-none bg-white"
                >
                  <option value="standard">Standard (PyMuPDF + pdfplumber)</option>
                  <option value="docling">Docling (Advanced Layout Analysis)</option>
                  <option value="odl_batch">Open Data Loader (Batch Processing)</option>
                </select>
                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                  <Settings className="h-4 w-4" />
                </div>
                <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            </div>
            
            {/* Docling Settings */}
            {options.parser_type === 'docling' && (
              <div className="mt-4 space-y-4 p-4 bg-blue-50 rounded-xl border border-blue-100">
                {/* Docling Installation Status */}
                {!dependencies.docling.installed && (
                  <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <div className="flex items-start space-x-3 mb-3">
                      <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
                      <div>
                        <h4 className="font-medium text-yellow-800">Docling Not Installed</h4>
                        <p className="text-sm text-yellow-700 mt-1">
                          Install Docling to access advanced document understanding features
                        </p>
                      </div>
                    </div>
                    <button
                      onClick={handleInstallDocling}
                      disabled={installing || checkingDependencies}
                      className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 
                               bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 
                               disabled:bg-gray-300 disabled:cursor-not-allowed 
                               transition-all text-sm font-medium"
                    >
                      {installing ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Installing Docling...</span>
                        </>
                      ) : checkingDependencies ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Checking dependencies...</span>
                        </>
                      ) : (
                        <>
                          <Download className="h-4 w-4" />
                          <span>Install Docling Now</span>
                        </>
                      )}
                    </button>
                    <button
                      onClick={async () => {
                        setCheckingDependencies(true);
                        try {
                          const result = await checkDependencies();
                          setDependencies(result);
                        } finally {
                          setCheckingDependencies(false);
                        }
                      }}
                      className="w-full mt-2 flex items-center justify-center space-x-2 py-2 px-4 
                               text-yellow-700 hover:text-yellow-800 
                               hover:bg-yellow-100/50 rounded-lg 
                               transition-all text-sm font-medium"
                    >
                      <RefreshCw className={`h-4 w-4 ${checkingDependencies ? 'animate-spin' : ''}`} />
                      <span>Check Again</span>
                    </button>
                  </div>
                )}
                
                {/* Docling is installed */}
                {dependencies.docling.installed && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg mb-3">
                    <div className="flex items-center space-x-2">
                      <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0" />
                      <div>
                        <h4 className="font-medium text-green-800">
                          Docling {dependencies.docling.version || 'v2.x'} Installed
                        </h4>
                        <p className="text-sm text-green-700">
                          Advanced document features are available
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                
                <div className="flex items-start space-x-2 p-3">
                  <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-gray-700">Docling Features</p>
                    <p className="text-sm text-gray-600">
                      Advanced document understanding with layout analysis, table detection, and figure extraction
                    </p>
                  </div>
                </div>
                
                <Toggle
                  id="doclingTableDetection"
                  checked={options.docling_enable_table_detection ?? true}
                  onChange={(checked) => onChange({ docling_enable_table_detection: checked })}
                  label="Table Detection"
                  description="Extract tables with structure preservation"
                />
                
                <Toggle
                  id="doclingFigureDetection"
                  checked={options.docling_enable_figure_detection ?? true}
                  onChange={(checked) => onChange({ docling_enable_figure_detection: checked })}
                  label="Figure Detection"
                  description="Extract images and figures from document"
                />
                
                <Toggle
                  id="doclingLayoutAnalysis"
                  checked={options.docling_enable_layout_analysis ?? true}
                  onChange={(checked) => onChange({ docling_enable_layout_analysis: checked })}
                  label="Layout Analysis"
                  description="Analyze document structure (headers, paragraphs, lists)"
                />
                
                <div className="mt-3">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    OCR Engine
                  </label>
                  <div className="relative">
                    <select
                      value={options.docling_ocr_engine ?? 'tesseract'}
                      onChange={(e) => onChange({ 
                        docling_ocr_engine: e.target.value as Options['docling_ocr_engine']
                      })}
                      className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2.5 
                                text-sm focus:border-blue-500 focus:ring-blue-500 
                                transition-colors appearance-none bg-white"
                    >
                      <option value="tesseract">Tesseract OCR</option>
                      <option value="easyocr">EasyOCR</option>
                    </select>
                    <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                      <Scan className="h-4 w-4" />
                    </div>
                    <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                  </div>
                </div>
              </div>
            )}
            
            {/* Open Data Loader Settings */}
            {options.parser_type === 'odl_batch' && (
              <div className="mt-4 space-y-4 p-4 bg-green-50 rounded-xl border border-green-100">
                <div className="flex items-start space-x-2 p-3">
                  <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-gray-700">Batch Processing</p>
                    <p className="text-sm text-gray-600">
                      Process multiple documents in parallel with progress tracking
                    </p>
                  </div>
                </div>
                
                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Batch Size
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="16"
                      value={options.odl_batch_size ?? 4}
                      onChange={(e) => onChange({ 
                        odl_batch_size: parseInt(e.target.value)
                      })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 
                                text-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Parallel Workers
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="8"
                      value={options.odl_num_workers ?? 2}
                      onChange={(e) => onChange({ 
                        odl_num_workers: parseInt(e.target.value)
                      })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 
                                text-sm focus:border-blue-500 focus:ring-blue-500"
                    />
                  </div>
                  
                  <Toggle
                    id="odlStreaming"
                    checked={options.odl_enable_streaming ?? false}
                    onChange={(checked) => onChange({ odl_enable_streaming: checked })}
                    label="Streaming Mode"
                    description="Process documents as a stream for large document sets"
                  />
                </div>
              </div>
            )}
          </div>
        </Section>
        
        {/* OCR Settings */}
        <Section 
          title="Text Extraction (OCR)" 
          icon={<Scan className="h-5 w-5" />}
          badge={options.use_ocr ? 'Enabled' : undefined}
        >
          <div className="space-y-4">
            <Toggle
              id="useOcr"
              checked={options.use_ocr}
              onChange={(checked) => onChange({ use_ocr: checked })}
              label="Enable OCR"
              description="Use OCR for scanned PDFs. Disable for searchable PDFs to extract text directly."
            />

            {options.use_ocr && (
              <div className="mt-4 space-y-4 pl-8">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    OCR Engine
                  </label>
                  <div className="relative">
                    <select
                      value={options.ocr_engine}
                      onChange={(e) => onChange({ 
                        ocr_engine: e.target.value as Options['ocr_engine'],
                        cloud_ocr_provider: undefined 
                      })}
                      className="w-full rounded-lg border border-gray-300 pl-10 pr-4 py-2.5 
                               text-sm focus:border-blue-500 focus:ring-blue-500 
                               transition-colors appearance-none bg-white"
                    >
                      <option value="paddleocr_mobile" disabled={!availableEngines.paddleocr_mobile}>
                        PaddleOCR Mobile (Fast)
                      </option>
                      <option value="paddleocr_server" disabled={!availableEngines.paddleocr_server}>
                        PaddleOCR Server (Accurate)
                      </option>
                      <option value="tesseract" disabled={!availableEngines.tesseract}>
                        Tesseract OCR
                      </option>
                      <option value="cloud" disabled={!availableEngines.cloud}>
                        Cloud OCR
                      </option>
                    </select>
                    <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400">
                      {getEngineIcon(options.ocr_engine)}
                    </div>
                    <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
                  </div>
                </div>

                {options.ocr_engine === 'cloud' && (
                  <div className="space-y-3 p-4 bg-blue-50/50 rounded-xl border border-blue-100">
                    <label className="block text-sm font-medium text-gray-700">
                      Cloud Provider
                    </label>
                    <select
                      value={options.cloud_ocr_provider || ''}
                      onChange={(e) => onChange({ 
                        cloud_ocr_provider: e.target.value as Options['cloud_ocr_provider'] 
                      })}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 
                               text-sm focus:border-blue-500 focus:ring-blue-500"
                    >
                      <option value="">Select Provider</option>
                      <option value="aws">AWS Textract</option>
                      <option value="azure">Azure Form Recognizer</option>
                      <option value="google">Google Vision</option>
                    </select>

                    {options.cloud_ocr_provider === 'aws' && (
                      <div className="space-y-3 mt-3">
                        <div className="relative">
                          <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                          <input
                            type="text"
                            value={options.aws_access_key_id || ''}
                            onChange={(e) => onChange({ aws_access_key_id: e.target.value })}
                            placeholder="AWS Access Key ID"
                            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>

                        <div className="relative">
                          <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                          <input
                            type="password"
                            value={options.aws_secret_access_key || ''}
                            onChange={(e) => onChange({ aws_secret_access_key: e.target.value })}
                            placeholder="AWS Secret Access Key"
                            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>

                        <div className="relative">
                          <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                          <input
                            type="text"
                            value={options.aws_region || 'us-east-1'}
                            onChange={(e) => onChange({ aws_region: e.target.value })}
                            placeholder="AWS Region"
                            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>

                        <button
                          onClick={handleTestCloudOCR}
                          disabled={testingCloudOCR || !options.cloud_ocr_provider}
                          className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 
                                   bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                                   disabled:bg-gray-300 disabled:cursor-not-allowed 
                                   transition-all text-sm font-medium"
                        >
                          {testingCloudOCR ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              <span>Testing...</span>
                            </>
                          ) : (
                            <>
                              <TestTube className="h-4 w-4" />
                              <span>Test Connection</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}

                    {options.cloud_ocr_provider && options.cloud_ocr_provider !== 'aws' && (
                      <div className="flex items-start space-x-2 p-3 bg-yellow-50 rounded-lg text-xs text-yellow-700">
                        <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <p>
                          {options.cloud_ocr_provider === 'azure' 
                            ? 'Azure configuration will use environment variables or default credentials.'
                            : 'Google Vision configuration will use environment variables or service account.'}
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </Section>

        {/* Content Extraction */}
        <Section 
          title="Content Extraction" 
          icon={<FileImage className="h-5 w-5" />}
          badge={options.extract_images || options.extract_tables ? 'Active' : undefined}
        >
          <div className="space-y-4">
            <Toggle
              id="extractImages"
              checked={options.extract_images}
              onChange={(checked) => onChange({ extract_images: checked })}
              label="Extract Images"
              description="Extract and save images from PDF pages"
            />

            <Toggle
              id="extractTables"
              checked={options.extract_tables}
              onChange={(checked) => onChange({ extract_tables: checked })}
              label="Extract Tables"
              description="Convert PDF tables to Markdown format"
            />

            <Toggle
              id="extractDrawings"
              checked={options.extract_drawings}
              onChange={(checked) => onChange({ extract_drawings: checked })}
              label="Extract Vector Drawings"
              description="Extract vector graphics and diagrams"
            />
          </div>
        </Section>

        {/* Image Processing */}
        {options.extract_images && (
          <Section 
            title="Image Processing" 
            icon={<ImageIcon className="h-5 w-5" />}
            badge={options.deduplicate_images ? 'Deduplication On' : undefined}
          >
            <Toggle
              id="deduplicateImages"
              checked={options.deduplicate_images}
              onChange={(checked) => onChange({ deduplicate_images: checked })}
              label="Deduplicate Images"
              description="Remove duplicate images using perceptual hashing to save space"
            />
          </Section>
        )}

        {/* AI Image Description */}
        {(options.extract_images || options.extract_tables) && (
          <Section 
            title="AI Image Description" 
            icon={<Sparkles className="h-5 w-5" />}
            badge={options.describe_images || options.describe_tables ? 'AI Enabled' : undefined}
            defaultOpen={false}
          >
            <div className="space-y-4">
              {options.extract_images && (
                <Toggle
                  id="describeImages"
                  checked={options.describe_images}
                  onChange={(checked) => onChange({ describe_images: checked })}
                  label="Describe Images"
                  description="Generate AI descriptions for extracted images"
                />
              )}

              {options.extract_tables && (
                <Toggle
                  id="describeTables"
                  checked={options.describe_tables}
                  onChange={(checked) => onChange({ describe_tables: checked })}
                  label="Describe Tables"
                  description="Generate AI descriptions for extracted tables"
                />
              )}

              {(options.describe_images || options.describe_tables) && (
                <>
                  <div className="p-4 bg-yellow-50 rounded-xl border border-yellow-200">
                    <Toggle
                      id="replaceTextWithDescription"
                      checked={options.replace_text_with_description}
                      onChange={(checked) => onChange({ replace_text_with_description: checked })}
                      label="Replace Text with Descriptions"
                      description="Replace searchable text with image descriptions to avoid duplication"
                    />
                  </div>

                  <div className="space-y-4 p-4 bg-gradient-to-br from-blue-50 to-indigo-50 
                                rounded-xl border border-blue-100">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Description Provider
                      </label>
                      <select
                        value={options.image_description_provider}
                        onChange={(e) => onChange({ 
                          image_description_provider: e.target.value as Options['image_description_provider'] 
                        })}
                        className="w-full rounded-lg border border-gray-300 px-3 py-2.5 
                                 text-sm focus:border-blue-500 focus:ring-blue-500 bg-white"
                      >
                        <option value="openai">OpenAI</option>
                        <option value="openai_compatible">OpenAI-Compatible API</option>
                      </select>
                    </div>

                    {options.image_description_provider === 'openai_compatible' && (
                      <div className="space-y-3">
                        <div className="relative">
                          <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                          <input
                            type="password"
                            value={options.openai_compatible_api_key || ''}
                            onChange={(e) => onChange({ openai_compatible_api_key: e.target.value })}
                            placeholder="API Key"
                            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>

                        <div className="relative">
                          <Globe className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                          <input
                            type="url"
                            value={options.openai_compatible_base_url || ''}
                            onChange={(e) => onChange({ openai_compatible_base_url: e.target.value })}
                            placeholder="https://api.example.com/v1"
                            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>

                        <div className="relative">
                          <Box className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                          <input
                            type="text"
                            value={options.openai_compatible_model || ''}
                            onChange={(e) => onChange({ openai_compatible_model: e.target.value })}
                            placeholder="Model (e.g., llava, gpt-4-vision)"
                            className="w-full rounded-lg border border-gray-300 pl-10 pr-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500"
                          />
                        </div>

                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Custom Prompt (Optional)
                          </label>
                          <textarea
                            value={options.image_description_prompt || ''}
                            onChange={(e) => onChange({ image_description_prompt: e.target.value })}
                            placeholder="Describe this image in detail..."
                            rows={3}
                            className="w-full rounded-lg border border-gray-300 px-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500 resize-none"
                          />
                          <p className="text-xs text-gray-500 mt-1">
                            Use {'{context}'} to include page context
                          </p>
                        </div>

                        <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                          <label className="block text-sm font-medium text-gray-700 mb-2 flex items-center">
                            <Zap className="h-4 w-4 mr-2 text-yellow-600" />
                            Concurrent Requests: {options.image_description_concurrent || 2}
                          </label>
                          <input
                            type="range"
                            min="1"
                            max="5"
                            value={options.image_description_concurrent || 2}
                            onChange={(e) => onChange({ 
                              image_description_concurrent: parseInt(e.target.value) 
                            })}
                            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                          />
                          <div className="flex justify-between text-xs text-gray-500 mt-2">
                            <span className="text-green-600 font-medium">1 - Safer, avoids rate limits</span>
                            <span className="text-orange-600">5 - Faster but may hit limits</span>
                          </div>
                          <p className="text-xs text-yellow-700 mt-2">
                            <Info className="h-3 w-3 inline mr-1" />
                            Higher values may trigger rate limits (429 errors). Start with 1-2 and increase gradually.
                          </p>
                        </div>
                      </div>
                    )}

                    <button
                      onClick={handleTestImageDescription}
                      disabled={testingImageDesc || 
                        (options.image_description_provider === 'openai_compatible' && 
                         !options.openai_compatible_api_key)}
                      className="w-full flex items-center justify-center space-x-2 py-2.5 px-4 
                               bg-green-600 text-white rounded-lg hover:bg-green-700 
                               disabled:bg-gray-300 disabled:cursor-not-allowed 
                               transition-all text-sm font-medium"
                    >
                      {testingImageDesc ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span>Testing...</span>
                        </>
                      ) : (
                        <>
                          <TestTube className="h-4 w-4" />
                          <span>Test Connection</span>
                        </>
                      )}
                    </button>

                    {/* Vector Embedding Option */}
                    <div className="pt-4 border-t border-blue-200">
                      <Toggle
                        id="enableVectorEmbedding"
                        checked={options.enable_vector_embedding}
                        onChange={(checked) => onChange({ enable_vector_embedding: checked })}
                        label="Generate Vector Embeddings"
                        description="Create embeddings for semantic search capabilities"
                      />
                      
                      {options.enable_vector_embedding && (
                        <div className="mt-3 pl-8">
                          <label className="block text-sm font-medium text-gray-700 mb-2">
                            Embedding Model
                          </label>
                          <select
                            value={options.vector_embedding_model || 'clip'}
                            onChange={(e) => onChange({ vector_embedding_model: e.target.value })}
                            className="w-full rounded-lg border border-gray-300 px-3 py-2 
                                     text-sm focus:border-blue-500 focus:ring-blue-500 bg-white"
                          >
                            <option value="clip">CLIP (Vision-Language)</option>
                            <option value="openai">OpenAI Embeddings</option>
                          </select>
                        </div>
                      )}
                    </div>

                    <div className="flex items-start space-x-2 text-xs text-gray-600 pt-2">
                      <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5 text-blue-500" />
                      <p>
                        Image description requires API credentials. Use a vision-capable model for best results.
                      </p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </Section>
        )}
      </div>
    </div>
  );
};

export default ProcessingOptionsPanel;
