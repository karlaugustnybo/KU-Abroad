import { useCallback, useEffect, useState } from 'react'
import type { Filters } from './exchange'

const FAVORITES_KEY = 'ku-abroad:favorites'
const SAVED_SEARCHES_KEY = 'ku-abroad:saved-searches'
const FAVORITES_ONLY_KEY = 'ku-abroad:favorites-only'

function readIds(key: string): string[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(key)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((id): id is string => typeof id === 'string')
  } catch {
    return []
  }
}

export interface SavedSearch {
  id: string
  name: string
  filters: Filters
  savedAt: string
}

function readSavedSearches(): SavedSearch[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(SAVED_SEARCHES_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter((entry): entry is SavedSearch =>
      typeof entry === 'object' && entry !== null &&
      typeof (entry as SavedSearch).id === 'string' &&
      typeof (entry as SavedSearch).name === 'string' &&
      typeof (entry as SavedSearch).filters === 'object')
  } catch {
    return []
  }
}

export function useFavorites() {
  const [favorites, setFavorites] = useState<string[]>(() => readIds(FAVORITES_KEY))
  const [favoritesOnly, setFavoritesOnly] = useState(() =>
    typeof window === 'undefined' ? false : window.localStorage.getItem(FAVORITES_ONLY_KEY) === '1')

  useEffect(() => {
    try {
      window.localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites))
    } catch {
      // storage full or unavailable — favorites simply won't persist
    }
  }, [favorites])

  useEffect(() => {
    try {
      window.localStorage.setItem(FAVORITES_ONLY_KEY, favoritesOnly ? '1' : '0')
    } catch {
      // ignore
    }
  }, [favoritesOnly])

  const toggle = useCallback((id: string) => {
    setFavorites(current => current.includes(id) ? current.filter(favorite => favorite !== id) : [...current, id])
  }, [])

  const has = useCallback((id: string) => favorites.includes(id), [favorites])

  return { favorites, favoritesOnly, setFavoritesOnly, toggle, has }
}

export function useSavedSearches() {
  const [searches, setSearches] = useState<SavedSearch[]>(readSavedSearches)

  useEffect(() => {
    try {
      window.localStorage.setItem(SAVED_SEARCHES_KEY, JSON.stringify(searches))
    } catch {
      // ignore
    }
  }, [searches])

  const save = useCallback((name: string, filters: Filters) => {
    const trimmed = name.trim().slice(0, 60)
    if (!trimmed) return
    setSearches(current => [
      { id: `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`, name: trimmed, filters, savedAt: new Date().toISOString() },
      ...current,
    ].slice(0, 20))
  }, [])

  const remove = useCallback((id: string) => {
    setSearches(current => current.filter(search => search.id !== id))
  }, [])

  return { searches, save, remove }
}
