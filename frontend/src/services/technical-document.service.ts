import { apiClient } from './api-client';

export interface FileAttachment {
  id: string;
  file_name: string;
  file_size_bytes: number;
  content_type: string;
  created_at: string;
  uploaded_by_id: string;
}

export interface DocumentRevision {
  id: string;
  document_id: string;
  file_attachment_id: string;
  revision_code: string;
  status: string;
  notes?: string;
  created_at: string;
  created_by_id: string;
  file_attachment?: FileAttachment;
  document?: TechnicalDocument;
}

export interface TechnicalDocument {
  id: string;
  document_number: string;
  name: string;
  document_category: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  revisions: DocumentRevision[];
}

export interface DocumentAssociation {
  id: string;
  revision_id: string;
  work_order_id?: string;
  variant_id?: string;
  template_id?: string;
  is_print_package_included: boolean;
  created_at: string;
  revision?: DocumentRevision;
}

export const technicalDocumentService = {
  async createDocument(data: FormData): Promise<TechnicalDocument> {
    const response = await apiClient.post<TechnicalDocument>('/technical-documents', data, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async associateDocument(data: {
    revision_id: string;
    target_type: 'work_order' | 'variant' | 'template';
    target_id: string;
    is_print_package_included: boolean;
  }): Promise<DocumentAssociation> {
    const response = await apiClient.post<DocumentAssociation>('/technical-documents/associations', data);
    return response.data;
  },

  async getAssociations(targetType: 'work_order' | 'variant' | 'template', targetId: string): Promise<DocumentAssociation[]> {
    const response = await apiClient.get<DocumentAssociation[]>(`/technical-documents/associations/${targetType}/${targetId}`);
    return response.data;
  },

  async downloadRevision(revisionId: string, fileName: string): Promise<void> {
    const response = await apiClient.get(`/technical-documents/revisions/${revisionId}/download`, {
      responseType: 'blob',
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  },

  async viewRevision(revisionId: string): Promise<void> {
    const response = await apiClient.get(`/technical-documents/revisions/${revisionId}/download`, {
      responseType: 'blob',
    });
    
    const url = window.URL.createObjectURL(new Blob([response.data], { type: response.headers['content-type'] || 'application/pdf' }));
    window.open(url, '_blank');
    setTimeout(() => window.URL.revokeObjectURL(url), 1000);
  },
};
