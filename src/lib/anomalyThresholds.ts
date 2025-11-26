/**
 * API service for managing anomaly detection thresholds
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export interface AnomalyThreshold {
  id: number
  account_code: string
  account_name: string
  threshold_value: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface AccountWithThreshold {
  account_code: string
  account_name: string
  account_type: string
  threshold_value: number | null
  is_custom: boolean
  default_threshold: number
}

export interface DefaultThreshold {
  default_threshold: number
  description?: string
}

/**
 * Get all thresholds
 */
export async function getThresholds(includeInactive: boolean = false): Promise<AnomalyThreshold[]> {
  const response = await fetch(
    `${API_BASE_URL}/anomaly-thresholds/?include_inactive=${includeInactive}`,
    {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  )

  if (!response.ok) {
    throw new Error(`Failed to fetch thresholds: ${response.statusText}`)
  }

  const data = await response.json()
  return data.thresholds
}

/**
 * Get all accounts with their threshold information
 */
export async function getAllAccountsWithThresholds(
  documentType?: string
): Promise<AccountWithThreshold[]> {
  const url = documentType
    ? `${API_BASE_URL}/anomaly-thresholds/accounts?document_type=${documentType}`
    : `${API_BASE_URL}/anomaly-thresholds/accounts`

  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch accounts with thresholds: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Get threshold for a specific account code
 */
export async function getThreshold(accountCode: string): Promise<AnomalyThreshold> {
  const response = await fetch(
    `${API_BASE_URL}/anomaly-thresholds/${encodeURIComponent(accountCode)}`,
    {
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    }
  )

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Threshold not found for account code: ${accountCode}`)
    }
    throw new Error(`Failed to fetch threshold: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Create or update a threshold (upsert)
 */
export async function saveThreshold(
  accountCode: string,
  accountName: string,
  thresholdValue: number,
  isActive: boolean = true
): Promise<AnomalyThreshold> {
  const response = await fetch(
    `${API_BASE_URL}/anomaly-thresholds/${encodeURIComponent(accountCode)}`,
    {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        account_code: accountCode,
        account_name: accountName,
        threshold_value: thresholdValue,
        is_active: isActive,
      }),
    }
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to save threshold: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Update an existing threshold
 */
export async function updateThreshold(
  accountCode: string,
  thresholdValue?: number,
  accountName?: string,
  isActive?: boolean
): Promise<AnomalyThreshold> {
  const body: any = {}
  if (thresholdValue !== undefined) body.threshold_value = thresholdValue
  if (accountName !== undefined) body.account_name = accountName
  if (isActive !== undefined) body.is_active = isActive

  const response = await fetch(
    `${API_BASE_URL}/anomaly-thresholds/${encodeURIComponent(accountCode)}`,
    {
      method: 'PUT',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    }
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to update threshold: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Delete (deactivate) a threshold
 */
export async function deleteThreshold(accountCode: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/anomaly-thresholds/${encodeURIComponent(accountCode)}`,
    {
      method: 'DELETE',
      credentials: 'include',
    }
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to delete threshold: ${response.statusText}`)
  }
}

/**
 * Get the global default threshold
 */
export async function getDefaultThreshold(): Promise<DefaultThreshold> {
  const response = await fetch(`${API_BASE_URL}/anomaly-thresholds/default/threshold`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`Failed to fetch default threshold: ${response.statusText}`)
  }

  return response.json()
}

/**
 * Set the global default threshold
 */
export async function setDefaultThreshold(thresholdValue: number): Promise<DefaultThreshold> {
  const response = await fetch(`${API_BASE_URL}/anomaly-thresholds/default/threshold`, {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      default_threshold: thresholdValue,
    }),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(error.detail || `Failed to set default threshold: ${response.statusText}`)
  }

  return response.json()
}

