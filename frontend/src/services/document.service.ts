import apiClient from './api-client'

export interface Document {
  id: string
  tenant_id: string
  document_type: string
  entity_id: string
  version_number: number
  file_path: string
  generated_by: string | null
  generated_at: string
  is_deleted: boolean
  deleted_at: string | null
}

export interface DocumentVersion {
  id: string
  version_number: number
  generated_by: string | null
  generated_at: string
  file_path: string
}

export interface DocumentList {
  document_type: string
  entity_id: string
  versions: DocumentVersion[]
  total: number
}

export interface DocumentGenerateOptions {
  force_regenerate?: boolean
}

class DocumentService {
  async generateDocument(
    documentType: string,
    entityId: string,
    options: DocumentGenerateOptions = {}
  ): Promise<Document> {
    const response = await apiClient.post(
      `/documents/${documentType}/${entityId}/generate`,
      options
    )
    return response.data
  }

  async downloadDocument(documentId: string): Promise<Blob> {
    const response = await apiClient.get(
      `/documents/${documentId}/download`,
      {
        responseType: 'blob',
      }
    )
    return response.data
  }

  async downloadDocumentByUrl(documentId: string, filename?: string): Promise<void> {
    const blob = await this.downloadDocument(documentId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `document_${documentId}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  async downloadDocumentPackage(documentId: string): Promise<Blob> {
    const response = await apiClient.get(
      `/documents/${documentId}/download-package`,
      {
        responseType: 'blob',
      }
    )
    return response.data
  }

  async downloadDocumentPackageByUrl(documentId: string, filename?: string): Promise<void> {
    const blob = await this.downloadDocumentPackage(documentId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // Default to .zip — the backend always returns application/zip for this endpoint
    a.download = filename || `document_package_${documentId}.zip`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  /**
   * Generate and download the Work Order + BOM PDF.
   * Uses the work_order_bom document type which renders
   * the material snapshot grouped by product line.
   */
  async downloadBomDocument(entityId: string): Promise<Blob> {
    const doc = await this.generateDocument('work_order_bom', entityId)
    const blob = await this.downloadDocument(doc.id)
    return blob
  }

  async downloadBomDocumentByUrl(entityId: string, filename?: string): Promise<void> {
    const blob = await this.downloadBomDocument(entityId)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || `work-order-bom_${entityId}.pdf`
    document.body.appendChild(a)
    a.click()
    window.URL.revokeObjectURL(url)
    document.body.removeChild(a)
  }

  async listDocumentVersions(
    documentType: string,
    entityId: string
  ): Promise<DocumentList> {
    const response = await apiClient.get(
      `/documents/${documentType}/${entityId}/versions`
    )
    return response.data
  }

  async previewDocument(documentId: string): Promise<string> {
    const blob = await this.downloadDocument(documentId)
    const url = window.URL.createObjectURL(blob)
    return url
  }
}

export const documentService = new DocumentService()
