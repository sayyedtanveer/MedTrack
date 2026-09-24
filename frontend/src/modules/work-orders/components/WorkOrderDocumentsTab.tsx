import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Upload, FileText, Download, Eye, X } from 'lucide-react';
import { technicalDocumentService, type DocumentAssociation } from '@/services/technical-document.service';
import { useToast } from '@/hooks/use-toast';

export function WorkOrderDocumentsTab() {
  const { id } = useParams<{ id: string }>();
  const { toast } = useToast();
  const [associations, setAssociations] = useState<DocumentAssociation[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [actionPendingId, setActionPendingId] = useState<string | null>(null);

  // Upload modal state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [docName, setDocName] = useState('');
  const [docCategory, setDocCategory] = useState('Attachment');

  useEffect(() => {
    loadAssociations();
  }, [id]);

  const loadAssociations = async () => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await technicalDocumentService.getAssociations('work_order', id);
      setAssociations(data);
    } catch (e) {
      toast({ title: 'Error', description: 'Failed to load documents', variant: 'destructive' });
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    setSelectedFile(file);
    // Remove extension for default name
    const nameWithoutExt = file.name.replace(/\.[^/.]+$/, "");
    setDocName(nameWithoutExt);
    setDocCategory('Attachment'); // default
    e.target.value = ''; // Reset input
  };

  const confirmUpload = async () => {
    if (!selectedFile || !id) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('document_number', `DOC-${Date.now()}`);
      formData.append('name', docName || selectedFile.name);
      formData.append('document_category', docCategory);
      
      const doc = await technicalDocumentService.createDocument(formData);
      
      await technicalDocumentService.associateDocument({
        revision_id: doc.revisions[0].id,
        target_type: 'work_order',
        target_id: id,
        is_print_package_included: true
      });
      
      toast({ title: 'Success', description: 'Document uploaded and attached' });
      await loadAssociations();
      setSelectedFile(null); // Close modal
    } catch (err: any) {
      toast({ title: 'Upload Failed', description: err.message || 'Failed to upload document', variant: 'destructive' });
    } finally {
      setUploading(false);
    }
  };

  const handleView = async (revisionId: string) => {
    try {
      setActionPendingId(revisionId);
      await technicalDocumentService.viewRevision(revisionId);
    } catch (e: any) {
      toast({ title: 'View Failed', description: e.message || 'Failed to view document', variant: 'destructive' });
    } finally {
      setActionPendingId(null);
    }
  };

  const handleDownload = async (revisionId: string, fileName: string) => {
    try {
      setActionPendingId(revisionId);
      await technicalDocumentService.downloadRevision(revisionId, fileName);
    } catch (e: any) {
      toast({ title: 'Download Failed', description: e.message || 'Failed to download document', variant: 'destructive' });
    } finally {
      setActionPendingId(null);
    }
  };

  if (loading) return <div className="p-4 text-center text-slate-500">Loading documents...</div>;

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white shadow-sm overflow-hidden p-4 sm:p-6 w-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <h3 className="text-lg font-semibold text-slate-900">Work Order Documents</h3>
        <div>
          <label className="cursor-pointer bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors inline-flex items-center gap-2 w-full sm:w-auto justify-center">
            <Upload className="w-4 h-4" />
            Upload Document
            <input 
              type="file" 
              className="hidden" 
              accept=".pdf,.png,.jpg,.jpeg,.doc,.docx,.xls,.xlsx,.dwg"
              onChange={handleFileSelect}
            />
          </label>
        </div>
      </div>
      
      {associations.length === 0 ? (
        <div className="text-center py-10 border-2 border-dashed border-slate-200 rounded-xl">
          <FileText className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <p className="text-slate-500 text-sm">No documents attached yet.</p>
        </div>
      ) : (
        <div className="border border-slate-200 rounded-xl overflow-hidden w-full">
          <div className="overflow-x-auto w-full pb-2 scrollbar-thin scrollbar-thumb-slate-300 scrollbar-track-transparent">
            <table className="w-full text-sm text-left whitespace-nowrap min-w-[600px]">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="px-4 py-3 font-medium">Document Name</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Revision</th>
                  <th className="px-4 py-3 font-medium">Print Package</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {associations.map(assoc => {
                  const fileName = assoc.revision?.file_attachment?.file_name || 'document.pdf';
                  const isPending = actionPendingId === assoc.revision_id;
                  return (
                    <tr key={assoc.id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 font-medium text-slate-900 truncate max-w-[200px]" title={assoc.revision?.document?.name || 'Unnamed Document'}>
                        {assoc.revision?.document?.name || 'Unnamed Document'}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {assoc.revision?.document?.document_category}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        Rev {assoc.revision?.revision_code}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {assoc.is_print_package_included ? 'Yes' : 'No'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex items-center justify-end gap-3">
                          <button 
                            onClick={() => handleView(assoc.revision_id)}
                            disabled={isPending}
                            className="text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            title="View Document"
                          >
                            <Eye className="w-4 h-4" />
                            <span className="hidden sm:inline">View</span>
                          </button>
                          <button 
                            onClick={() => handleDownload(assoc.revision_id, fileName)}
                            disabled={isPending}
                            className="text-slate-600 hover:text-slate-900 font-medium inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            title="Download Document"
                          >
                            <Download className="w-4 h-4" />
                            <span className="hidden sm:inline">Download</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Upload Details Modal */}
      {selectedFile && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900">Document Details</h3>
              <button 
                onClick={() => setSelectedFile(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Document Name
                </label>
                <input 
                  type="text" 
                  value={docName}
                  onChange={e => setDocName(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="E.g. Assembly Drawing v2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Category
                </label>
                <select 
                  value={docCategory}
                  onChange={e => setDocCategory(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                >
                  <option value="Attachment">Attachment</option>
                  <option value="Drawing">Drawing</option>
                  <option value="Specification">Specification</option>
                  <option value="Procedure">Procedure</option>
                  <option value="Manual">Manual</option>
                  <option value="Other">Other</option>
                </select>
              </div>
              <p className="text-xs text-slate-500">
                File: {selectedFile.name} ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
              </p>
            </div>
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-slate-200 bg-slate-50 rounded-b-2xl">
              <button 
                onClick={() => setSelectedFile(null)}
                className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
                disabled={uploading}
              >
                Cancel
              </button>
              <button 
                onClick={confirmUpload}
                disabled={uploading || !docName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {uploading ? 'Uploading...' : 'Confirm Upload'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
